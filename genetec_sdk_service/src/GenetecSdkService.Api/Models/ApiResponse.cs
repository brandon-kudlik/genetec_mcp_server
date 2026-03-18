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
    public string Guid { get; set; } = string.Empty;
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
    public string Guid { get; set; } = string.Empty;
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

// Cloudlink query models

public class CloudlinkInfo
{
    public string Guid { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public bool IsOnline { get; set; }
}

public class QueryCloudlinksResponse
{
    public List<CloudlinkInfo> Cloudlinks { get; set; } = new();
}

// Door creation models

public class CreateDoorItem
{
    public string Name { get; set; } = string.Empty;
    public DoorProperties? Properties { get; set; }
}

public class DoorProperties
{
    public int? RelockDelayInSeconds { get; set; }
    public int? StandardEntryTimeInSeconds { get; set; }
    public int? ExtendedEntryTimeInSeconds { get; set; }
    public int? StandardGrantTimeInSeconds { get; set; }
    public int? ExtendedGrantTimeInSeconds { get; set; }
    public bool? RelockOnClose { get; set; }
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
}

public class DoorHardwareConfig
{
    public DoorSideHardware? EntrySide { get; set; }
    public DoorSideHardware? ExitSide { get; set; }
    public string? DoorLockGuid { get; set; }
    public string? DoorSensorGuid { get; set; }
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

// Alarm models

public class AlarmRequest
{
    public string Name { get; set; } = string.Empty;
    public int? Priority { get; set; }
    public int? ReactivationThreshold { get; set; }
}

public class AlarmResponse
{
    public string Guid { get; set; } = string.Empty;
}

// Event-to-action models

public class EventToActionMapping
{
    public string EntityGuid { get; set; } = string.Empty;
    public string EventType { get; set; } = string.Empty;
    public string ActionType { get; set; } = string.Empty;
    public string? AlarmGuid { get; set; }
}

public class AddEventToActionRequest
{
    public List<EventToActionMapping> Mappings { get; set; } = new();
}

public class EventToActionResult
{
    public string EntityGuid { get; set; } = string.Empty;
    public string EventType { get; set; } = string.Empty;
    public string ActionType { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
}

public class AddEventToActionResponse
{
    public List<EventToActionResult> Results { get; set; } = new();
    public int AddedCount { get; set; }
    public string Message { get; set; } = string.Empty;
}

// Access rule models

public class AccessRuleItem
{
    public string Name { get; set; } = string.Empty;
    public List<string> DoorGuids { get; set; } = new();
    public string Side { get; set; } = "Both";
}

public class BatchCreateAccessRulesRequest
{
    public List<AccessRuleItem> AccessRules { get; set; } = new();
}

public class AccessRuleResult
{
    public string Name { get; set; } = string.Empty;
    public string Guid { get; set; } = string.Empty;
    public int DoorsAssigned { get; set; }
    public string Status { get; set; } = string.Empty;
}

public class BatchCreateAccessRulesResponse
{
    public List<AccessRuleResult> Results { get; set; } = new();
    public int CreatedCount { get; set; }
}

// Credential models

public class CredentialRequest
{
    public string Name { get; set; } = string.Empty;
    public string FormatType { get; set; } = string.Empty;
    public int? Facility { get; set; }
    public int? CardId { get; set; }
    public int? Code { get; set; }
    public string? LicensePlate { get; set; }
    public string? RawData { get; set; }
    public int? BitLength { get; set; }
    public string? CardholderGuid { get; set; }
}

public class CredentialResponse
{
    public string Guid { get; set; } = string.Empty;
}

// Credential assignment models

public class AssignCredentialRequest
{
    public string CredentialGuid { get; set; } = string.Empty;
    public string CardholderGuid { get; set; } = string.Empty;
}

public class AssignCredentialResponse
{
    public string CredentialGuid { get; set; } = string.Empty;
    public string CardholderGuid { get; set; } = string.Empty;
    public string? PreviousCardholderGuid { get; set; }
}

// Cardholder query models

public class CardholderInfo
{
    public string Guid { get; set; } = string.Empty;
    public string FirstName { get; set; } = string.Empty;
    public string LastName { get; set; } = string.Empty;
    public string? EmailAddress { get; set; }
    public string? MobilePhone { get; set; }
    public string Status { get; set; } = string.Empty;
}

public class QueryCardholdersResponse
{
    public List<CardholderInfo> Cardholders { get; set; } = new();
}

// Credential query models

public class CredentialInfo
{
    public string Guid { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string FormatType { get; set; } = string.Empty;
    public string? CardholderGuid { get; set; }
    public string? CardholderName { get; set; }
    public string Status { get; set; } = string.Empty;
}

public class QueryCredentialsResponse
{
    public List<CredentialInfo> Credentials { get; set; } = new();
}

// Access rule query and assignment models

public class AccessRuleInfo
{
    public string Guid { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
}

public class QueryAccessRulesResponse
{
    public List<AccessRuleInfo> AccessRules { get; set; } = new();
}

public class AssignAccessRulesRequest
{
    public List<string> AccessRuleGuids { get; set; } = new();
    public List<string> CardholderGuids { get; set; } = new();
}

public class AccessRuleAssignmentResult
{
    public string AccessRuleGuid { get; set; } = string.Empty;
    public string CardholderGuid { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public string? Error { get; set; }
}

public class AssignAccessRulesResponse
{
    public List<AccessRuleAssignmentResult> Assignments { get; set; } = new();
}

// Cleanup models

public class CleanupEntityTypeResult
{
    public string EntityType { get; set; } = string.Empty;
    public int Found { get; set; }
    public int Deleted { get; set; }
    public List<string> Errors { get; set; } = new();
}

public class CleanupDemoResponse
{
    public List<CleanupEntityTypeResult> Results { get; set; } = new();
    public int TotalDeleted { get; set; }
}