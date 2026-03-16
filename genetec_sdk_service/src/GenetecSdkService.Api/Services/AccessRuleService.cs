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
                        var doorObj = (object)doorEntity;
                        var addAccessRuleMethod = doorObj.GetType().GetMethod("AddAccessRule")
                            ?? throw new InvalidOperationException(
                                $"Could not find AddAccessRule on {doorObj.GetType().Name}.");
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
