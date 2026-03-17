using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class AlarmEndpoints
{
    public static void MapAlarmEndpoints(this WebApplication app)
    {
        app.MapPost("/api/alarms", (AlarmRequest request, AlarmService service) =>
        {
            try
            {
                var result = service.CreateAlarm(request);
                return Results.Ok(ApiResponse<AlarmResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<AlarmResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<AlarmResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var inner = ex;
                while (inner.InnerException != null) inner = inner.InnerException;
                return Results.Ok(ApiResponse<AlarmResponse>.Fail(
                    $"{ex.GetType().Name}: {inner.GetType().Name}: {inner.Message}\nStack: {inner.StackTrace}"));
            }
        });

        app.MapGet("/api/debug/alarm-info/{alarmGuid}", (string alarmGuid, AlarmService service) =>
        {
            try
            {
                var result = service.InspectAlarmEntity(alarmGuid);
                return Results.Ok(ApiResponse<object>.Ok(result));
            }
            catch (Exception ex)
            {
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<object>.Fail(msg));
            }
        });
    }
}
