using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class CardholderEndpoints
{
    public static void MapCardholderEndpoints(this WebApplication app)
    {
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
                return Results.Ok(ApiResponse<CardholderResponse>.Fail(ex.Message));
            }
        });
    }
}
