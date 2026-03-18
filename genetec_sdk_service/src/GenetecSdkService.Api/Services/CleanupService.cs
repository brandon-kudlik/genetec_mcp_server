using System.Data;
using System.Reflection;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

public class CleanupService
{
    private readonly GenetecEngineService _engineService;
    private readonly ILogger<CleanupService> _logger;

    // Deletion order: bottom-up by dependency
    private static readonly string[] EntityTypesToDelete =
    {
        "AccessRule",
        "Alarm",
        "Door",
        "Cardholder",
        "Credential",
        "InterfaceModule",
    };

    public CleanupService(GenetecEngineService engineService, ILogger<CleanupService> logger)
    {
        _engineService = engineService;
        _logger = logger;
    }

    public async Task<CleanupDemoResponse> CleanupDemoAsync()
    {
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var response = new CleanupDemoResponse();
        var totalDeleted = 0;

        foreach (var entityTypeName in EntityTypesToDelete)
        {
            var typeResult = new CleanupEntityTypeResult { EntityType = entityTypeName };

            try
            {
                var guids = await QueryEntitiesByTypeAsync(engine, entityTypeName);
                typeResult.Found = guids.Count;
                _logger.LogInformation("Cleanup: found {Count} {Type} entities to delete.", guids.Count, entityTypeName);

                foreach (var guid in guids)
                {
                    try
                    {
                        engine.DeleteEntity(guid);
                        typeResult.Deleted++;
                        totalDeleted++;
                    }
                    catch (Exception ex)
                    {
                        var errorMsg = $"Failed to delete {entityTypeName} {guid}: {ex.Message}";
                        _logger.LogWarning(errorMsg);
                        typeResult.Errors.Add(errorMsg);
                    }
                }
            }
            catch (Exception ex)
            {
                var errorMsg = $"Failed to query {entityTypeName}: {ex.Message}";
                _logger.LogWarning(errorMsg);
                typeResult.Errors.Add(errorMsg);
            }

            response.Results.Add(typeResult);
        }

        response.TotalDeleted = totalDeleted;
        return response;
    }

    private async Task<List<Guid>> QueryEntitiesByTypeAsync(dynamic engine, string entityTypeName)
    {
        // Resolve SDK enum types via reflection
        var reportTypeEnum = FindTypeByName("ReportType")
            ?? throw new InvalidOperationException("Could not find ReportType enum in loaded assemblies.");
        var entityTypeEnum = FindTypeByName("EntityType")
            ?? throw new InvalidOperationException("Could not find EntityType enum in loaded assemblies.");

        var entityConfigValue = Enum.Parse(reportTypeEnum, "EntityConfiguration");
        var entityTypeValue = Enum.Parse(entityTypeEnum, entityTypeName);

        // Create query via reflection on ReportManager
        var reportManager = (object)engine.ReportManager;
        var rmType = reportManager.GetType();
        var createQueryMethod = rmType.GetMethods()
            .FirstOrDefault(m => m.Name == "CreateReportQuery" && m.GetParameters().Length == 1
                && m.GetParameters()[0].ParameterType == reportTypeEnum)
            ?? throw new InvalidOperationException(
                $"Could not find CreateReportQuery({reportTypeEnum.Name}) on ReportManager.");

        var queryObj = createQueryMethod.Invoke(reportManager, new[] { entityConfigValue })!;
        var queryType = queryObj.GetType();

        // Set DownloadAllRelatedData = true
        var downloadProp = queryType.GetProperty("DownloadAllRelatedData");
        if (downloadProp != null)
            downloadProp.SetValue(queryObj, true);

        // Set paging
        var pageSizeProp = queryType.GetProperty("PageSize");
        if (pageSizeProp != null)
            pageSizeProp.SetValue(queryObj, 5000);
        var pageProp = queryType.GetProperty("Page");
        if (pageProp != null)
            pageProp.SetValue(queryObj, 1);

        // Filter to specific entity type
        var filterProp = queryType.GetProperty("EntityTypeFilter")
            ?? throw new InvalidOperationException($"Could not find EntityTypeFilter on {queryType.Name}.");
        var filterObj = filterProp.GetValue(queryObj)!;
        var addMethod = filterObj.GetType().GetMethods()
            .FirstOrDefault(m => m.Name == "Add" && m.GetParameters().Length >= 1
                && m.GetParameters()[0].ParameterType == entityTypeEnum)
            ?? throw new InvalidOperationException(
                $"Could not find Add({entityTypeEnum.Name}) on {filterObj.GetType().Name}.");
        addMethod.Invoke(filterObj, new object[] { entityTypeValue, Array.Empty<byte>() });

        // Execute query via BeginQuery/EndQuery async pattern
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

        // Extract GUIDs from results
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
            catch (ReflectionTypeLoadException)
            {
                // Skip assemblies that can't be fully loaded
            }
        }
        return null;
    }
}
