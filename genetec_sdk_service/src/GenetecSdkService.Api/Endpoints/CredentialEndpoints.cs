using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class CredentialEndpoints
{
    public static void MapCredentialEndpoints(this WebApplication app)
    {
        app.MapGet("/api/credentials", async (CredentialService service) =>
        {
            try
            {
                var result = await service.QueryCredentialsAsync();
                return Results.Ok(ApiResponse<QueryCredentialsResponse>.Ok(result));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<QueryCredentialsResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<QueryCredentialsResponse>.Fail(msg));
            }
        });

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
        app.MapPost("/api/credentials/assign", (AssignCredentialRequest request, CredentialService service) =>
        {
            try
            {
                var result = service.AssignCredential(request);
                return Results.Ok(ApiResponse<AssignCredentialResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<AssignCredentialResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<AssignCredentialResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<AssignCredentialResponse>.Fail(msg));
            }
        });
    }
}
