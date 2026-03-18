using System.Data;
using System.Reflection;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

/// <summary>
/// Service for access rule (access level) creation and door assignment.
/// </summary>
public class AccessRuleService
{
    private readonly GenetecEngineService _engineService;

    public AccessRuleService(GenetecEngineService engineService)
    {
        _engineService = engineService;
    }

    public BatchCreateAccessRulesResponse BatchCreateAccessRules(BatchCreateAccessRulesRequest request)
    {
        if (request.AccessRules == null || request.AccessRules.Count == 0)
            throw new ArgumentException("accessRules is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var results = new List<AccessRuleResult>();

        // Resolve SDK enum types via reflection
        var accessRuleTypeEnum = FindTypeByName("AccessRuleType")
            ?? throw new InvalidOperationException("Could not find AccessRuleType enum in loaded assemblies.");
        var accessRuleSideEnum = FindTypeByName("AccessRuleSide")
            ?? throw new InvalidOperationException("Could not find AccessRuleSide enum in loaded assemblies.");

        // Create a transaction via reflection
        var transactionManager = (object)engine.TransactionManager;
        var tmType = transactionManager.GetType();
        var createTxMethod = tmType.GetMethod("CreateTransaction")
            ?? throw new InvalidOperationException("Could not find CreateTransaction on TransactionManager.");
        createTxMethod.Invoke(transactionManager, null);

        try
        {
            foreach (var rule in request.AccessRules)
            {
                if (string.IsNullOrWhiteSpace(rule.Name))
                    throw new ArgumentException("Each access rule must contain a 'name'.");

                try
                {
                    // Parse the AccessRuleType.Permanent enum value
                    var permanentType = Enum.Parse(accessRuleTypeEnum, "Permanent");

                    // Create access rule via reflection (takes SDK enum parameter)
                    var engineObj = (object)engine;
                    var createMethod = engineObj.GetType().GetMethod("CreateAccessRule")
                        ?? throw new InvalidOperationException("Could not find CreateAccessRule on Engine.");
                    var ruleEntity = createMethod.Invoke(engineObj, new object[] { rule.Name, permanentType });

                    if (ruleEntity == null)
                        throw new InvalidOperationException($"CreateAccessRule returned null for '{rule.Name}'.");

                    var ruleGuid = (Guid)((dynamic)ruleEntity).Guid;

                    // Parse the side enum value
                    var sideValue = Enum.Parse(accessRuleSideEnum, rule.Side ?? "Both");

                    // Assign doors to this access rule
                    int doorsAssigned = 0;
                    foreach (var doorGuidStr in rule.DoorGuids ?? new List<string>())
                    {
                        var doorGuid = Guid.Parse(doorGuidStr);
                        dynamic doorEntity = engine.GetEntity(doorGuid);
                        if (doorEntity == null)
                            throw new InvalidOperationException($"Door entity not found: {doorGuidStr}");

                        // Call door.AddAccessRule(ruleGuid, side) via reflection
                        // Multiple overloads exist — select the 2-parameter one (Guid, AccessRuleSide)
                        var doorObj = (object)doorEntity;
                        var addAccessRuleMethod = doorObj.GetType().GetMethods()
                            .FirstOrDefault(m => m.Name == "AddAccessRule" && m.GetParameters().Length == 2)
                            ?? throw new InvalidOperationException(
                                $"Could not find AddAccessRule(Guid, AccessRuleSide) on {doorObj.GetType().Name}.");
                        addAccessRuleMethod.Invoke(doorObj, new object[] { ruleGuid, sideValue });
                        doorsAssigned++;
                    }

                    results.Add(new AccessRuleResult
                    {
                        Name = rule.Name,
                        Guid = ruleGuid.ToString(),
                        DoorsAssigned = doorsAssigned,
                        Status = "Created",
                    });
                }
                catch (TargetInvocationException ex) when (ex.InnerException != null)
                {
                    results.Add(new AccessRuleResult
                    {
                        Name = rule.Name,
                        Status = $"Failed: {ex.InnerException.Message}",
                    });
                }
                catch (Exception ex) when (ex is not ArgumentException && ex is not InvalidOperationException)
                {
                    results.Add(new AccessRuleResult
                    {
                        Name = rule.Name,
                        Status = $"Failed: {ex.Message}",
                    });
                }
            }

            // Commit the transaction
            var commitMethod = tmType.GetMethods()
                .FirstOrDefault(m => m.Name == "CommitTransaction" && m.GetParameters().Length == 1
                    && m.GetParameters()[0].ParameterType == typeof(bool))
                ?? tmType.GetMethods().FirstOrDefault(m => m.Name == "CommitTransaction" && m.GetParameters().Length == 0)
                ?? throw new InvalidOperationException("Could not find CommitTransaction on TransactionManager.");
            if (commitMethod.GetParameters().Length == 1)
                commitMethod.Invoke(transactionManager, new object[] { true });
            else
                commitMethod.Invoke(transactionManager, null);
        }
        catch
        {
            var rollbackMethod = tmType.GetMethod("RollbackTransaction");
            if (rollbackMethod != null)
            {
                try { rollbackMethod.Invoke(transactionManager, null); }
                catch { /* best-effort rollback */ }
            }
            throw;
        }

        return new BatchCreateAccessRulesResponse
        {
            Results = results,
            CreatedCount = results.Count(r => r.Status == "Created"),
        };
    }

    public async Task<QueryAccessRulesResponse> QueryAccessRulesAsync()
    {
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var guids = await QueryEntitiesByTypeAsync(engine, "AccessRule");

        var accessRules = new List<AccessRuleInfo>();
        foreach (var guid in guids)
        {
            try
            {
                dynamic entity = engine.GetEntity(guid);
                if (entity == null) continue;

                var entityType = ((object)entity).GetType();
                var info = new AccessRuleInfo { Guid = guid.ToString() };

                var nameProp = entityType.GetProperty("Name");
                if (nameProp != null)
                    info.Name = nameProp.GetValue(entity)?.ToString() ?? "";

                accessRules.Add(info);
            }
            catch
            {
                // Skip entities that can't be read
            }
        }

        return new QueryAccessRulesResponse { AccessRules = accessRules };
    }

    public AssignAccessRulesResponse AssignAccessRules(AssignAccessRulesRequest request)
    {
        if (request.AccessRuleGuids == null || request.AccessRuleGuids.Count == 0)
            throw new ArgumentException("accessRuleGuids is required and cannot be empty.");
        if (request.CardholderGuids == null || request.CardholderGuids.Count == 0)
            throw new ArgumentException("cardholderGuids is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var results = new List<AccessRuleAssignmentResult>();

        var transactionManager = (object)engine.TransactionManager;
        var tmType = transactionManager.GetType();
        var createTxMethod = tmType.GetMethod("CreateTransaction")
            ?? throw new InvalidOperationException("Could not find CreateTransaction on TransactionManager.");
        createTxMethod.Invoke(transactionManager, null);

        try
        {
            foreach (var accessRuleGuidStr in request.AccessRuleGuids)
            {
                foreach (var cardholderGuidStr in request.CardholderGuids)
                {
                    try
                    {
                        var accessRuleGuid = Guid.Parse(accessRuleGuidStr);
                        var cardholderGuid = Guid.Parse(cardholderGuidStr);

                        dynamic accessRule = engine.GetEntity(accessRuleGuid);
                        if (accessRule == null)
                        {
                            results.Add(new AccessRuleAssignmentResult
                            {
                                AccessRuleGuid = accessRuleGuidStr,
                                CardholderGuid = cardholderGuidStr,
                                Status = "Failed",
                                Error = $"Access rule entity not found: {accessRuleGuidStr}",
                            });
                            continue;
                        }

                        accessRule.AddCardholders(cardholderGuid);

                        results.Add(new AccessRuleAssignmentResult
                        {
                            AccessRuleGuid = accessRuleGuidStr,
                            CardholderGuid = cardholderGuidStr,
                            Status = "Assigned",
                        });
                    }
                    catch (Exception ex)
                    {
                        var inner = ex;
                        while (inner.InnerException != null) inner = inner.InnerException;
                        results.Add(new AccessRuleAssignmentResult
                        {
                            AccessRuleGuid = accessRuleGuidStr,
                            CardholderGuid = cardholderGuidStr,
                            Status = "Failed",
                            Error = inner.Message,
                        });
                    }
                }
            }

            var commitMethod = tmType.GetMethods()
                .FirstOrDefault(m => m.Name == "CommitTransaction" && m.GetParameters().Length == 1
                    && m.GetParameters()[0].ParameterType == typeof(bool))
                ?? tmType.GetMethods().FirstOrDefault(m => m.Name == "CommitTransaction" && m.GetParameters().Length == 0)
                ?? throw new InvalidOperationException("Could not find CommitTransaction on TransactionManager.");
            if (commitMethod.GetParameters().Length == 1)
                commitMethod.Invoke(transactionManager, new object[] { true });
            else
                commitMethod.Invoke(transactionManager, null);
        }
        catch
        {
            var rollbackMethod = tmType.GetMethod("RollbackTransaction");
            if (rollbackMethod != null)
            {
                try { rollbackMethod.Invoke(transactionManager, null); }
                catch { /* best-effort rollback */ }
            }
            throw;
        }

        return new AssignAccessRulesResponse { Assignments = results };
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
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            try
            {
                foreach (var t in asm.GetTypes())
                {
                    if (t.Name == typeName)
                        return t;
                }
            }
            catch (ReflectionTypeLoadException)
            {
                // Some assemblies may fail to enumerate types — skip them
            }
        }
        return null;
    }
}
