using Genetec.Sdk;
using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class SystemEndpoints
{
    public static void MapSystemEndpoints(this WebApplication app)
    {
        app.MapGet("/api/health", (GenetecEngineService engineService) =>
        {
            string? version = null;
            if (engineService.IsConnected)
            {
                try
                {
                    version = GetServerVersion(engineService.Engine);
                }
                catch
                {
                    // Version retrieval failed, but health check still returns connection state
                }
            }

            return Results.Ok(ApiResponse<HealthData>.Ok(new HealthData
            {
                IsConnected = engineService.IsConnected,
                ServerVersion = version
            }));
        });

        app.MapGet("/api/system/version", (GenetecEngineService engineService) =>
        {
            if (!engineService.IsConnected)
                return Results.Ok(ApiResponse<VersionData>.Fail("Not connected to Security Center."));

            try
            {
                var version = GetServerVersion(engineService.Engine);
                if (version == null)
                    return Results.Ok(ApiResponse<VersionData>.Fail("No server entity found in Security Center."));

                return Results.Ok(ApiResponse<VersionData>.Ok(new VersionData
                {
                    Version = version
                }));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<VersionData>.Fail(ex.Message));
            }
        });
    }

    private static string? GetServerVersion(Engine engine)
    {
        // CreateReportQuery returns base ReportQuery — use dynamic to access
        // EntityTypeFilter which is on the EntityConfigurationQuery subclass
        dynamic query = engine.ReportManager.CreateReportQuery(ReportType.EntityConfiguration);
        query.EntityTypeFilter.Add(EntityType.Server);
        var results = query.Query();

        foreach (System.Data.DataRow row in results.Data.Rows)
        {
            var guid = new Guid(row["Guid"].ToString()!);
            // GetEntity returns base Entity — use dynamic to access Version property
            dynamic? server = engine.GetEntity(guid);
            if (server != null)
            {
                return server.Version.ToString();
            }
        }

        return null;
    }
}
