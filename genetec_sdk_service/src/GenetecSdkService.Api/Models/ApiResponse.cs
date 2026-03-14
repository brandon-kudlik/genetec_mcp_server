namespace GenetecSdkService.Api.Models;

/// <summary>
/// Standard API response envelope.
/// </summary>
public class ApiResponse<T>
{
    public bool Success { get; set; }
    public T? Data { get; set; }
    public string? Error { get; set; }

    public static ApiResponse<T> Ok(T data) => new() { Success = true, Data = data };
    public static ApiResponse<T> Fail(string error) => new() { Success = false, Error = error };
}

public class HealthData
{
    public bool IsConnected { get; set; }
    public string? ServerVersion { get; set; }
}

public class VersionData
{
    public string Version { get; set; } = string.Empty;
}

public class CardholderRequest
{
    public string FirstName { get; set; } = string.Empty;
    public string LastName { get; set; } = string.Empty;
    public string? Email { get; set; }
    public string? MobilePhone { get; set; }
}

public class CardholderResponse
{
    public string Guid { get; set; } = string.Empty;
}

public class CloudlinkRequest
{
    public string Name { get; set; } = string.Empty;
    public string IpAddress { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public string AccessManagerGuid { get; set; } = string.Empty;
}

public class CloudlinkResponse
{
    public string Name { get; set; } = string.Empty;
}

public class MercuryControllerRequest
{
    public string Name { get; set; } = string.Empty;
    public string ControllerType { get; set; } = string.Empty;
    public string IpAddress { get; set; } = string.Empty;
    public int Port { get; set; } = 3001;
    public int Channel { get; set; } = 0;
}

public class MercuryControllerResponse
{
    public string Message { get; set; } = string.Empty;
}

public class InterfaceModuleRequest
{
    public string Name { get; set; } = string.Empty;
    public string BoardType { get; set; } = string.Empty;
    public int Address { get; set; } = 0;
}

public class InterfaceModuleResponse
{
    public string Message { get; set; } = string.Empty;
}

public class IoDeviceInfo
{
    public string Guid { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string PhysicalName { get; set; } = string.Empty;
    public string DeviceType { get; set; } = string.Empty;
    public bool IsOnline { get; set; }
}

public class ListIoDevicesResponse
{
    public List<IoDeviceInfo> Devices { get; set; } = new();
}

public class DeviceConfigItem
{
    public string DeviceGuid { get; set; } = string.Empty;
    public string? Name { get; set; }
    public string? InputContactType { get; set; }
    public double? Debounce { get; set; }
    public bool? Shunted { get; set; }
    public string? Supervised { get; set; }
    public string? OutputContactType { get; set; }
}

public class ConfigureIoDevicesRequest
{
    public List<DeviceConfigItem> DeviceConfigs { get; set; } = new();
}

public class ConfigureIoDevicesResponse
{
    public string Message { get; set; } = string.Empty;
    public int ConfiguredCount { get; set; }
}

// Door creation models

public class CreateDoorItem
{
    public string Name { get; set; } = string.Empty;
    public DoorProperties? Properties { get; set; }
}

public class DoorProperties
{
    public uint? RelockDelayInSeconds { get; set; }
    public uint? StandardEntryTimeInSeconds { get; set; }
    public uint? ExtendedEntryTimeInSeconds { get; set; }
    public uint? StandardGrantTimeInSeconds { get; set; }
    public uint? ExtendedGrantTimeInSeconds { get; set; }
    public bool? RelockOnClose { get; set; }
    public bool? ForcedOpenEventsEnabled { get; set; }
    public bool? HeldOpenEventsEnabled { get; set; }
    public uint? HeldOpenTriggerTimeInSeconds { get; set; }
}

public class BatchCreateDoorsRequest
{
    public List<CreateDoorItem> Doors { get; set; } = new();
}

public class DoorResult
{
    public string Name { get; set; } = string.Empty;
    public string Guid { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
}

public class BatchCreateDoorsResponse
{
    public List<DoorResult> Results { get; set; } = new();
    public int CreatedCount { get; set; }
}

// Door hardware configuration models

public class DoorSideHardware
{
    public string? ReaderGuid { get; set; }
    public string? RexGuid { get; set; }
    public string? DoorSensorGuid { get; set; }
}

public class DoorHardwareConfig
{
    public DoorSideHardware? EntrySide { get; set; }
    public DoorSideHardware? ExitSide { get; set; }
    public string? DoorLockGuid { get; set; }
}

public class DoorHardwareAssignment
{
    public string DoorGuid { get; set; } = string.Empty;
    public DoorHardwareConfig Hardware { get; set; } = new();
}

public class BatchConfigureDoorHardwareRequest
{
    public List<DoorHardwareAssignment> Assignments { get; set; } = new();
}

public class DoorHardwareResult
{
    public string DoorGuid { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
}

public class BatchConfigureDoorHardwareResponse
{
    public List<DoorHardwareResult> Results { get; set; } = new();
    public int ConfiguredCount { get; set; }
}