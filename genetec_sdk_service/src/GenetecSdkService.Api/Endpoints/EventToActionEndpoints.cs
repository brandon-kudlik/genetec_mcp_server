using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class EventToActionEndpoints
{
    public static void MapEventToActionEndpoints(this WebApplication app)
    {
        app.MapPost("/api/event-to-actions", (AddEventToActionRequest request, EventToActionService service) =>
        {
            try
            {
                var result = service.AddEventToActions(request);
                return Results.Ok(ApiResponse<AddEventToActionResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.Ok(ApiResponse<AddEventToActionResponse>.Fail($"Validation: {ex.Message}"));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<AddEventToActionResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var inner = ex;
                while (inner.InnerException != null) inner = inner.InnerException;
                return Results.Ok(ApiResponse<AddEventToActionResponse>.Fail(
                    $"{ex.GetType().Name}: {inner.GetType().Name}: {inner.Message}\nStack: {inner.StackTrace}"));
            }
        });

        app.MapGet("/api/debug/event-to-actions/{entityGuid}", (string entityGuid, EventToActionService service) =>
        {
            try
            {
                var result = service.InspectEventToActions(entityGuid);
                return Results.Ok(ApiResponse<object>.Ok(result));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<object>.Fail(ex.Message));
            }
        });
    }
}
