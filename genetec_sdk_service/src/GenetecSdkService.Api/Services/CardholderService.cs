using System.Data;
using Genetec.Sdk;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

/// <summary>
/// Service for cardholder operations against the Genetec SDK.
/// </summary>
public class CardholderService
{
    private readonly GenetecEngineService _engineService;

    public CardholderService(GenetecEngineService engineService)
    {
        _engineService = engineService;
    }

    public CardholderResponse CreateCardholder(CardholderRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.FirstName))
            throw new ArgumentException("firstName is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.LastName))
            throw new ArgumentException("lastName is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var entityName = $"{request.FirstName} {request.LastName}";

        // CreateEntity returns base Entity — use dynamic to access Cardholder properties
        dynamic cardholder = engine.CreateEntity(entityName, EntityType.Cardholder);

        cardholder.FirstName = request.FirstName;
        cardholder.LastName = request.LastName;

        if (!string.IsNullOrEmpty(request.Email))
            cardholder.EmailAddress = request.Email;
        if (!string.IsNullOrEmpty(request.MobilePhone))
            cardholder.MobilePhoneNumber = request.MobilePhone;

        return new CardholderResponse { Guid = cardholder.Guid.ToString() };
    }

    public async Task<QueryCardholdersResponse> QueryCardholdersAsync()
    {
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var guids = await QueryEntitiesByTypeAsync(engine, "Cardholder");

        var cardholders = new List<CardholderInfo>();
        foreach (var guid in guids)
        {
            try
            {
                dynamic entity = engine.GetEntity(guid);
                if (entity == null) continue;

                var entityType = ((object)entity).GetType();

                var info = new CardholderInfo
                {
                    Guid = guid.ToString(),
                };

                // Read properties via reflection (not dynamic — per project conventions for some types)
                var firstNameProp = entityType.GetProperty("FirstName");
                if (firstNameProp != null)
                    info.FirstName = firstNameProp.GetValue(entity)?.ToString() ?? "";

                var lastNameProp = entityType.GetProperty("LastName");
                if (lastNameProp != null)
                    info.LastName = lastNameProp.GetValue(entity)?.ToString() ?? "";

                var emailProp = entityType.GetProperty("EmailAddress");
                if (emailProp != null)
                    info.EmailAddress = emailProp.GetValue(entity)?.ToString();

                var phoneProp = entityType.GetProperty("MobilePhoneNumber");
                if (phoneProp != null)
                    info.MobilePhone = phoneProp.GetValue(entity)?.ToString();

                // Read status
                info.Status = ReadEntityStatus(entity, entityType);

                cardholders.Add(info);
            }
            catch (Exception)
            {
                // Skip entities that can't be read
            }
        }

        return new QueryCardholdersResponse { Cardholders = cardholders };
    }

    private static string ReadEntityStatus(object entity, Type entityType)
    {
        try
        {
            var statusProp = entityType.GetProperty("Status");
            if (statusProp == null) return "Unknown";
            var statusObj = statusProp.GetValue(entity);
            if (statusObj == null) return "Unknown";

            var stateProp = statusObj.GetType().GetProperty("State");
            if (stateProp != null)
                return stateProp.GetValue(statusObj)?.ToString() ?? "Unknown";

            return statusObj.ToString() ?? "Unknown";
        }
        catch
        {
            return "Unknown";
        }
    }

    private async Task<List<Guid>> QueryEntitiesByTypeAsync(dynamic engine, string entityTypeName)
    {
        var reportTypeEnum = FindTypeByName("ReportType")
            ?? throw new InvalidOperationException("Could not find ReportType enum in loaded assemblies.");
        var entityTypeEnum = FindTypeByName("EntityType")
            ?? throw new InvalidOperationException("Could not find EntityType enum in loaded assemblies.");

        var entityConfigValue = Enum.Parse(reportTypeEnum, "EntityConfiguration");
        var entityTypeValue = Enum.Parse(entityTypeEnum, entityTypeName);

        var reportManager = (object)engine.ReportManager;
        var rmType = reportManager.GetType();
        var createQueryMethod = rmType.GetMethods()
            .FirstOrDefault(m => m.Name == "CreateReportQuery" && m.GetParameters().Length == 1
                && m.GetParameters()[0].ParameterType == reportTypeEnum)
            ?? throw new InvalidOperationException(
                $"Could not find CreateReportQuery({reportTypeEnum.Name}) on ReportManager.");

        var queryObj = createQueryMethod.Invoke(reportManager, new[] { entityConfigValue })!;
        var queryType = queryObj.GetType();

        var downloadProp = queryType.GetProperty("DownloadAllRelatedData");
        if (downloadProp != null)
            downloadProp.SetValue(queryObj, true);

        var pageSizeProp = queryType.GetProperty("PageSize");
        if (pageSizeProp != null)
            pageSizeProp.SetValue(queryObj, 5000);
        var pageProp = queryType.GetProperty("Page");
        if (pageProp != null)
            pageProp.SetValue(queryObj, 1);

        var filterProp = queryType.GetProperty("EntityTypeFilter")
            ?? throw new InvalidOperationException($"Could not find EntityTypeFilter on {queryType.Name}.");
        var filterObj = filterProp.GetValue(queryObj)!;
        var addMethod = filterObj.GetType().GetMethods()
            .FirstOrDefault(m => m.Name == "Add" && m.GetParameters().Length >= 1
                && m.GetParameters()[0].ParameterType == entityTypeEnum)
            ?? throw new InvalidOperationException(
                $"Could not find Add({entityTypeEnum.Name}) on {filterObj.GetType().Name}.");
        addMethod.Invoke(filterObj, new object[] { entityTypeValue, Array.Empty<byte>() });

        var beginMethod = queryType.GetMethods()
            .FirstOrDefault(m => m.Name == "BeginQuery"
                && m.GetParameters().Length == 2
                && m.GetParameters()[0].ParameterType == typeof(AsyncCallback)
                && m.GetParameters()[1].ParameterType == typeof(object))
            ?? throw new InvalidOperationException($"Could not find BeginQuery on {queryType.Name}.");
        var endMethod = queryType.GetMethod("EndQuery")
            ?? throw new InvalidOperationException($"Could not find EndQuery on {queryType.Name}.");

        var queryResult = await Task.Factory.FromAsync(
            (callback, state) => (IAsyncResult)beginMethod.Invoke(queryObj, new object[] { callback!, state! })!,
            ar => endMethod.Invoke(queryObj, new object[] { ar! }),
            null);

        var dataProp = queryResult!.GetType().GetProperty("Data")
            ?? throw new InvalidOperationException("Could not find Data property on query result.");
        var dataTable = (DataTable)dataProp.GetValue(queryResult)!;

        var guids = new List<Guid>();
        foreach (DataRow row in dataTable.Rows)
        {
            Guid guid;
            if (row.Table.Columns.Contains("Guid"))
                guid = (Guid)row["Guid"];
            else if (row.Table.Columns.Contains("EntityGuid"))
                guid = (Guid)row["EntityGuid"];
            else
                continue;

            guids.Add(guid);
        }

        return guids;
    }

    private static Type? FindTypeByName(string typeName)
    {
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            try
            {
                var type = assembly.GetTypes().FirstOrDefault(t => t.Name == typeName);
                if (type != null) return type;
            }
            catch
            {
                // Skip assemblies that can't be reflected
            }
        }
        return null;
    }
}
