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