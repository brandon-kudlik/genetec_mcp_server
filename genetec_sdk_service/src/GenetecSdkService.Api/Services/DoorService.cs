using System.Reflection;
using Genetec.Sdk;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

/// <summary>
/// Service for door entity creation and hardware configuration.
/// </summary>
public class DoorService
{
    private readonly GenetecEngineService _engineService;

    public DoorService(GenetecEngineService engineService)
    {
        _engineService = engineService;
    }

    public BatchCreateDoorsResponse BatchCreateDoors(BatchCreateDoorsRequest request)
    {
        if (request.Doors == null || request.Doors.Count == 0)
            throw new ArgumentException("doors is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var results = new List<DoorResult>();

        // Create a transaction via reflection (dynamic dispatch fails on TransactionManager)
        var transactionManager = (object)engine.TransactionManager;
        var tmType = transactionManager.GetType();
        var createTxMethod = tmType.GetMethod("CreateTransaction")
            ?? throw new InvalidOperationException("Could not find CreateTransaction on TransactionManager.");
        createTxMethod.Invoke(transactionManager, null);

        try
        {
            foreach (var door in request.Doors)
            {
                if (string.IsNullOrWhiteSpace(door.Name))
                    throw new ArgumentException("Each door must contain a 'name'.");

                try
                {
                    // Create door entity using dynamic dispatch (same pattern as CardholderService)
                    dynamic doorEntity = engine.CreateEntity(door.Name, EntityType.Door);
                    var doorGuid = (Guid)doorEntity.Guid;

                    results.Add(new DoorResult
                    {
                        Name = door.Name,
                        Guid = doorGuid.ToString(),
                        Status = "Created",
                    });
                }
                catch (TargetInvocationException ex) when (ex.InnerException != null)
                {
                    results.Add(new DoorResult
                    {
                        Name = door.Name,
                        Status = $"Failed: {ex.InnerException.Message}",
                    });
                }
                catch (Exception ex) when (ex is not ArgumentException && ex is not InvalidOperationException)
                {
                    results.Add(new DoorResult
                    {
                        Name = door.Name,
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

        return new BatchCreateDoorsResponse
        {
            Results = results,
            CreatedCount = results.Count(r => r.Status == "Created"),
        };
    }

    public BatchConfigureDoorHardwareResponse ConfigureDoorHardware(BatchConfigureDoorHardwareRequest request)
    {
        if (request.Assignments == null || request.Assignments.Count == 0)
            throw new ArgumentException("assignments is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var results = new List<DoorHardwareResult>();

        // Resolve AccessPointType enum via reflection
        var accessPointTypeEnum = FindTypeByName("AccessPointType")
            ?? throw new InvalidOperationException("Could not find AccessPointType enum in loaded assemblies.");

        foreach (var assignment in request.Assignments)
        {
            if (string.IsNullOrWhiteSpace(assignment.DoorGuid))
                throw new ArgumentException("Each assignment must contain a 'doorGuid'.");

            try
            {
                var doorGuid = Guid.Parse(assignment.DoorGuid);
                dynamic doorEntity = engine.GetEntity(doorGuid);
                if (doorEntity == null)
                    throw new InvalidOperationException($"Door entity not found: {assignment.DoorGuid}");

                var doorObj = (object)doorEntity;
                var doorType = doorObj.GetType();

                // Find AddConnection method
                var addConnectionMethod = doorType.GetMethod("AddConnection")
                    ?? throw new InvalidOperationException(
                        $"Could not find AddConnection on {doorType.Name}.");

                // Assign door lock via AddConnection with AccessPointType.DoorLock
                if (!string.IsNullOrEmpty(assignment.Hardware.DoorLockGuid))
                {
                    AddHardwareConnection(addConnectionMethod, doorObj, accessPointTypeEnum,
                        assignment.Hardware.DoorLockGuid, "DoorLock");
                }

                // Entry side hardware connections
                if (assignment.Hardware.EntrySide != null)
                {
                    AddHardwareConnection(addConnectionMethod, doorObj, accessPointTypeEnum,
                        assignment.Hardware.EntrySide.ReaderGuid, "CardReader");
                    AddHardwareConnection(addConnectionMethod, doorObj, accessPointTypeEnum,
                        assignment.Hardware.EntrySide.RexGuid, "Rex");
                    AddHardwareConnection(addConnectionMethod, doorObj, accessPointTypeEnum,
                        assignment.Hardware.EntrySide.DoorSensorGuid, "EntrySensor");
                }

                // Exit side hardware connections
                if (assignment.Hardware.ExitSide != null)
                {
                    AddHardwareConnection(addConnectionMethod, doorObj, accessPointTypeEnum,
                        assignment.Hardware.ExitSide.ReaderGuid, "CardReader");
                    AddHardwareConnection(addConnectionMethod, doorObj, accessPointTypeEnum,
                        assignment.Hardware.ExitSide.RexGuid, "Rex");
                    AddHardwareConnection(addConnectionMethod, doorObj, accessPointTypeEnum,
                        assignment.Hardware.ExitSide.DoorSensorGuid, "EntrySensor");
                }

                results.Add(new DoorHardwareResult
                {
                    DoorGuid = assignment.DoorGuid,
                    Status = "Configured",
                });
            }
            catch (TargetInvocationException ex)
            {
                var inner = ex.InnerException ?? ex;
                while (inner.InnerException != null) inner = inner.InnerException;
                results.Add(new DoorHardwareResult
                {
                    DoorGuid = assignment.DoorGuid,
                    Status = $"Failed: [{inner.GetType().Name}] {inner.Message} | Stack: {inner.StackTrace?.Split('\n').FirstOrDefault()?.Trim()}",
                });
            }
            catch (Exception ex) when (ex is not ArgumentException && ex is not InvalidOperationException)
            {
                results.Add(new DoorHardwareResult
                {
                    DoorGuid = assignment.DoorGuid,
                    Status = $"Failed: [{ex.GetType().Name}] {ex.Message}",
                });
            }
        }

        return new BatchConfigureDoorHardwareResponse
        {
            Results = results,
            ConfiguredCount = results.Count(r => r.Status == "Configured"),
        };
    }

    /// <summary>
    /// Diagnostic: inspect Door entity properties and methods for SDK discovery.
    /// </summary>
    public List<string> InspectDoorEntity(string doorGuid)
    {
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var guid = Guid.Parse(doorGuid);
        var results = new List<string>();

        dynamic entity = engine.GetEntity(guid);
        if (entity == null)
            throw new InvalidOperationException($"Entity not found: {doorGuid}");

        var entityObj = (object)entity;
        results.Add($"Entity type: {entityObj.GetType().FullName}");

        // List all properties
        foreach (var prop in entityObj.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
        {
            try
            {
                var val = prop.GetValue(entityObj);
                var valStr = val?.ToString() ?? "null";
                if (valStr.Length > 200) valStr = valStr[..200] + "...";
                var rw = prop.CanWrite ? "RW" : "RO";
                results.Add($"  [{rw}] {prop.PropertyType.Name} {prop.Name} = {valStr}");

                // Drill into DoorSide types
                if ((prop.Name == "DoorSideIn" || prop.Name == "DoorSideOut") && val != null)
                {
                    var sideType = val.GetType();
                    results.Add($"    DoorSide type: {sideType.FullName}");
                    foreach (var sProp in sideType.GetProperties(BindingFlags.Public | BindingFlags.Instance))
                    {
                        try
                        {
                            var sVal = sProp.GetValue(val);
                            var sRw = sProp.CanWrite ? "RW" : "RO";
                            results.Add($"    [{sRw}] {sProp.PropertyType.Name} {sProp.Name} = {sVal}");
                        }
                        catch (Exception ex2)
                        {
                            results.Add($"    {sProp.PropertyType.Name} {sProp.Name} = ERROR: {ex2.InnerException?.Message ?? ex2.Message}");
                        }
                    }
                    foreach (var sMethod in sideType.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
                    {
                        var paramList = string.Join(", ", sMethod.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"));
                        results.Add($"    Method: {sMethod.ReturnType.Name} {sMethod.Name}({paramList})");
                    }
                }

                // Drill into DoorHeld / DoorForced sub-objects
                if ((prop.Name == "DoorHeld" || prop.Name == "DoorForced") && val != null)
                {
                    var subType = val.GetType();
                    results.Add($"    {prop.Name} type: {subType.FullName}");
                    foreach (var sProp in subType.GetProperties(BindingFlags.Public | BindingFlags.Instance))
                    {
                        try
                        {
                            var sVal = sProp.GetValue(val);
                            var sRw = sProp.CanWrite ? "RW" : "RO";
                            results.Add($"    [{sRw}] {sProp.PropertyType.Name} {sProp.Name} = {sVal}");
                        }
                        catch (Exception ex2)
                        {
                            results.Add($"    {sProp.PropertyType.Name} {sProp.Name} = ERROR: {ex2.InnerException?.Message ?? ex2.Message}");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                results.Add($"  {prop.PropertyType.Name} {prop.Name} = ERROR: {ex.InnerException?.Message ?? ex.Message}");
            }
        }

        // List all declared methods
        results.Add("\nDeclared Methods:");
        foreach (var method in entityObj.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
        {
            var paramList = string.Join(", ", method.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"));
            results.Add($"  {method.ReturnType.Name} {method.Name}({paramList})");
        }

        // Enumerate AccessPointType enum values
        var accessPointTypeEnum = FindTypeByName("AccessPointType");
        if (accessPointTypeEnum != null)
        {
            results.Add($"\nAccessPointType enum values:");
            var underlyingType = Enum.GetUnderlyingType(accessPointTypeEnum);
            foreach (var name in Enum.GetNames(accessPointTypeEnum))
            {
                var val = Enum.Parse(accessPointTypeEnum, name);
                results.Add($"  {name} = {Convert.ChangeType(val, underlyingType)}");
            }
        }

        return results;
    }

    private static void AddHardwareConnection(MethodInfo addConnectionMethod, object doorObj, Type accessPointTypeEnum, string? deviceGuid, string accessPointTypeName)
    {
        if (string.IsNullOrEmpty(deviceGuid)) return;

        var device = Guid.Parse(deviceGuid);
        var apType = Enum.Parse(accessPointTypeEnum, accessPointTypeName);
        addConnectionMethod.Invoke(doorObj, new object[] { device, apType });
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
