using System.Reflection;
using Genetec.Sdk;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

/// <summary>
/// Service for adding event-to-action mappings on entities via the Genetec SDK.
/// </summary>
public class EventToActionService
{
    private readonly GenetecEngineService _engineService;

    public EventToActionService(GenetecEngineService engineService)
    {
        _engineService = engineService;
    }

    public AddEventToActionResponse AddEventToActions(AddEventToActionRequest request)
    {
        if (request.Mappings == null || request.Mappings.Count == 0)
            throw new ArgumentException("mappings is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var results = new List<EventToActionResult>();

        // Resolve SDK enum types via reflection
        var eventTypeEnum = FindTypeByName("EventType")
            ?? throw new InvalidOperationException("Could not find EventType enum in loaded assemblies.");
        var actionTypeEnum = FindTypeByName("ActionType")
            ?? throw new InvalidOperationException("Could not find ActionType enum in loaded assemblies.");

        foreach (var mapping in request.Mappings)
        {
            if (string.IsNullOrWhiteSpace(mapping.EntityGuid))
                throw new ArgumentException("Each mapping must contain an 'entityGuid'.");
            if (string.IsNullOrWhiteSpace(mapping.EventType))
                throw new ArgumentException("Each mapping must contain an 'eventType'.");
            if (string.IsNullOrWhiteSpace(mapping.ActionType))
                throw new ArgumentException("Each mapping must contain an 'actionType'.");

            try
            {
                var entityGuid = Guid.Parse(mapping.EntityGuid);
                dynamic entity = engine.GetEntity(entityGuid);
                if (entity == null)
                    throw new InvalidOperationException($"Entity not found: {mapping.EntityGuid}");

                // Parse event and action type enums
                var eventType = Enum.Parse(eventTypeEnum, mapping.EventType);
                var actionType = Enum.Parse(actionTypeEnum, mapping.ActionType);

                // Access EventToActions collection via reflection (dynamic dispatch fails on SDK collection types)
                var entityObj = (object)entity;
                var entityType = entityObj.GetType();
                var etaProp = entityType.GetProperty("EventToActions")
                    ?? throw new InvalidOperationException($"Entity {entityType.Name} does not have EventToActions property.");
                var etaCollection = etaProp.GetValue(entityObj)
                    ?? throw new InvalidOperationException("EventToActions collection is null.");
                var etaType = etaCollection.GetType();

                // Build the action using ActionManager
                // ActionManager.BuildAction(ActionType, Guid recipient, Guid schedule)
                var actionManager = (object)engine.ActionManager;
                var amType = actionManager.GetType();
                var buildActionMethod = amType.GetMethod("BuildAction",
                    new[] { actionTypeEnum, typeof(Guid), typeof(Guid) })
                    ?? throw new InvalidOperationException("Could not find BuildAction on ActionManager.");

                // Determine recipient based on action type
                var recipientGuid = Guid.Empty;
                if (mapping.ActionType == "TriggerAlarm" && !string.IsNullOrEmpty(mapping.AlarmGuid))
                    recipientGuid = Guid.Parse(mapping.AlarmGuid);

                // Schedule.AlwaysScheduleGuid — resolve via reflection
                var scheduleType = FindTypeByName("Schedule");
                var alwaysGuid = Guid.Empty;
                if (scheduleType != null)
                {
                    var alwaysProp = scheduleType.GetProperty("AlwaysScheduleGuid",
                        BindingFlags.Public | BindingFlags.Static);
                    if (alwaysProp != null)
                        alwaysGuid = (Guid)alwaysProp.GetValue(null)!;
                }
                // Fallback: the well-known Always schedule GUID
                if (alwaysGuid == Guid.Empty)
                    alwaysGuid = new Guid("00000000-0000-0000-0000-000000000006");

                var action = buildActionMethod.Invoke(actionManager,
                    new object[] { actionType, recipientGuid, alwaysGuid });

                // Add the event-to-action: EventToActions.Add(EventType, Action)
                var addMethod = etaType.GetMethod("Add", new[] { eventTypeEnum, action!.GetType() })
                    ?? etaType.GetMethod("Add", new[] { eventTypeEnum, action!.GetType().BaseType! })
                    ?? FindAddMethod(etaType, eventTypeEnum, action!);

                if (addMethod == null)
                    throw new InvalidOperationException(
                        $"Could not find Add method on {etaType.Name}. " +
                        $"Available methods: {string.Join(", ", etaType.GetMethods().Select(m => $"{m.Name}({string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name))})"))}");

                addMethod.Invoke(etaCollection, new object[] { eventType, action });

                results.Add(new EventToActionResult
                {
                    EntityGuid = mapping.EntityGuid,
                    EventType = mapping.EventType,
                    ActionType = mapping.ActionType,
                    Status = "Added",
                });
            }
            catch (TargetInvocationException ex)
            {
                var inner = ex.InnerException ?? ex;
                while (inner.InnerException != null) inner = inner.InnerException;
                results.Add(new EventToActionResult
                {
                    EntityGuid = mapping.EntityGuid,
                    EventType = mapping.EventType,
                    ActionType = mapping.ActionType,
                    Status = $"Failed: [{inner.GetType().Name}] {inner.Message}",
                });
            }
            catch (Exception ex) when (ex is not ArgumentException && ex is not InvalidOperationException)
            {
                results.Add(new EventToActionResult
                {
                    EntityGuid = mapping.EntityGuid,
                    EventType = mapping.EventType,
                    ActionType = mapping.ActionType,
                    Status = $"Failed: [{ex.GetType().Name}] {ex.Message}",
                });
            }
        }

        return new AddEventToActionResponse
        {
            Results = results,
            AddedCount = results.Count(r => r.Status == "Added"),
            Message = $"Added {results.Count(r => r.Status == "Added")} event-to-action(s).",
        };
    }

    /// <summary>
    /// Diagnostic: inspect EventToActions collection methods and relevant enum values on an entity.
    /// </summary>
    public object InspectEventToActions(string entityGuid)
    {
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var guid = Guid.Parse(entityGuid);
        dynamic entity = engine.GetEntity(guid);
        var entityObj = (object)entity;
        var entityType = entityObj.GetType();

        var info = new Dictionary<string, object>();
        info["entityType"] = entityType.FullName ?? entityType.Name;

        // Inspect EventToActions collection
        var etaProp = entityType.GetProperty("EventToActions");
        if (etaProp == null)
        {
            info["error"] = "Entity does not have EventToActions property.";
            return info;
        }

        var etaCollection = etaProp.GetValue(entityObj);
        if (etaCollection == null)
        {
            info["error"] = "EventToActions collection is null.";
            return info;
        }

        var etaType = etaCollection.GetType();
        info["collectionType"] = etaType.FullName ?? etaType.Name;

        // List methods
        var methods = etaType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
            .Select(m => new
            {
                m.Name,
                Parameters = m.GetParameters().Select(p => new { p.Name, Type = p.ParameterType.Name }).ToList(),
                ReturnType = m.ReturnType.Name,
            })
            .OrderBy(m => m.Name)
            .ToList();
        info["methods"] = methods;

        // Enumerate existing event-to-actions
        var existingMappings = new List<object>();
        try
        {
            foreach (var eta in (System.Collections.IEnumerable)etaCollection)
            {
                var etaObj = (object)eta;
                var etaItemType = etaObj.GetType();
                var props = new Dictionary<string, string?>();
                foreach (var prop in etaItemType.GetProperties())
                {
                    try { props[prop.Name] = prop.GetValue(etaObj)?.ToString(); }
                    catch (Exception ex) { props[prop.Name] = $"<error: {ex.Message}>"; }
                }
                existingMappings.Add(props);
            }
        }
        catch (Exception ex)
        {
            existingMappings.Add(new { error = ex.Message });
        }
        info["existingMappings"] = existingMappings;

        // List relevant EventType values (door-related subset)
        var eventTypeEnum = FindTypeByName("EventType");
        if (eventTypeEnum != null)
        {
            var doorEvents = Enum.GetNames(eventTypeEnum)
                .Where(n => n.Contains("Door", StringComparison.OrdinalIgnoreCase)
                    || n.Contains("Access", StringComparison.OrdinalIgnoreCase)
                    || n.Contains("Held", StringComparison.OrdinalIgnoreCase)
                    || n.Contains("Forced", StringComparison.OrdinalIgnoreCase))
                .OrderBy(n => n)
                .ToList();
            info["doorRelatedEventTypes"] = doorEvents;
        }

        // List ActionType enum values
        var actionTypeEnum = FindTypeByName("ActionType");
        if (actionTypeEnum != null)
        {
            info["actionTypes"] = Enum.GetNames(actionTypeEnum).OrderBy(n => n).ToList();
        }

        // Inspect ActionManager.BuildAction signature
        var actionManager = (object)engine.ActionManager;
        var amType = actionManager.GetType();
        var buildMethods = amType.GetMethods()
            .Where(m => m.Name == "BuildAction")
            .Select(m => new
            {
                Parameters = m.GetParameters().Select(p => new { p.Name, Type = p.ParameterType.Name }).ToList(),
                ReturnType = m.ReturnType.Name,
            })
            .ToList();
        info["buildActionOverloads"] = buildMethods;

        return info;
    }

    private static MethodInfo? FindAddMethod(Type collectionType, Type eventTypeEnum, object action)
    {
        // Try to find an Add method that accepts (EventType, <some action base type>)
        foreach (var method in collectionType.GetMethods().Where(m => m.Name == "Add"))
        {
            var parameters = method.GetParameters();
            if (parameters.Length == 2
                && parameters[0].ParameterType == eventTypeEnum
                && parameters[1].ParameterType.IsAssignableFrom(action.GetType()))
            {
                return method;
            }
        }
        return null;
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
            catch (ReflectionTypeLoadException) { }
        }
        return null;
    }
}
