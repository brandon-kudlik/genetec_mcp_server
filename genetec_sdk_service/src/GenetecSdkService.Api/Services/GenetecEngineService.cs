using System.IO;
using Genetec.Sdk;

namespace GenetecSdkService.Api.Services;

/// <summary>
/// Configuration options for the Genetec SDK connection.
/// </summary>
public class GenetecSdkOptions
{
    public string SdkPath { get; set; } = string.Empty;
    public string ConfigPath { get; set; } = string.Empty;
    public string Server { get; set; } = "localhost";
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public string ClientCertificate { get; set; } = string.Empty;
}

/// <summary>
/// Singleton hosted service that manages the Genetec SDK Engine lifecycle.
/// Connects on startup, disconnects on shutdown.
/// </summary>
public class GenetecEngineService : IHostedService, IDisposable
{
    private readonly ILogger<GenetecEngineService> _logger;
    private readonly GenetecSdkOptions _options;
    private Engine? _engine;
    private string? _lastFailure;

    public GenetecEngineService(
        ILogger<GenetecEngineService> logger,
        IConfiguration configuration)
    {
        _logger = logger;
        _options = new GenetecSdkOptions();
        configuration.GetSection("GenetecSdk").Bind(_options);
    }

    public Engine Engine => _engine ?? throw new InvalidOperationException("Engine not initialized.");
    public bool IsConnected => _engine?.IsConnected ?? false;
    public string? LastFailure => _lastFailure;

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Initializing Genetec SDK Engine...");

        // Assembly resolver is registered in Program.cs (must run before any SDK type is loaded).
        // Set configuration path for Engine constructor.
        var configPath = _options.ConfigPath;
        Directory.CreateDirectory(Path.Combine(configPath, "ConfigurationFiles"));
        AppDomain.CurrentDomain.SetData("GENETEC_GCONFIG_PATH_5_13", configPath);

        // Create engine
        _engine = new Engine();

        // Set client certificate
        if (!string.IsNullOrEmpty(_options.ClientCertificate))
        {
            _engine.ClientCertificate = _options.ClientCertificate;
        }

        // Auto-accept directory TLS certificates
        _engine.LoginManager.RequestDirectoryCertificateValidation += (sender, e) =>
        {
            e.AcceptDirectory = true;
        };

        // Connect using TaskCompletionSource (avoids async deadlock)
        var tcs = new TaskCompletionSource<string>();

        _engine.LoginManager.LoggedOn += (sender, e) =>
        {
            _lastFailure = null;
            tcs.TrySetResult("Success");
        };

        _engine.LoginManager.LogonFailed += (sender, e) =>
        {
            _lastFailure = e.FormattedErrorMessage;
            tcs.TrySetResult(e.FailureCode.ToString());
        };

        if (!string.IsNullOrEmpty(_options.Username))
        {
            _engine.LoginManager.BeginLogOn(_options.Server, _options.Username, _options.Password);
        }
        else
        {
            _engine.LoginManager.BeginLogOnUsingWindowsCredential(_options.Server);
        }

        var timeoutTask = Task.Delay(TimeSpan.FromSeconds(30), cancellationToken);
        var completedTask = await Task.WhenAny(tcs.Task, timeoutTask);

        if (completedTask == timeoutTask)
        {
            _lastFailure = "Connection timed out after 30 seconds.";
            _logger.LogWarning("Genetec SDK connection timed out.");
        }
        else
        {
            var result = await tcs.Task;
            if (result == "Success")
                _logger.LogInformation("Connected to Genetec Security Center at {Server}.", _options.Server);
            else
                _logger.LogWarning("Genetec SDK connection failed: {Result} - {Detail}", result, _lastFailure);
        }
    }

    public Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Shutting down Genetec SDK Engine...");
        if (_engine?.IsConnected == true)
        {
            _engine.LoginManager.LogOff();
        }
        _engine?.Dispose();
        _engine = null;
        return Task.CompletedTask;
    }

    public void Dispose()
    {
        _engine?.Dispose();
        _engine = null;
    }
}
