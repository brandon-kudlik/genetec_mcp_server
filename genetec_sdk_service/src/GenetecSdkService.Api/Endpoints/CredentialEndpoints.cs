using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class CredentialEndpoints
{
    public static void MapCredentialEndpoints(this WebApplication app)
    {
        app.MapPost("/api/credentials", (CredentialRequest request, CredentialService service) =>
        {
            try
            {
                var result = service.CreateCredential(request);
                return Results.Ok(ApiResponse<CredentialResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<CredentialResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<CredentialResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<CredentialResponse>.Fail(msg));
            }
        });
    }
}
