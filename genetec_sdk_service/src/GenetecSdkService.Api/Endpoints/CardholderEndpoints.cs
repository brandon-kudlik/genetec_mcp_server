using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class CardholderEndpoints
{
    public static void MapCardholderEndpoints(this WebApplication app)
    {
        app.MapGet("/api/cardholders", async (CardholderService service) =>
        {
            try
            {
                var result = await service.QueryCardholdersAsync();
                return Results.Ok(ApiResponse<QueryCardholdersResponse>.Ok(result));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<QueryCardholdersResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<QueryCardholdersResponse>.Fail(msg));
            }
        });

        app.MapPost("/api/cardholders", (CardholderRequest request, CardholderService service) =>
        {
            try
            {
                var result = service.CreateCardholder(request);
                return Results.Ok(ApiResponse<CardholderResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<CardholderResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<CardholderResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<CardholderResponse>.Fail(msg));
            }
        });
    }
}
