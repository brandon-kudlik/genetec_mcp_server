using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class DoorEndpoints
{
    public static void MapDoorEndpoints(this WebApplication app)
    {
        app.MapPost("/api/doors/batch", (BatchCreateDoorsRequest request, DoorService service) =>
        {
            try
            {
                var result = service.BatchCreateDoors(request);
                return Results.Ok(ApiResponse<BatchCreateDoorsResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<BatchCreateDoorsResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<BatchCreateDoorsResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<BatchCreateDoorsResponse>.Fail(ex.Message));
            }
        });

        app.MapPost("/api/doors/hardware/batch", (BatchConfigureDoorHardwareRequest request, DoorService service) =>
        {
            try
            {
                var result = service.ConfigureDoorHardware(request);
                return Results.Ok(ApiResponse<BatchConfigureDoorHardwareResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                // Return 200 with error details instead of 400 to avoid swallowed messages
                return Results.Ok(ApiResponse<BatchConfigureDoorHardwareResponse>.Fail($"Validation: {ex.Message}"));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<BatchConfigureDoorHardwareResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var inner = ex;
                while (inner.InnerException != null) inner = inner.InnerException;
                return Results.Ok(ApiResponse<BatchConfigureDoorHardwareResponse>.Fail(
                    $"{ex.GetType().Name}: {inner.GetType().Name}: {inner.Message}\nStack: {inner.StackTrace}"));
            }
        });

        app.MapGet("/api/debug/door-info/{guid}", (string guid, DoorService service) =>
        {
            try
            {
                var info = service.InspectDoorEntity(guid);
                return Results.Ok(ApiResponse<List<string>>.Ok(info));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<List<string>>.Fail(ex.InnerException?.Message ?? ex.Message));
            }
        });
    }
}
