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

        // Create a transaction via reflection (dynamic dispatch fails on SDK types)
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
                    // Create door entity via reflection
                    var entityManager = (object)engine.EntityManager;
                    var emType = entityManager.GetType();

                    // Find EntityType.Door enum value
                    var entityTypeEnum = FindTypeByName("EntityType")
                        ?? throw new InvalidOperationException("Could not find EntityType enum.");
                    var doorEntityType = Enum.Parse(entityTypeEnum, "Door");

                    // CreateEntity(name, entityType) — returns Guid
                    var createMethod = emType.GetMethods()
                        .FirstOrDefault(m => m.Name == "CreateEntity"
                            && m.GetParameters().Length == 2
                            && m.GetParameters()[0].ParameterType == typeof(string))
                        ?? throw new InvalidOperationException(
                            $"Could not find CreateEntity(string, EntityType) on EntityManager. " +
                            $"Available methods: {string.Join(", ", emType.GetMethods().Where(m => m.Name == "CreateEntity").Select(m => $"{m.Name}({string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"))})").Distinct())}");

                    var doorGuid = (Guid)createMethod.Invoke(entityManager, new object[] { door.Name, doorEntityType })!;

                    // Set door properties if provided
                    if (door.Properties != null)
                    {
                        dynamic doorEntity = engine.GetEntity(doorGuid);
                        var doorObj = (object)doorEntity;
                        var doorType = doorObj.GetType();

                        SetPropertyIfProvided(doorType, doorObj, "RelockDelay",
                            door.Properties.RelockDelayInSeconds.HasValue
                                ? TimeSpan.FromSeconds(door.Properties.RelockDelayInSeconds.Value)
                                : null);
                        SetPropertyIfProvided(doorType, doorObj, "StandardEntryTime",
                            door.Properties.StandardEntryTimeInSeconds.HasValue
                                ? TimeSpan.FromSeconds(door.Properties.StandardEntryTimeInSeconds.Value)
                                : null);
                        SetPropertyIfProvided(doorType, doorObj, "ExtendedEntryTime",
                            door.Properties.ExtendedEntryTimeInSeconds.HasValue
                                ? TimeSpan.FromSeconds(door.Properties.ExtendedEntryTimeInSeconds.Value)
                                : null);
                        SetPropertyIfProvided(doorType, doorObj, "StandardGrantTime",
                            door.Properties.StandardGrantTimeInSeconds.HasValue
                                ? TimeSpan.FromSeconds(door.Properties.StandardGrantTimeInSeconds.Value)
                                : null);
                        SetPropertyIfProvided(doorType, doorObj, "ExtendedGrantTime",
                            door.Properties.ExtendedGrantTimeInSeconds.HasValue
                                ? TimeSpan.FromSeconds(door.Properties.ExtendedGrantTimeInSeconds.Value)
                                : null);
                        SetPropertyIfProvided(doorType, doorObj, "RelockOnClose", door.Properties.RelockOnClose);
                        SetPropertyIfProvided(doorType, doorObj, "HeldOpenEventsEnabled", door.Properties.HeldOpenEventsEnabled);
                        SetPropertyIfProvided(doorType, doorObj, "ForcedOpenEventsEnabled", door.Properties.ForcedOpenEventsEnabled);
                    }

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

        // Create a transaction via reflection
        var transactionManager = (object)engine.TransactionManager;
        var tmType = transactionManager.GetType();
        var createTxMethod = tmType.GetMethod("CreateTransaction")
            ?? throw new InvalidOperationException("Could not find CreateTransaction on TransactionManager.");
        createTxMethod.Invoke(transactionManager, null);

        try
        {
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

                    // Configure entry side
                    if (assignment.Hardware.EntrySide != null)
                    {
                        ConfigureDoorSide(doorType, doorObj, "DoorSideIn", assignment.Hardware.EntrySide);
                    }

                    // Configure exit side
                    if (assignment.Hardware.ExitSide != null)
                    {
                        ConfigureDoorSide(doorType, doorObj, "DoorSideOut", assignment.Hardware.ExitSide);
                    }

                    // Configure door lock
                    if (!string.IsNullOrEmpty(assignment.Hardware.DoorLockGuid))
                    {
                        var lockGuid = Guid.Parse(assignment.Hardware.DoorLockGuid);
                        // Try setting DoorLock property or use SetDoorLock method
                        var lockProp = doorType.GetProperty("DoorLock");
                        if (lockProp != null && lockProp.CanWrite)
                        {
                            lockProp.SetValue(doorObj, lockGuid);
                        }
                        else
                        {
                            var setLockMethod = doorType.GetMethod("SetDoorLock")
                                ?? doorType.GetMethod("SetLock");
                            if (setLockMethod != null)
                                setLockMethod.Invoke(doorObj, new object[] { lockGuid });
                        }
                    }

                    results.Add(new DoorHardwareResult
                    {
                        DoorGuid = assignment.DoorGuid,
                        Status = "Configured",
                    });
                }
                catch (TargetInvocationException ex) when (ex.InnerException != null)
                {
                    results.Add(new DoorHardwareResult
                    {
                        DoorGuid = assignment.DoorGuid,
                        Status = $"Failed: {ex.InnerException.Message}",
                    });
                }
                catch (Exception ex) when (ex is not ArgumentException && ex is not InvalidOperationException)
                {
                    results.Add(new DoorHardwareResult
                    {
                        DoorGuid = assignment.DoorGuid,
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

        return results;
    }

    private static void ConfigureDoorSide(Type doorType, object doorObj, string sidePropName, DoorSideHardware hardware)
    {
        var sideProp = doorType.GetProperty(sidePropName);
        if (sideProp == null) return;

        var sideObj = sideProp.GetValue(doorObj);
        if (sideObj == null) return;

        var sideType = sideObj.GetType();

        if (!string.IsNullOrEmpty(hardware.ReaderGuid))
        {
            var readerGuid = Guid.Parse(hardware.ReaderGuid);
            var readerProp = sideType.GetProperty("Reader");
            if (readerProp != null && readerProp.CanWrite)
                readerProp.SetValue(sideObj, readerGuid);
            else
            {
                var setMethod = sideType.GetMethod("SetReader");
                setMethod?.Invoke(sideObj, new object[] { readerGuid });
            }
        }

        if (!string.IsNullOrEmpty(hardware.RexGuid))
        {
            var rexGuid = Guid.Parse(hardware.RexGuid);
            var rexProp = sideType.GetProperty("Rex");
            if (rexProp != null && rexProp.CanWrite)
                rexProp.SetValue(sideObj, rexGuid);
            else
            {
                var setMethod = sideType.GetMethod("SetRex");
                setMethod?.Invoke(sideObj, new object[] { rexGuid });
            }
        }

        if (!string.IsNullOrEmpty(hardware.DoorSensorGuid))
        {
            var sensorGuid = Guid.Parse(hardware.DoorSensorGuid);
            var sensorProp = sideType.GetProperty("DoorSensor") ?? sideType.GetProperty("EntrySensor");
            if (sensorProp != null && sensorProp.CanWrite)
                sensorProp.SetValue(sideObj, sensorGuid);
            else
            {
                var setMethod = sideType.GetMethod("SetDoorSensor") ?? sideType.GetMethod("SetEntrySensor");
                setMethod?.Invoke(sideObj, new object[] { sensorGuid });
            }
        }
    }

    private static void SetPropertyIfProvided(Type type, object obj, string propName, object? value)
    {
        if (value == null) return;
        var prop = type.GetProperty(propName);
        if (prop != null && prop.CanWrite)
        {
            prop.SetValue(obj, value);
        }
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
