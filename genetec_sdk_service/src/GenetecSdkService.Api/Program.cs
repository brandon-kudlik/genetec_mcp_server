using System.IO;
using System.Reflection;
using GenetecSdkService.Api.Endpoints;
using GenetecSdkService.Api.Services;

// Register assembly resolver BEFORE any SDK types are referenced.
// The SDK path comes from configuration — read it early.
var config = new ConfigurationBuilder()
    .AddJsonFile("appsettings.json", optional: false)
    .Build();

var sdkPath = config["GenetecSdk:SdkPath"]
    ?? @"C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows";

AppDomain.CurrentDomain.AssemblyResolve += (sender, args) =>
{
    var assemblyName = args.Name.Split(',')[0];
    var dllPath = Path.Combine(sdkPath, $"{assemblyName}.dll");
    if (File.Exists(dllPath))
        return Assembly.LoadFrom(dllPath);
    return null;
};

var builder = WebApplication.CreateBuilder(args);

// Register Genetec Engine as a singleton hosted service
builder.Services.AddSingleton<GenetecEngineService>();
builder.Services.AddHostedService(sp => sp.GetRequiredService<GenetecEngineService>());

// Register business services
builder.Services.AddSingleton<CardholderService>();
builder.Services.AddSingleton<AccessControlService>();
builder.Services.AddSingleton<DoorService>();
builder.Services.AddSingleton<AlarmService>();
builder.Services.AddSingleton<EventToActionService>();
builder.Services.AddSingleton<AccessRuleService>();
builder.Services.AddSingleton<CleanupService>();
builder.Services.AddSingleton<CredentialService>();

var app = builder.Build();

// Map endpoints
app.MapSystemEndpoints();
app.MapCardholderEndpoints();
app.MapAccessControlEndpoints();
app.MapDoorEndpoints();
app.MapAlarmEndpoints();
app.MapEventToActionEndpoints();
app.MapAccessRuleEndpoints();
app.MapCleanupEndpoints();
app.MapCredentialEndpoints();

app.Run();
