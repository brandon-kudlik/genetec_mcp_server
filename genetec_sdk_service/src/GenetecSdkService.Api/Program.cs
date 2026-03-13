using GenetecSdkService.Api.Endpoints;
using GenetecSdkService.Api.Services;

var builder = WebApplication.CreateBuilder(args);

// Register Genetec Engine as a singleton hosted service
builder.Services.AddSingleton<GenetecEngineService>();
builder.Services.AddHostedService(sp => sp.GetRequiredService<GenetecEngineService>());

// Register business services
builder.Services.AddSingleton<CardholderService>();
builder.Services.AddSingleton<AccessControlService>();

var app = builder.Build();

// Map endpoints
app.MapSystemEndpoints();
app.MapCardholderEndpoints();
app.MapAccessControlEndpoints();

app.Run();
