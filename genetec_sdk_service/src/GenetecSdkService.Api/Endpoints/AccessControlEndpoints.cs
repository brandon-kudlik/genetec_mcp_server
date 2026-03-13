using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class AccessControlEndpoints
{
    public static void MapAccessControlEndpoints(this WebApplication app)
    {
        app.MapPost("/api/units/cloudlink", async (CloudlinkRequest request, AccessControlService service) =>
        {
            try
            {
                var result = await service.AddCloudlinkUnitAsync(request);
                return Results.Ok(ApiResponse<CloudlinkResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<CloudlinkResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<CloudlinkResponse>.Fail(ex.Message));
            }
            catch (TimeoutException ex)
            {
                return Results.Ok(ApiResponse<CloudlinkResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<CloudlinkResponse>.Fail(ex.Message));
            }
        });

        app.MapPost("/api/units/{unitGuid}/mercury", (string unitGuid, MercuryControllerRequest request, AccessControlService service) =>
        {
            try
            {
                var result = service.AddMercuryController(unitGuid, request);
                return Results.Ok(ApiResponse<MercuryControllerResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<MercuryControllerResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<MercuryControllerResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<MercuryControllerResponse>.Fail(ex.Message));
            }
        });

        app.MapPost("/api/units/{controllerGuid}/interface-modules", (string controllerGuid, InterfaceModuleRequest request, AccessControlService service) =>
        {
            try
            {
                var result = service.AddInterfaceModule(controllerGuid, request);
                return Results.Ok(ApiResponse<InterfaceModuleResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<InterfaceModuleResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<InterfaceModuleResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<InterfaceModuleResponse>.Fail(ex.Message));
            }
        });

        app.MapGet("/api/debug/builder-methods/{unitGuid}", (string unitGuid, AccessControlService service) =>
        {
            try
            {
                var methods = service.InspectBuilderMethods(unitGuid);
                return Results.Ok(ApiResponse<List<string>>.Ok(methods));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<List<string>>.Fail(ex.InnerException?.Message ?? ex.Message));
            }
        });
    }
}
