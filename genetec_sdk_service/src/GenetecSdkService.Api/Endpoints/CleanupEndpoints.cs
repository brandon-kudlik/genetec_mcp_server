using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class CleanupEndpoints
{
    public static void MapCleanupEndpoints(this WebApplication app)
    {
        app.MapDelete("/api/cleanup/demo", async (CleanupService service) =>
        {
            try
            {
                var result = await service.CleanupDemoAsync();
                return Results.Ok(ApiResponse<CleanupDemoResponse>.Ok(result));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<CleanupDemoResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<CleanupDemoResponse>.Fail($"Unexpected error: {ex.Message}"));
            }
        });
    }
}
