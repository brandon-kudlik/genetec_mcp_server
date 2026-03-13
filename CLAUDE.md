# CLAUDE.md - Genetec MCP Server

## Project Overview
Python MCP server interfacing with the Genetec Security Center 5.13 SDK via a C# SDK service.

## Architecture
```
Claude/Client  →  Python MCP Server (FastMCP, port 8000)  →  C# SDK Service (localhost:5100)  →  Genetec SDK
                  [MCP tools, httpx HTTP client]              [ASP.NET Minimal API, native SDK]
```

- **Python** is the MCP endpoint (FastMCP) — handles tool definitions and HTTP transport
- **C# ASP.NET Minimal API** handles all Genetec SDK interop natively
- Communication: HTTP over localhost (sub-ms latency)
- Both run as NSSM services on WIN-SERVER-02

## Tech Stack
- **Python 3.12** managed by `uv`
- **httpx** for HTTP client to C# service
- **C# / .NET 8.0** ASP.NET Minimal API for SDK interop
- **Genetec SDK 5.13.0.0** at `C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows`

## Commands
### Python (MCP Server)
- **Run:** `uv run python -m genetec_mcp_server`
- **Test:** `uv run python -m pytest tests/ -v`
- **Test single:** `uv run python -m pytest tests/test_file.py::test_name -v`
- **Add dep:** `uv add <package>`
- **Add dev dep:** `uv add --dev <package>`
- **Sync:** `uv sync`

### C# (SDK Service)
- **Run:** `dotnet run --project genetec_sdk_service/src/GenetecSdkService.Api/`
- **Build:** `dotnet build genetec_sdk_service/GenetecSdkService.sln`
- **Publish:** `dotnet publish genetec_sdk_service/src/GenetecSdkService.Api/ -c Release -r win-x64 --self-contained -o publish/`
- Set `GenetecSdkPath` MSBuild property or update `HintPath` in `.csproj` to point to SDK DLLs

## Project Structure
```
src/genetec_mcp_server/
  __init__.py          # Package init, CLI entry point
  __main__.py          # Module entry point
  config.py            # Environment config (SDK_SERVICE_URL, HOST, PORT)
  connection.py        # GenetecConnection: httpx client to C# service
  server.py            # FastMCP server with MCP tools
tests/
  test_connection.py   # HTTP client tests (mocked httpx)
  test_server.py       # MCP tool tests (mocked connection)
genetec_sdk_service/
  GenetecSdkService.sln
  src/GenetecSdkService.Api/
    Program.cs                    # Minimal API setup, DI, Kestrel on port 5100
    GenetecSdkService.Api.csproj  # SDK DLL references
    appsettings.json              # Server, credentials, SDK path config
    Services/
      GenetecEngineService.cs     # Singleton: Engine lifecycle, connect/disconnect
      CardholderService.cs        # Cardholder CRUD operations
      AccessControlService.cs     # Cloudlink enrollment, Mercury controllers
    Models/
      ApiResponse.cs              # Request/response models + API envelope
    Endpoints/
      SystemEndpoints.cs          # GET /api/health, GET /api/system/version
      CardholderEndpoints.cs      # POST /api/cardholders
      AccessControlEndpoints.cs   # POST /api/units/cloudlink, POST /api/units/{guid}/mercury
```

## Development Workflow: Red/Green TDD
Follow strict red/green TDD for all new features:

1. **Red:** Write a failing test first that defines the expected behavior
2. **Green:** Write the minimum code to make the test pass
3. **Refactor:** Clean up the code while keeping tests green
4. Run tests after each step to confirm red -> green -> green

## Key Technical Patterns

### Python Side
- `GenetecConnection` is an HTTP client wrapping `httpx.Client`
- All SDK operations are REST calls to `http://localhost:5100/api/...`
- API response envelope: `{ success: bool, data: T?, error: string? }`
- Client-side validation (empty fields, controller type) runs before HTTP calls
- `_get()` / `_post()` helpers check `success` field and raise `RuntimeError` / `ValueError`

### C# SDK Service
- `GenetecEngineService` implements `IHostedService` — connects on startup, disconnects on shutdown
- Engine lifecycle: create → set certificate → register TLS handler → `BeginLogOn` + `TaskCompletionSource`
- **Assembly resolver MUST be registered in `Program.cs` before any DI/hosted service code** — the runtime loads `Genetec.Sdk.dll` at JIT time when it first encounters `Engine`, so registering inside `StartAsync` is too late
- **`<UseWPF>true</UseWPF>` required in `.csproj`** — the SDK's `Engine` constructor depends on `System.Windows.Threading.Dispatcher` from `WindowsBase.dll` even in non-UI apps
- **Use `dynamic` for SDK entity/query objects** — `CreateEntity`/`GetEntity` return base `Entity`, `CreateReportQuery` returns base `ReportQuery`; subclass properties (`FirstName`, `Version`, `EntityTypeFilter`) are only accessible via `dynamic` or explicit casts to types that may live in unreferenced assemblies
- **Use reflection (not `dynamic`) for SDK builder/manager types** — `dynamic` dispatch fails on types like `EntityManager` and `AccessControlInterfacePeripheralsBuilder` due to SDK assembly loading context. Use `GetType().GetMethod().Invoke()` for these. Example: `engine.EntityManager.GetType().GetMethod("GetAccessControlInterfacePeripheralsBuilder").Invoke(entityManager, new object[] { guid })`
- **SDK builders are obtained via accessor methods**, not constructed directly — e.g., `engine.EntityManager.GetAccessControlInterfacePeripheralsBuilder(unitGuid)`, `engine.EntityManager.GetCredentialBuilder()`, `engine.EntityManager.GetUserCreationBuilder()`
- AppDomain key `GENETEC_GCONFIG_PATH_5_13` set for Engine constructor
- SDK certificate (dev): `KxsD11z743Hf5Gq9mv3+5ekxzemlCiUXkTFY5ba1NOGcLCmGstt2n0zYE9NsNimv`
- `.cert` file must be at `<SDK_PATH>/certificates/Genetec.Sdk.Engine.cert`
- **Missing NuGet dependencies** must be manually placed in the SDK directory:
  - `Microsoft.Extensions.Caching.Memory` v2.1.23 (CRITICAL)
  - `Microsoft.Extensions.Caching.Abstractions` v2.1.2 (CRITICAL)
  - `BouncyCastle.Cryptography` v2.4.0
  - `System.ServiceModel.Primitives/Http/NetTcp/Security/Duplex` v4.10.3 + `System.Private.ServiceModel`
  - `System.Security.Cryptography.Pkcs` v8.0.0 + `System.Formats.Asn1` v8.0.0
  - `System.Security.Cryptography.Xml` v6.0.1
  - `Microsoft.Extensions.ObjectPool` v5.0.10

### C# API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Connection status + server version |
| GET | `/api/system/version` | Security Center version |
| POST | `/api/cardholders` | Create cardholder |
| POST | `/api/units/cloudlink` | Enroll Cloudlink unit |
| POST | `/api/units/{guid}/mercury` | Add Mercury sub-controller |

## Genetec Platform SDK Reference
**Wiki:** https://github.com/Genetec/DAP/wiki/platform-sdk-overview

### SDK Assemblies
| Assembly | Purpose |
|----------|---------|
| `Genetec.Sdk.dll` | **Core** — entity model, connection, events, queries, transactions |
| `Genetec.Sdk.Plugin.dll` | Server-side custom role hosting |
| `Genetec.Sdk.Workspace.dll` | Client UI extensions (Security Desk / Config Tool) |
| `Genetec.Sdk.Media.dll` | Video/audio playback, frame decoding |
| `Genetec.Sdk.Controls.dll` | Reusable WPF/WinForms controls |

Only `Genetec.Sdk.dll` is required; the rest are optional.

### Core SDK Concepts
- **Entities** — cameras, doors, cardholders, 60+ types with inheritance
- **Caching** — local entity data cache with sync
- **Transactions** — batch operations for performance/consistency
- **Events** — real-time system event subscriptions
- **Actions** — command transmission to Security Center
- **Reporting** — historical data retrieval and entity queries
- **Logging** — diagnostic configuration

### Deployment Requirements
- SDK installation on host machine (for C# service)
- `.cert` certificate file in SDK's `Certificates/` folder
- Valid Security Center license with certificate part number
- SDK version must be within 3 major versions of server

## SDK Query Patterns
- Use `engine.ReportManager.CreateReportQuery(ReportType.X)` to create queries
- Filter entities: `query.EntityTypeFilter.Add(EntityType.X)`, then `query.Query()` returns `results.Data.Rows`
- `Server.Version` = full version (e.g. `5.13.3132.18`); `Engine.ProductVersion` = SDK version only (`5.13`)

## Environment Variables

### Python MCP Server (.env)
- `GENETEC_SDK_SERVICE_URL` — C# SDK service URL (default: `http://localhost:5100`)
- `GENETEC_MCP_HOST` — MCP server bind address (default: `0.0.0.0`)
- `GENETEC_MCP_PORT` — MCP server port (default: `8000`)

### C# SDK Service (appsettings.json)
- `GenetecSdk:SdkPath` — path to SDK DLLs
- `GenetecSdk:ConfigPath` — path for .gconfig files
- `GenetecSdk:Server` — Security Center directory server
- `GenetecSdk:Username` — login username (empty = Windows auth)
- `GenetecSdk:Password` — login password
- `GenetecSdk:ClientCertificate` — SDK ApplicationId string

## AWS Deployment Notes (WIN-SERVER-02)

### Two NSSM Services
1. **GenetecSdkService** — C# SDK service on port 5100 (starts first)
2. **GenetecMCPServer** — Python MCP server on port 8000 (depends on GenetecSdkService)

### Python MCP Server
- NSSM runs `uv run genetec-mcp-server`
- Service runs behind ALB with TLS termination at `mcp.acmepavingcorp.com`
- NSSM service account: if `uv` is installed per-user, run as `.\Administrator`
- ALB idle timeout: 600s (default 60s breaks SSE connections)
- ALB health check: `GET /mcp` returns 406; success codes `200-406`

### C# SDK Service
- Self-contained publish: `dotnet publish -c Release -r win-x64 --self-contained -o publish/`
- NSSM runs the published executable directly (bundles .NET runtime)
- `appsettings.json` configured with `Server: 172.31.25.170` (WIN-SERVER-01 private IP)
- SDK certificate must exist at `<SDK_PATH>/certificates/Genetec.Sdk.Engine.cert`
- All NuGet dependencies must be manually placed in SDK directory

## Diagnosing Connection Failures

### Check C# SDK Service health
```powershell
Invoke-WebRequest -Uri "http://localhost:5100/api/health" -UseBasicParsing | Select-Object -ExpandProperty Content
```

### Check Python MCP Server → SDK Service connectivity
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

### Common issues
- `Success` = working
- `Failed` = SDK service reports not connected to Security Center (check C# service logs)
- `Error: [Errno 111] Connection refused` = C# SDK service not running
- Missing NuGet DLLs = most common cause of silent `Failed` login in C# service
