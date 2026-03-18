using System.Data;
using Genetec.Sdk;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

public class CredentialService
{
    private readonly GenetecEngineService _engineService;

    public CredentialService(GenetecEngineService engineService)
    {
        _engineService = engineService;
    }

    public async Task<QueryCredentialsResponse> QueryCredentialsAsync()
    {
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var guids = await QueryEntitiesByTypeAsync(engine, "Credential");

        var credentials = new List<CredentialInfo>();
        foreach (var guid in guids)
        {
            try
            {
                dynamic entity = engine.GetEntity(guid);
                if (entity == null) continue;

                var entityType = ((object)entity).GetType();

                var info = new CredentialInfo
                {
                    Guid = guid.ToString(),
                };

                // Name
                var nameProp = entityType.GetProperty("Name");
                if (nameProp != null)
                    info.Name = nameProp.GetValue(entity)?.ToString() ?? "";

                // Format
                try
                {
                    var formatProp = entityType.GetProperty("Format");
                    if (formatProp != null)
                    {
                        var formatObj = formatProp.GetValue(entity);
                        if (formatObj != null)
                        {
                            var formatNameProp = formatObj.GetType().GetProperty("Name");
                            info.FormatType = formatNameProp != null
                                ? formatNameProp.GetValue(formatObj)?.ToString() ?? formatObj.ToString() ?? "Unknown"
                                : formatObj.ToString() ?? "Unknown";
                        }
                    }
                }
                catch
                {
                    info.FormatType = "Unknown";
                }

                // CardholderGuid
                try
                {
                    var chGuidProp = entityType.GetProperty("CardholderGuid");
                    if (chGuidProp != null)
                    {
                        var chGuid = (Guid)chGuidProp.GetValue(entity)!;
                        if (chGuid != Guid.Empty)
                        {
                            info.CardholderGuid = chGuid.ToString();
                            // Try to get cardholder name
                            try
                            {
                                dynamic chEntity = engine.GetEntity(chGuid);
                                if (chEntity != null)
                                {
                                    var chType = ((object)chEntity).GetType();
                                    var fnProp = chType.GetProperty("FirstName");
                                    var lnProp = chType.GetProperty("LastName");
                                    var fn = fnProp?.GetValue(chEntity)?.ToString() ?? "";
                                    var ln = lnProp?.GetValue(chEntity)?.ToString() ?? "";
                                    info.CardholderName = $"{fn} {ln}".Trim();
                                }
                            }
                            catch { }
                        }
                    }
                }
                catch { }

                // Status
                info.Status = ReadEntityStatus(entity, entityType);

                credentials.Add(info);
            }
            catch (Exception)
            {
                // Skip entities that can't be read
            }
        }

        return new QueryCredentialsResponse { Credentials = credentials };
    }

    public CredentialResponse CreateCredential(CredentialRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Name))
            throw new ArgumentException("name is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.FormatType))
            throw new ArgumentException("formatType is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;

        // Create the credential format based on formatType
        dynamic credentialFormat = CreateFormat(request);

        // Get the credential builder via reflection (SDK builder/manager pattern)
        var entityManager = engine.EntityManager;
        var getBuilderMethod = entityManager.GetType().GetMethod("GetCredentialBuilder")
            ?? throw new InvalidOperationException("GetCredentialBuilder method not found on EntityManager.");
        var builderObj = getBuilderMethod.Invoke(entityManager, null)
            ?? throw new InvalidOperationException("GetCredentialBuilder returned null.");

        // Use reflection for builder methods (dynamic dispatch fails on SDK builder types)
        var builderType = builderObj.GetType();

        var setNameMethod = builderType.GetMethod("SetName")
            ?? throw new InvalidOperationException("SetName method not found on credential builder.");
        setNameMethod.Invoke(builderObj, new object[] { request.Name });

        var setFormatMethod = builderType.GetMethod("SetFormat")
            ?? throw new InvalidOperationException("SetFormat method not found on credential builder.");
        setFormatMethod.Invoke(builderObj, new object[] { credentialFormat });

        var buildMethod = builderType.GetMethod("Build")
            ?? throw new InvalidOperationException("Build method not found on credential builder.");
        var credentialObj = buildMethod.Invoke(builderObj, null)
            ?? throw new InvalidOperationException("Build returned null.");

        var guidProp = credentialObj.GetType().GetProperty("Guid")
            ?? throw new InvalidOperationException("Guid property not found on credential.");
        var credentialGuid = (Guid)guidProp.GetValue(credentialObj)!;
        string credentialGuidStr = credentialGuid.ToString();

        // Assign to cardholder if specified
        if (!string.IsNullOrEmpty(request.CardholderGuid))
        {
            var cardholderGuidParsed = new Guid(request.CardholderGuid);
            dynamic cardholder = engine.GetEntity(cardholderGuidParsed);
            if (cardholder != null)
            {
                cardholder.Credentials.Add(credentialGuid);
            }
        }

        return new CredentialResponse { Guid = credentialGuidStr };
    }

    public AssignCredentialResponse AssignCredential(AssignCredentialRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.CredentialGuid))
            throw new ArgumentException("credentialGuid is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.CardholderGuid))
            throw new ArgumentException("cardholderGuid is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var credentialGuid = new Guid(request.CredentialGuid);
        var cardholderGuid = new Guid(request.CardholderGuid);

        // Get credential entity to check current assignment
        dynamic credential = engine.GetEntity(credentialGuid);
        if (credential == null)
            throw new InvalidOperationException($"Credential entity '{request.CredentialGuid}' not found.");

        Guid previousCardholderGuid = credential.CardholderGuid;
        string? previousCardholderGuidStr = previousCardholderGuid != Guid.Empty
            ? previousCardholderGuid.ToString()
            : null;

        // If already assigned to a different cardholder, unassign first
        if (previousCardholderGuid != Guid.Empty && previousCardholderGuid != cardholderGuid)
        {
            credential.CardholderGuid = Guid.Empty;
        }

        // Assign to the new cardholder
        dynamic cardholder = engine.GetEntity(cardholderGuid);
        if (cardholder == null)
            throw new InvalidOperationException($"Cardholder entity '{request.CardholderGuid}' not found.");

        cardholder.Credentials.Add(credentialGuid);

        return new AssignCredentialResponse
        {
            CredentialGuid = request.CredentialGuid,
            CardholderGuid = request.CardholderGuid,
            PreviousCardholderGuid = previousCardholderGuidStr,
        };
    }

    private static object CreateFormat(CredentialRequest request)
    {
        // Load credential format types from SDK assembly
        var sdkAssembly = typeof(EntityType).Assembly;

        var typeName = request.FormatType switch
        {
            "WiegandStandard26Bit" => "Genetec.Sdk.Credentials.WiegandStandardCredentialFormat",
            "WiegandH10306" => "Genetec.Sdk.Credentials.WiegandH10306CredentialFormat",
            "WiegandH10304" => "Genetec.Sdk.Credentials.WiegandH10304CredentialFormat",
            "WiegandH10302" => "Genetec.Sdk.Credentials.WiegandH10302CredentialFormat",
            "WiegandCsn32" => "Genetec.Sdk.Credentials.WiegandCsn32CredentialFormat",
            "WiegandCorporate1000" => "Genetec.Sdk.Credentials.WiegandCorporate1000CredentialFormat",
            "Wiegand48BitCorporate1000" => "Genetec.Sdk.Credentials.Wiegand48BitCorporate1000CredentialFormat",
            "Keypad" => "Genetec.Sdk.Credentials.KeypadCredentialFormat",
            "LicensePlate" => "Genetec.Sdk.Credentials.LicensePlateCredentialFormat",
            "RawCard" => "Genetec.Sdk.Credentials.RawCardCredentialFormat",
            _ => throw new ArgumentException($"Unknown formatType '{request.FormatType}'.")
        };

        var formatType = sdkAssembly.GetType(typeName)
            ?? throw new InvalidOperationException($"SDK type '{typeName}' not found in assembly.");

        object[] args = request.FormatType switch
        {
            "WiegandH10302" or "WiegandCsn32" => new object[] { request.CardId ?? 0 },
            "Keypad" => new object[] { request.Code ?? 0 },
            "LicensePlate" => new object[] { request.LicensePlate ?? "" },
            "RawCard" => new object[] { request.RawData ?? "", request.BitLength ?? 0 },
            _ => new object[] { request.Facility ?? 0, request.CardId ?? 0 }
        };

        return Activator.CreateInstance(formatType, args)
            ?? throw new InvalidOperationException($"Failed to create instance of '{typeName}'.");
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
