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
    }
}
