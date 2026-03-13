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

        // Create and configure the Mercury interface object
        dynamic mercuryInterface = Activator.CreateInstance(mercuryType)!;
        mercuryInterface.IpAddress = IPAddress.Parse(request.IpAddress);
        mercuryInterface.Port = request.Port;
        mercuryInterface.Channel = request.Channel;

        // Get the builder via the SDK accessor method (not direct construction)
        dynamic entityManager = engine.EntityManager;
        dynamic builder = entityManager.GetAccessControlInterfacePeripheralsBuilder(parentGuid);
        builder.AddAccessControlBusInterface(request.Name, mercuryInterface);
        builder.Build();

        return new MercuryControllerResponse
        {
            Message = $"Mercury {request.ControllerType} '{request.Name}' added at {request.IpAddress} to unit {unitGuid}"
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
