# CLAUDE.md - Genetec MCP Server

## Project Overview
Python MCP server interfacing with the Genetec Security Center 5.13 SDK (C#/.NET) via pythonnet.

## Tech Stack
- **Python 3.12** managed by `uv` (installed at `~/.local/bin`)
- **pythonnet 3.0.5** + **clr-loader 0.2.10** for .NET 8.0 coreclr interop
- **.NET 8.0.418** at `C:\Program Files\dotnet`
- **Genetec SDK 5.13.0.0** at `C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows`

## Commands
- **Run:** `uv run python -m genetec_mcp_server`
- **Test:** `uv run python -m pytest tests/ -v`
- **Test single:** `uv run python -m pytest tests/test_file.py::test_name -v`
- **Add dep:** `uv add <package>`
- **Add dev dep:** `uv add --dev <package>`
- **Sync:** `uv sync`

## Project Structure
```
src/genetec_mcp_server/
  __init__.py          # Package init, CLI entry point
  __main__.py          # Module entry point
  config.py            # Environment config from .env
  sdk_loader.py        # CLR runtime setup + SDK assembly loading
  connection.py        # GenetecConnection: Engine lifecycle + login
tests/
  test_sdk_loader.py   # SDK loading tests
  test_connection.py   # Engine creation + connection tests
genetec_sdk.runtimeconfig.json  # .NET 8.0 runtime config
```

## Development Workflow: Red/Green TDD
Follow strict red/green TDD for all new features:

1. **Red:** Write a failing test first that defines the expected behavior
2. **Green:** Write the minimum code to make the test pass
3. **Refactor:** Clean up the code while keeping tests green
4. Run tests after each step to confirm red -> green -> green

## Key Technical Patterns
- `set_runtime()` MUST be called before `import clr` — handled by `sdk_loader._configure_runtime()`
- `clr_loader.get_coreclr(runtime_config=...)` takes a keyword argument, not positional
- Use `System.AppDomain.CurrentDomain.GetAssemblies()` to list loaded assemblies (not `Assembly.GetAssemblies()`)
- Custom `AssemblyResolve` handler in `sdk_loader.py` resolves SDK's 150+ transitive dependencies
- `Engine()` constructor requires AppDomain key `GENETEC_GCONFIG_PATH_5_13` set to a valid config folder — handled by `sdk_loader._set_configuration_path()`
- PATH must include `~/.local/bin` (uv) and `C:\Program Files\dotnet` (.NET 8) when running from shell
- SDK certificate (dev): `KxsD11z743Hf5Gq9mv3+5ekxzemlCiUXkTFY5ba1NOGcLCmGstt2n0zYE9NsNimv`
- `GenetecConnection` auto-accepts directory TLS certificates via `RequestDirectoryCertificateValidation`
- Connection uses `BeginLogOn` with `threading.Event` callbacks — `LogOnAsync().Result` deadlocks in pythonnet
- `.cert` file must be placed at `<SDK_PATH>/certificates/Genetec.Sdk.Engine.cert` (SDK resolves path via `SdkCertificateHelpers.GetCertificatePath(Engine.GetType(), False)`)
- **Missing NuGet dependencies:** The SDK ships without several required NuGet packages that must be manually placed in the SDK directory:
  - `Microsoft.Extensions.Caching.Memory` v2.1.23 (CRITICAL — without this, SecurityTokenHelper initialization fails silently, causing generic `Failed` login errors)
  - `Microsoft.Extensions.Caching.Abstractions` v2.1.2 (CRITICAL — transitive dependency of Caching.Memory; must also be present or Caching.Memory fails to load)
  - `BouncyCastle.Cryptography` v2.4.0
  - `System.ServiceModel.Primitives/Http/NetTcp/Security/Duplex` v4.10.3 + `System.Private.ServiceModel`
  - `System.Security.Cryptography.Pkcs` v8.0.0 + `System.Formats.Asn1` v8.0.0
  - `System.Security.Cryptography.Xml` v6.0.1
  - `Microsoft.Extensions.ObjectPool` v5.0.10

## SDK Query Patterns
- Use `engine.ReportManager.CreateReportQuery(ReportType.X)` to create queries — do NOT instantiate query classes directly
- Filter entities: `query.EntityTypeFilter.Add(EntityType.X)`, then `query.Query()` returns `results.Data.Rows`
- Convert rows to entities: `System.Guid(str(row["Guid"]))` -> `engine.GetEntity(guid)`
- `Server.Version` = full version (e.g. `5.13.3132.18`); `Engine.ProductVersion` = SDK version only (`5.13`)
- SDK XML docs are incomplete — use runtime reflection to discover entity properties

## Environment Variables (.env)
- `GENETEC_SDK_PATH` — path to SDK DLLs (default: `C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows`)
- `GENETEC_CONFIG_PATH` — path for .gconfig files (default: `C:\ProgramData\Genetec Security Center 5.13`)
- `GENETEC_SERVER` — Security Center directory server (default: `localhost`)
- `GENETEC_USERNAME` — login username (empty = Windows auth)
- `GENETEC_PASSWORD` — login password
- `GENETEC_CLIENT_CERTIFICATE` — SDK ApplicationId string (default: DAP development cert)

## AWS Deployment Notes (WIN-SERVER-02)
- Production deployment uses NSSM Windows service (`GenetecMCPServer`) running `uv run genetec-mcp-server`
- Service runs behind an ALB with TLS termination at `mcp.acmepavingcorp.com`
- NSSM service account: if `uv` is installed per-user, service must run as `.\Administrator` (not `LocalSystem`)
- ALB idle timeout must be set to 600s (default 60s breaks SSE connections)
- ALB health check: `GET /mcp` returns 406 (expected); success codes configured as `200-406`
- The `.env` file on WIN-SERVER-02 uses `GENETEC_SERVER=172.31.25.170` (WIN-SERVER-01 private IP)
- **SDK certificate must exist in TWO locations:** the repo's `Certificates/python.exe.cert` AND `<SDK_PATH>/certificates/Genetec.Sdk.Engine.cert` — the SDK resolves the latter path internally
- **All NuGet dependencies (see list above) must be manually placed in the SDK directory on every machine** — they are not included in the SDK installer and are not part of the git repo. This is the most common cause of silent `Failed` login errors on fresh deployments.

## Diagnosing Connection Failures
The `app_lifespan` in `server.py` calls `conn.connect()` but does not log the result — the server starts normally even if the SDK connection fails. To diagnose:
```powershell
uv run python -c "
from genetec_mcp_server.connection import GenetecConnection
conn = GenetecConnection()
result = conn.connect()
print(f'Connect result: {result}')
print(f'Is connected: {conn.is_connected}')
print(f'Last failure: {conn.last_failure}')
conn.dispose()
"
```
- `Success` = working. `Timeout` = network issue. `Failed` with no detail = missing NuGet DLL or certificate.
- A generic `Failed` code that occurs regardless of correct/wrong credentials means the failure is pre-authentication (certificate or DLL issue, not credentials).
- Verify all required DLLs are present:
```powershell
$sdkPath = "C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows"
@("Microsoft.Extensions.Caching.Memory.dll","Microsoft.Extensions.Caching.Abstractions.dll","Microsoft.Extensions.Options.dll","BouncyCastle.Cryptography.dll","System.ServiceModel.Primitives.dll","System.Private.ServiceModel.dll","System.Security.Cryptography.Pkcs.dll","System.Formats.Asn1.dll","System.Security.Cryptography.Xml.dll","Microsoft.Extensions.ObjectPool.dll") | ForEach-Object { Write-Host "$_ : $(Test-Path (Join-Path $sdkPath $_))" }
```
- Missing DLLs can be downloaded directly from NuGet without the .NET SDK:
```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri "https://www.nuget.org/api/v2/package/<PackageName>/<Version>" -OutFile "C:\Temp\pkg.zip" -UseBasicParsing
Expand-Archive -Path "C:\Temp\pkg.zip" -DestinationPath "C:\Temp\pkg" -Force
Copy-Item "C:\Temp\pkg\lib\netstandard2.0\<PackageName>.dll" $sdkPath -Force
```
