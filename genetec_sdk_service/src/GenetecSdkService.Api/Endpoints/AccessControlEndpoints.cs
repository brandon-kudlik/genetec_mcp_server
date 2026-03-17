using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class AccessControlEndpoints
{
    public static void MapAccessControlEndpoints(this WebApplication app)
    {
        app.MapGet("/api/units/cloudlinks", async (AccessControlService service) =>
        {
            try
            {
                var result = await service.QueryCloudlinksAsync();
                return Results.Ok(ApiResponse<QueryCloudlinksResponse>.Ok(result));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<QueryCloudlinksResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<QueryCloudlinksResponse>.Fail(msg));
            }
        });

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
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<CloudlinkResponse>.Fail(msg));
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
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<MercuryControllerResponse>.Fail(msg));
            }
        });

        app.MapPost("/api/units/{unitGuid}/controllers/{controllerGuid}/interface-modules", (string unitGuid, string controllerGuid, InterfaceModuleRequest request, AccessControlService service) =>
        {
            try
            {
                var result = service.AddInterfaceModule(unitGuid, controllerGuid, request);
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
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<InterfaceModuleResponse>.Fail(msg));
            }
        });

        app.MapGet("/api/interface-modules/{guid}/devices", (string guid, AccessControlService service) =>
        {
            try
            {
                var result = service.ListIoDevices(guid);
                return Results.Ok(ApiResponse<ListIoDevicesResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<ListIoDevicesResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<ListIoDevicesResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<ListIoDevicesResponse>.Fail(msg));
            }
        });

        app.MapPost("/api/interface-modules/{guid}/devices/configure", (string guid, ConfigureIoDevicesRequest request, AccessControlService service) =>
        {
            try
            {
                var result = service.ConfigureIoDevices(guid, request);
                return Results.Ok(ApiResponse<ConfigureIoDevicesResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<ConfigureIoDevicesResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<ConfigureIoDevicesResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var msg = ex.InnerException?.Message ?? ex.Message;
                return Results.Ok(ApiResponse<ConfigureIoDevicesResponse>.Fail(msg));
            }
        });

        app.MapGet("/api/debug/cloudlink-query", async (AccessControlService service) =>
        {
            try
            {
                var info = await service.DiagnoseCloudlinkQueryAsync();
                return Results.Ok(ApiResponse<List<string>>.Ok(info));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<List<string>>.Fail(ex.InnerException?.Message ?? ex.Message));
            }
        });

        app.MapGet("/api/debug/mercury-test/{unitGuid}", (string unitGuid, AccessControlService service) =>
        {
            var diagnostics = new List<string>();
            try
            {
                diagnostics.Add($"Testing mercury addition on unit: {unitGuid}");

                var request = new MercuryControllerRequest
                {
                    Name = "DiagTest Controller",
                    ControllerType = "LP1502",
                    IpAddress = "192.168.1.250",
                    Port = 3001,
                    Channel = 0
                };

                var result = service.AddMercuryController(unitGuid, request);
                diagnostics.Add($"SUCCESS: {result.Message}");
            }
            catch (Exception ex)
            {
                diagnostics.Add($"Exception type: {ex.GetType().FullName}");
                diagnostics.Add($"Message: {ex.Message}");
                if (ex.InnerException != null)
                {
                    diagnostics.Add($"Inner type: {ex.InnerException.GetType().FullName}");
                    diagnostics.Add($"Inner message: {ex.InnerException.Message}");
                    diagnostics.Add($"Inner stack: {ex.InnerException.StackTrace}");
                    if (ex.InnerException.InnerException != null)
                    {
                        diagnostics.Add($"Inner inner type: {ex.InnerException.InnerException.GetType().FullName}");
                        diagnostics.Add($"Inner inner message: {ex.InnerException.InnerException.Message}");
                    }
                }
                diagnostics.Add($"Stack: {ex.StackTrace}");
            }
            return Results.Ok(ApiResponse<List<string>>.Ok(diagnostics));
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

        app.MapGet("/api/debug/interface-module-info/{guid}", (string guid, AccessControlService service) =>
        {
            try
            {
                var info = service.InspectInterfaceModuleDevices(guid);
                return Results.Ok(ApiResponse<List<string>>.Ok(info));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<List<string>>.Fail(ex.InnerException?.Message ?? ex.Message));
            }
        });

        app.MapGet("/api/debug/build-return-info/{unitGuid}", (string unitGuid, AccessControlService service) =>
        {
            try
            {
                var info = service.GetBuildReturnInfo(unitGuid);
                return Results.Ok(new { success = true, data = info });
            }
            catch (Exception ex)
            {
                return Results.Ok(new { success = false, error = ex.InnerException?.Message ?? ex.Message });
            }
        });
    }
}
