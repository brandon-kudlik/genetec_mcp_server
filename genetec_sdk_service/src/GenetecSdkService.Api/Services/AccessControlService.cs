using System.Net;
using System.Reflection;
using System.Security;
using Genetec.Sdk;
using Genetec.Sdk.Entities.AccessControl;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

/// <summary>
/// Service for access control operations (Cloudlink enrollment, Mercury controllers).
/// </summary>
public class AccessControlService
{
    private readonly GenetecEngineService _engineService;

    private static readonly HashSet<string> ValidMercuryTypes = new()
    {
        "EP1501", "EP1501WithExpansion", "EP1502", "EP2500", "EP4502",
        "LP1501", "LP1501WithExpansion", "LP1502", "LP2500", "LP4502",
        "MP1501", "MP1501WithExpansion", "MP1502", "MP2500", "MP4502",
        "M5IC", "MSICS",
    };

    public AccessControlService(GenetecEngineService engineService)
    {
        _engineService = engineService;
    }

    public async Task<CloudlinkResponse> AddCloudlinkUnitAsync(CloudlinkRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Name))
            throw new ArgumentException("name is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.IpAddress))
            throw new ArgumentException("ipAddress is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.AccessManagerGuid))
            throw new ArgumentException("accessManagerGuid is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var securePassword = new SecureString();
        foreach (var ch in request.Password)
            securePassword.AppendChar(ch);

        var info = new AddAccessControlUnitInfo(
            address: IPAddress.Parse(request.IpAddress),
            extensionType: AccessControlExtensionType.CloudLink,
            port: 80,
            username: request.Username,
            password: securePassword
        );

        var roleGuid = Guid.Parse(request.AccessManagerGuid);

        var tcs = new TaskCompletionSource<string>();

        // Use EventHandler<EventArgs> for success, and dynamic event wiring
        // for the failed event since AddUnitProgressEventArgs lives in an
        // SDK namespace not directly importable from our assembly reference.
        EventHandler<EventArgs> onSuccess = (sender, e) =>
        {
            tcs.TrySetResult("success");
        };

        // Wire the failed event via dynamic to avoid needing the exact EventArgs type
        dynamic mgr = engine.AccessControlUnitManager;
        mgr.UnitEnrollmentSucceeded += onSuccess;

        // Use a lambda that accepts dynamic args to sidestep the type resolution
        EventHandler<dynamic> onFailed = (sender, e) =>
        {
            tcs.TrySetResult($"failed:{e.ActionDetails}");
        };
        mgr.UnitEnrollmentFailed += onFailed;

        try
        {
            mgr.EnrollAccessControlUnit(info, roleGuid);

            var timeoutTask = Task.Delay(TimeSpan.FromSeconds(60));
            var completed = await Task.WhenAny(tcs.Task, timeoutTask);

            if (completed == timeoutTask)
                throw new TimeoutException("Unit enrollment timed out after 60 seconds.");

            var result = await tcs.Task;
            if (result.StartsWith("failed:"))
                throw new InvalidOperationException($"Unit enrollment failed: {result[7..]}");

            return new CloudlinkResponse { Name = request.Name };
        }
        finally
        {
            mgr.UnitEnrollmentSucceeded -= onSuccess;
            mgr.UnitEnrollmentFailed -= onFailed;
        }
    }

    public MercuryControllerResponse AddMercuryController(string unitGuid, MercuryControllerRequest request)
    {
        if (string.IsNullOrWhiteSpace(unitGuid))
            throw new ArgumentException("unitGuid is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.Name))
            throw new ArgumentException("name is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.ControllerType))
            throw new ArgumentException("controllerType is required and cannot be empty.");
        if (!ValidMercuryTypes.Contains(request.ControllerType))
            throw new ArgumentException(
                $"Unknown controllerType '{request.ControllerType}'. Valid types: {string.Join(", ", ValidMercuryTypes.OrderBy(t => t))}");
        if (string.IsNullOrWhiteSpace(request.IpAddress))
            throw new ArgumentException("ipAddress is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var parentGuid = Guid.Parse(unitGuid);

        // Resolve Mercury class by name via reflection (e.g. MercuryLP1502)
        var mercuryClassName = $"Mercury{request.ControllerType}";
        var mercuryType = FindTypeByName(mercuryClassName)
            ?? throw new InvalidOperationException($"Could not find type {mercuryClassName} in loaded assemblies.");

        // Create and configure the Mercury interface object via reflection
        // (dynamic dispatch fails on SDK types due to assembly loading context)
        var mercuryInterface = Activator.CreateInstance(mercuryType)!;
        mercuryType.GetProperty("IpAddress")!.SetValue(mercuryInterface, IPAddress.Parse(request.IpAddress));
        mercuryType.GetProperty("Port")!.SetValue(mercuryInterface, request.Port);
        mercuryType.GetProperty("Channel")!.SetValue(mercuryInterface, request.Channel);

        // Get the builder via the SDK accessor method using reflection
        // (dynamic dispatch fails due to SDK assembly loading context)
        var entityManager = engine.EntityManager;
        var emType = ((object)entityManager).GetType();
        var getBuilderMethod = emType.GetMethod("GetAccessControlInterfacePeripheralsBuilder")
            ?? throw new InvalidOperationException(
                "Could not find GetAccessControlInterfacePeripheralsBuilder on EntityManager. " +
                $"Available methods: {string.Join(", ", emType.GetMethods().Select(m => m.Name).Distinct())}");

        var builderObj = getBuilderMethod.Invoke(entityManager, new object[] { parentGuid })
            ?? throw new InvalidOperationException("GetAccessControlInterfacePeripheralsBuilder returned null.");

        // All SDK builder calls must use reflection (dynamic dispatch fails on SDK types)
        var builderType = builderObj.GetType();

        var addMethod = builderType.GetMethod("AddAccessControlBusInterface")
            ?? throw new InvalidOperationException(
                $"Could not find AddAccessControlBusInterface on {builderType.Name}. " +
                $"Available methods: {string.Join(", ", builderType.GetMethods().Select(m => m.Name).Distinct())}");
        addMethod.Invoke(builderObj, new object[] { request.Name, (object)mercuryInterface });

        var buildMethod = builderType.GetMethod("Build")
            ?? throw new InvalidOperationException($"Could not find Build on {builderType.Name}.");
        buildMethod.Invoke(builderObj, null);

        return new MercuryControllerResponse
        {
            Message = $"Mercury {request.ControllerType} '{request.Name}' added at {request.IpAddress} to unit {unitGuid}"
        };
    }

    private static readonly HashSet<string> ValidInterfaceBoardTypes = new()
    {
        "MR50", "MR51e", "MR52", "MR62e", "MR16In", "MR16Out",
        "MSACS", "MSI8S", "MSR8S",
        "M516Do", "M516Dor", "M520In", "M52K", "M52RP", "M52SRP", "M58RP",
    };

    public InterfaceModuleResponse AddInterfaceModule(string unitGuid, string controllerGuid, InterfaceModuleRequest request)
    {
        if (string.IsNullOrWhiteSpace(unitGuid))
            throw new ArgumentException("unitGuid is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(controllerGuid))
            throw new ArgumentException("controllerGuid is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.Name))
            throw new ArgumentException("name is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.BoardType))
            throw new ArgumentException("boardType is required and cannot be empty.");
        if (!ValidInterfaceBoardTypes.Contains(request.BoardType))
            throw new ArgumentException(
                $"Unknown boardType '{request.BoardType}'. Valid types: {string.Join(", ", ValidInterfaceBoardTypes.OrderBy(t => t))}");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        try
        {
            var engine = _engineService.Engine;
            var parentUnitGuid = Guid.Parse(unitGuid);
            var parentControllerGuid = Guid.Parse(controllerGuid);

            // Resolve interface board class by name via reflection (e.g. MercuryMR52)
            var boardClassName = $"Mercury{request.BoardType}";
            var boardType = FindTypeByName(boardClassName)
                ?? throw new InvalidOperationException($"Could not find type {boardClassName} in loaded assemblies.");

            // Create the interface board object via reflection
            var boardInterface = Activator.CreateInstance(boardType)!;

            // Set Address property if it exists on the type
            var addressProp = boardType.GetProperty("Address");
            if (addressProp != null)
                addressProp.SetValue(boardInterface, request.Address);

            // Get the builder from the Cloudlink unit (must be a Unit, not InterfaceModule)
            var entityManager = engine.EntityManager;
            var emType = ((object)entityManager).GetType();
            var getBuilderMethod = emType.GetMethod("GetAccessControlInterfacePeripheralsBuilder")
                ?? throw new InvalidOperationException(
                    "Could not find GetAccessControlInterfacePeripheralsBuilder on EntityManager.");

            var builderObj = getBuilderMethod.Invoke(entityManager, new object[] { parentUnitGuid })
                ?? throw new InvalidOperationException("GetAccessControlInterfacePeripheralsBuilder returned null.");

            // Use AddAccessControlChildInterface(name, interface, parentGuid) to add
            // the board under the Mercury controller, not directly under the unit
            var builderType = builderObj.GetType();

            var addChildMethod = builderType.GetMethod("AddAccessControlChildInterface")
                ?? throw new InvalidOperationException(
                    $"Could not find AddAccessControlChildInterface on {builderType.Name}.");
            addChildMethod.Invoke(builderObj, new object[] { request.Name, (object)boardInterface, parentControllerGuid });

            var buildMethod = builderType.GetMethod("Build")
                ?? throw new InvalidOperationException($"Could not find Build on {builderType.Name}.");
            buildMethod.Invoke(builderObj, null);

            return new InterfaceModuleResponse
            {
                Message = $"{request.BoardType} '{request.Name}' added to controller {controllerGuid}"
            };
        }
        catch (System.Reflection.TargetInvocationException ex) when (ex.InnerException != null)
        {
            throw new InvalidOperationException(
                $"SDK error in AddInterfaceModule: {ex.InnerException.GetType().Name}: {ex.InnerException.Message}", ex.InnerException);
        }
    }

    public ListIoDevicesResponse ListIoDevices(string interfaceModuleGuid)
    {
        if (string.IsNullOrWhiteSpace(interfaceModuleGuid))
            throw new ArgumentException("interfaceModuleGuid is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        try
        {
            var engine = _engineService.Engine;
            var moduleGuid = Guid.Parse(interfaceModuleGuid);

            // Get the interface module entity via reflection
            dynamic entity = engine.GetEntity(moduleGuid);
            if (entity == null)
                throw new InvalidOperationException($"Entity not found: {interfaceModuleGuid}");

            var devices = new List<IoDeviceInfo>();

            // Access the Devices collection via reflection
            var entityObj = (object)entity;
            var devicesProperty = entityObj.GetType().GetProperty("Devices");
            if (devicesProperty == null)
                throw new InvalidOperationException(
                    $"Entity {interfaceModuleGuid} does not have a Devices property. " +
                    $"Type: {entityObj.GetType().Name}");

            var devicesCollection = devicesProperty.GetValue(entityObj);
            if (devicesCollection == null)
                return new ListIoDevicesResponse { Devices = devices };

            // Iterate device GUIDs in the collection
            foreach (var deviceGuid in (System.Collections.IEnumerable)devicesCollection)
            {
                var guid = (Guid)deviceGuid;
                dynamic deviceEntity = engine.GetEntity(guid);
                if (deviceEntity == null) continue;

                var deviceObj = (object)deviceEntity;
                var deviceTypeName = deviceObj.GetType().Name;

                // Classify device type based on runtime type name
                string deviceType;
                if (deviceTypeName.Contains("Input"))
                    deviceType = "Input";
                else if (deviceTypeName.Contains("Output"))
                    deviceType = "Output";
                else if (deviceTypeName.Contains("Reader"))
                    deviceType = "Reader";
                else
                    deviceType = deviceTypeName;

                var info = new IoDeviceInfo
                {
                    Guid = guid.ToString(),
                    DeviceType = deviceType,
                };

                // Read Name property
                var nameProp = deviceObj.GetType().GetProperty("Name");
                if (nameProp != null)
                    info.Name = nameProp.GetValue(deviceObj)?.ToString() ?? "";

                // Read PhysicalName property if available
                var physicalNameProp = deviceObj.GetType().GetProperty("PhysicalName");
                if (physicalNameProp != null)
                    info.PhysicalName = physicalNameProp.GetValue(deviceObj)?.ToString() ?? "";

                // Read IsOnline property if available
                var isOnlineProp = deviceObj.GetType().GetProperty("IsOnline");
                if (isOnlineProp != null)
                    info.IsOnline = (bool)(isOnlineProp.GetValue(deviceObj) ?? false);

                devices.Add(info);
            }

            return new ListIoDevicesResponse { Devices = devices };
        }
        catch (System.Reflection.TargetInvocationException ex) when (ex.InnerException != null)
        {
            throw new InvalidOperationException(
                $"SDK error in ListIoDevices: {ex.InnerException.GetType().Name}: {ex.InnerException.Message}", ex.InnerException);
        }
    }

    public ConfigureIoDevicesResponse ConfigureIoDevices(string interfaceModuleGuid, ConfigureIoDevicesRequest request)
    {
        if (string.IsNullOrWhiteSpace(interfaceModuleGuid))
            throw new ArgumentException("interfaceModuleGuid is required and cannot be empty.");
        if (request.DeviceConfigs == null || request.DeviceConfigs.Count == 0)
            throw new ArgumentException("deviceConfigs is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        try
        {
            var engine = _engineService.Engine;

            // Create a transaction via reflection (dynamic dispatch fails on SDK types)
            var transactionManager = (object)engine.TransactionManager;
            var tmType = transactionManager.GetType();
            var createTxMethod = tmType.GetMethod("CreateTransaction")
                ?? throw new InvalidOperationException("Could not find CreateTransaction on TransactionManager.");
            createTxMethod.Invoke(transactionManager, null);

            int configuredCount = 0;
            try
            {
                foreach (var config in request.DeviceConfigs)
                {
                    if (string.IsNullOrWhiteSpace(config.DeviceGuid))
                        throw new ArgumentException("Each device config must contain a 'deviceGuid'.");

                    var deviceGuid = Guid.Parse(config.DeviceGuid);
                    dynamic deviceEntity = engine.GetEntity(deviceGuid);
                    if (deviceEntity == null)
                        throw new InvalidOperationException($"Device entity not found: {config.DeviceGuid}");

                    var deviceObj = (object)deviceEntity;
                    var deviceType = deviceObj.GetType();

                    // Set Name if provided
                    if (!string.IsNullOrEmpty(config.Name))
                    {
                        var nameProp = deviceType.GetProperty("Name");
                        if (nameProp != null && nameProp.CanWrite)
                            nameProp.SetValue(deviceObj, config.Name);
                    }

                    // Configure input settings
                    if (config.InputContactType != null || config.Debounce != null || config.Shunted != null)
                    {
                        var settingsProp = deviceType.GetProperty("InputDeviceSettings");
                        if (settingsProp != null)
                        {
                            var settings = settingsProp.GetValue(deviceObj);
                            if (settings != null)
                            {
                                var settingsType = settings.GetType();

                                if (config.InputContactType != null)
                                {
                                    var contactTypeProp = settingsType.GetProperty("InputContactType");
                                    if (contactTypeProp != null)
                                    {
                                        var enumType = contactTypeProp.PropertyType;
                                        var enumValue = Enum.Parse(enumType, config.InputContactType);
                                        contactTypeProp.SetValue(settings, enumValue);
                                    }
                                }

                                if (config.Debounce != null)
                                {
                                    var debounceProp = settingsType.GetProperty("Debounce");
                                    if (debounceProp != null)
                                        debounceProp.SetValue(settings, config.Debounce.Value);
                                }

                                if (config.Shunted != null)
                                {
                                    var shuntedProp = settingsType.GetProperty("Shunted");
                                    if (shuntedProp != null)
                                        shuntedProp.SetValue(settings, config.Shunted.Value);
                                }
                            }
                        }
                    }

                    // Configure output settings
                    if (config.OutputContactType != null)
                    {
                        var settingsProp = deviceType.GetProperty("OutputDeviceSettings");
                        if (settingsProp != null)
                        {
                            var settings = settingsProp.GetValue(deviceObj);
                            if (settings != null)
                            {
                                var settingsType = settings.GetType();
                                var contactTypeProp = settingsType.GetProperty("OutputContactType");
                                if (contactTypeProp != null)
                                {
                                    var enumType = contactTypeProp.PropertyType;
                                    var enumValue = Enum.Parse(enumType, config.OutputContactType);
                                    contactTypeProp.SetValue(settings, enumValue);
                                }
                            }
                        }
                    }

                    configuredCount++;
                }

                // Commit the transaction
                var commitMethod = tmType.GetMethod("CommitTransaction")
                    ?? throw new InvalidOperationException("Could not find CommitTransaction on TransactionManager.");
                // Pass rollBackOnFailure: true
                var commitParams = commitMethod.GetParameters();
                if (commitParams.Length == 1 && commitParams[0].ParameterType == typeof(bool))
                    commitMethod.Invoke(transactionManager, new object[] { true });
                else
                    commitMethod.Invoke(transactionManager, null);
            }
            catch
            {
                // Attempt to roll back on error
                var rollbackMethod = tmType.GetMethod("RollbackTransaction");
                if (rollbackMethod != null)
                {
                    try { rollbackMethod.Invoke(transactionManager, null); }
                    catch { /* best-effort rollback */ }
                }
                throw;
            }

            return new ConfigureIoDevicesResponse
            {
                Message = $"Configured {configuredCount} device(s) on interface module {interfaceModuleGuid}.",
                ConfiguredCount = configuredCount,
            };
        }
        catch (System.Reflection.TargetInvocationException ex) when (ex.InnerException != null)
        {
            throw new InvalidOperationException(
                $"SDK error in ConfigureIoDevices: {ex.InnerException.GetType().Name}: {ex.InnerException.Message}", ex.InnerException);
        }
    }

    /// <summary>
    /// Diagnostic: inspect builder methods for a given unit GUID.
    /// </summary>
    public List<string> InspectBuilderMethods(string unitGuid)
    {
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var guid = Guid.Parse(unitGuid);

        var entityManager = engine.EntityManager;
        var emType = ((object)entityManager).GetType();
        var getBuilderMethod = emType.GetMethod("GetAccessControlInterfacePeripheralsBuilder")
            ?? throw new InvalidOperationException("Could not find GetAccessControlInterfacePeripheralsBuilder.");

        var builderObj = getBuilderMethod.Invoke(entityManager, new object[] { guid })
            ?? throw new InvalidOperationException("Builder returned null.");

        var builderType = builderObj.GetType();
        var results = new List<string>();

        foreach (var method in builderType.GetMethods(BindingFlags.Public | BindingFlags.Instance))
        {
            var paramList = string.Join(", ", method.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"));
            results.Add($"{method.ReturnType.Name} {method.Name}({paramList})");
        }

        return results.OrderBy(r => r).ToList();
    }

    /// <summary>
    /// Diagnostic: inspect interface module devices, their types, properties, and settings.
    /// </summary>
    public List<string> InspectInterfaceModuleDevices(string interfaceModuleGuid)
    {
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var moduleGuid = Guid.Parse(interfaceModuleGuid);
        var results = new List<string>();

        dynamic entity = engine.GetEntity(moduleGuid);
        if (entity == null)
            throw new InvalidOperationException($"Entity not found: {interfaceModuleGuid}");

        var entityObj = (object)entity;
        results.Add($"Entity type: {entityObj.GetType().FullName}");

        // List all properties on the entity
        foreach (var prop in entityObj.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
        {
            try
            {
                var val = prop.GetValue(entityObj);
                results.Add($"  Property: {prop.PropertyType.Name} {prop.Name} = {val}");
            }
            catch (Exception ex)
            {
                results.Add($"  Property: {prop.PropertyType.Name} {prop.Name} = ERROR: {ex.InnerException?.Message ?? ex.Message}");
            }
        }

        // Try to iterate Devices
        var devicesProperty = entityObj.GetType().GetProperty("Devices");
        if (devicesProperty != null)
        {
            var devicesCollection = devicesProperty.GetValue(entityObj);
            if (devicesCollection != null)
            {
                foreach (var deviceGuid in (System.Collections.IEnumerable)devicesCollection)
                {
                    var guid = (Guid)deviceGuid;
                    dynamic deviceEntity = engine.GetEntity(guid);
                    if (deviceEntity == null) continue;

                    var deviceObj = (object)deviceEntity;
                    results.Add($"\nDevice: {guid} | Type: {deviceObj.GetType().FullName}");

                    foreach (var prop in deviceObj.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
                    {
                        try
                        {
                            var val = prop.GetValue(deviceObj);
                            var valStr = val?.ToString() ?? "null";
                            if (valStr.Length > 200) valStr = valStr[..200] + "...";
                            results.Add($"  {prop.PropertyType.Name} {prop.Name} = {valStr}");

                            // If it's a settings object, enumerate its properties too
                            if (prop.Name.Contains("Settings") && val != null)
                            {
                                var settingsType = val.GetType();
                                results.Add($"    Settings type: {settingsType.FullName}");
                                foreach (var sProp in settingsType.GetProperties(BindingFlags.Public | BindingFlags.Instance))
                                {
                                    try
                                    {
                                        var sVal = sProp.GetValue(val);
                                        results.Add($"    {sProp.PropertyType.Name} {sProp.Name} = {sVal}");

                                        // If it's an enum, list all values
                                        if (sProp.PropertyType.IsEnum)
                                        {
                                            var enumValues = Enum.GetNames(sProp.PropertyType);
                                            results.Add($"      Enum values: {string.Join(", ", enumValues)}");
                                        }
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
                }
            }
        }

        return results;
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
