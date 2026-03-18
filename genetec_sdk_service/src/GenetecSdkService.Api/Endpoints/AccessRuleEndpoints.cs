using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class AccessRuleEndpoints
{
    public static void MapAccessRuleEndpoints(this WebApplication app)
    {
        app.MapPost("/api/access-rules/batch", (BatchCreateAccessRulesRequest request, AccessRuleService service) =>
        {
            try
            {
                var result = service.BatchCreateAccessRules(request);
                return Results.Ok(ApiResponse<BatchCreateAccessRulesResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<BatchCreateAccessRulesResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<BatchCreateAccessRulesResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var inner = ex;
                while (inner.InnerException != null) inner = inner.InnerException;
                return Results.Ok(ApiResponse<BatchCreateAccessRulesResponse>.Fail(
                    $"{ex.GetType().Name}: {inner.GetType().Name}: {inner.Message}\nStack: {inner.StackTrace}"));
            }
        });

        app.MapGet("/api/access-rules", async (AccessRuleService service) =>
        {
            try
            {
                var result = await service.QueryAccessRulesAsync();
                return Results.Ok(ApiResponse<QueryAccessRulesResponse>.Ok(result));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<QueryAccessRulesResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var inner = ex;
                while (inner.InnerException != null) inner = inner.InnerException;
                return Results.Ok(ApiResponse<QueryAccessRulesResponse>.Fail(
                    $"{ex.GetType().Name}: {inner.GetType().Name}: {inner.Message}"));
            }
        });

        app.MapPost("/api/access-rules/assign", (AssignAccessRulesRequest request, AccessRuleService service) =>
        {
            try
            {
                var result = service.AssignAccessRules(request);
                return Results.Ok(ApiResponse<AssignAccessRulesResponse>.Ok(result));
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(ApiResponse<AssignAccessRulesResponse>.Fail(ex.Message));
            }
            catch (InvalidOperationException ex)
            {
                return Results.Ok(ApiResponse<AssignAccessRulesResponse>.Fail(ex.Message));
            }
            catch (Exception ex)
            {
                var inner = ex;
                while (inner.InnerException != null) inner = inner.InnerException;
                return Results.Ok(ApiResponse<AssignAccessRulesResponse>.Fail(
                    $"{ex.GetType().Name}: {inner.GetType().Name}: {inner.Message}"));
            }
        });
    }
}
