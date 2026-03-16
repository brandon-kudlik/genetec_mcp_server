using Genetec.Sdk;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

/// <summary>
/// Service for alarm operations against the Genetec SDK.
/// </summary>
public class AlarmService
{
    private readonly GenetecEngineService _engineService;

    public AlarmService(GenetecEngineService engineService)
    {
        _engineService = engineService;
    }

    public AlarmResponse CreateAlarm(AlarmRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Name))
            throw new ArgumentException("name is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;

        // CreateEntity returns base Entity — use dynamic to access Alarm properties
        dynamic alarm = engine.CreateEntity(request.Name, EntityType.Alarm);

        if (request.Priority.HasValue)
            alarm.Priority = (byte)request.Priority.Value;

        if (request.ReactivationThreshold.HasValue)
            alarm.ReactivationThreshold = TimeSpan.FromSeconds(request.ReactivationThreshold.Value);

        return new AlarmResponse { Guid = alarm.Guid.ToString() };
    }

    /// <summary>
    /// Diagnostic: inspect writable properties on an Alarm entity.
    /// </summary>
    public object InspectAlarmEntity(string alarmGuid)
    {
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var guid = Guid.Parse(alarmGuid);
        dynamic entity = engine.GetEntity(guid);
        var entityObj = (object)entity;
        var entityType = entityObj.GetType();

        var properties = entityType.GetProperties()
            .Select(p =>
            {
                string? value = null;
                try { value = p.GetValue(entityObj)?.ToString(); }
                catch (Exception ex) { value = $"<error: {ex.Message}>"; }
                return new { p.Name, Type = p.PropertyType.Name, CanWrite = p.CanWrite, Value = value };
            })
            .OrderBy(p => p.Name)
            .ToList();

        return new
        {
            EntityTypeName = entityType.FullName,
            Properties = properties,
        };
    }
}
