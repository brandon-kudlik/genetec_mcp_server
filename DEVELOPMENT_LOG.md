# Development Log - Genetec MCP Server

This document summarizes the development journey of the Genetec MCP Server: a Python MCP server that interfaces with the Genetec Security Center 5.13 SDK (C#/.NET) via pythonnet.

---

## Phase 1: SDK Loading & Runtime Setup

### Goal
Get the Genetec Security Center 5.13 SDK loaded into Python via pythonnet and .NET 8.0 coreclr.

### Key Challenges

1. **Runtime initialization order:** `set_runtime()` must be called before `import clr`. The `clr_loader.get_coreclr()` function requires `runtime_config` as a keyword argument, not positional.

2. **AppDomain configuration:** The SDK's `Engine()` constructor requires the AppDomain key `GENETEC_GCONFIG_PATH_5_13` to point to a valid configuration folder. Without it, the constructor fails with "The path is empty."

3. **150+ transitive dependencies:** The SDK ships with Autofac, AutoMapper, Castle.Core, CoreWCF, Azure.Identity, and many others. A custom `AssemblyResolve` handler was needed to resolve these from the SDK directory at runtime.

4. **Native DLL paths:** The SDK includes native DLLs (FFmpeg, DirectShow, etc.) in `x64/` and `amd64/` subdirectories. These required `os.add_dll_directory()` and `PATH` modifications.

### Result
`sdk_loader.py` handles all of this in a single `load_sdk()` call, with lazy loading to ensure it only runs once.

---

## Phase 2: Connecting to Security Center

### Goal
Establish a live connection from Python to the Genetec Security Center directory server.

### The Connection Problem

After SDK loading worked, every connection attempt returned a generic `Failed` error (ConnectionStateCode 4). All credential combinations - correct, wrong password, wrong user - returned the same `Failed` code, meaning the failure was happening *before* authentication, at the certificate/security stage.

### Debugging Journey

1. **Certificate file creation:** The SDK requires a `.cert` file (XML format with CompanyName, ApplicationName, ApplicationId) in a `certificates/` folder. Used `SdkCertificateHelpers.GetCertificatePath(Engine.GetType(), False)` to discover the exact path the SDK looks for:
   ```
   <SDK_PATH>/certificates/Genetec.Sdk.Engine.cert
   ```

2. **Certificate was found but login still failed:** `GetCertificate()` returned the correct ApplicationId and `NeedToRegisterCertificate()` returned `True` - the cert was loading correctly. Something else was wrong.

3. **FirstChanceException handler revealed the root cause:** Attached a `System.AppDomain.CurrentDomain.FirstChanceException` handler to capture all .NET exceptions during the login flow. This revealed a cascade:
   - `SecurityTokenHelper` static constructor threw `TypeInitializationException`
   - Caused by `CoreWCF.IdentityModel.Tokens.DefaultTokenReplayCache` failing
   - Which needed `Microsoft.Extensions.Caching.Memory` - **a DLL not shipped with the SDK**

### The Fix: Missing NuGet Dependencies

The Genetec SDK 5.13 ships without several required NuGet packages. These had to be manually downloaded (via `dotnet add package` in a temp project) and placed in the SDK directory:

| Package | Version | Why It's Needed |
|---------|---------|-----------------|
| **`Microsoft.Extensions.Caching.Memory`** | **2.1.23** | **ROOT CAUSE - SecurityTokenHelper depends on this via CoreWCF** |
| `Microsoft.Extensions.Caching.Abstractions` | 2.1.2 | Dependency of Caching.Memory |
| `Microsoft.Extensions.Options` | 2.1.1 | Dependency of Caching.Memory |
| `BouncyCastle.Cryptography` | 2.4.0 | Cryptographic operations |
| `System.ServiceModel.Primitives` | 4.10.3 | WCF communication |
| `System.ServiceModel.Http` | 4.10.3 | WCF HTTP transport |
| `System.ServiceModel.NetTcp` | 4.10.3 | WCF TCP transport |
| `System.ServiceModel.Security` | 4.10.3 | WCF security |
| `System.ServiceModel.Duplex` | 4.10.3 | WCF duplex communication |
| `System.Private.ServiceModel` | 4.10.3 | WCF internals |
| `System.Security.Cryptography.Pkcs` | 8.0.0 | PKCS cryptography |
| `System.Formats.Asn1` | 8.0.0 | ASN.1 encoding |
| `System.Security.Cryptography.Xml` | 6.0.1 | XML signature/encryption |
| `Microsoft.Extensions.ObjectPool` | 5.0.10 | Object pooling |

### Connection Pattern

The SDK's `LogOnAsync().Result` deadlocks in pythonnet. The working pattern uses `BeginLogOn` with `threading.Event` callbacks:

```python
done = threading.Event()
login_manager.LoggedOn += on_logged_on    # sets done
login_manager.LogonFailed += on_failed    # sets done
login_manager.BeginLogOn(server, username, password)
done.wait(timeout=30)
```

### Result
`GenetecConnection` class in `connection.py` handles engine lifecycle, certificate configuration, directory TLS certificate auto-acceptance, and login/logout with the `BeginLogOn` pattern. Connection to Security Center at `dev01` returns `"Success"`.

---

## Phase 3: System Version Tool

### Goal
Query the Security Center version from the connected directory server.

### SDK API Discovery

- `Engine.ProductVersion` only returns `"5.13"` (SDK version, not server version)
- `SystemConfiguration` entity had no version property
- **Working approach:** Query `Server` entities via `ReportManager.CreateReportQuery(ReportType.EntityConfiguration)` with `EntityTypeFilter.Add(EntityType.Server)`, then access `Server.Version`
- Do NOT instantiate query classes directly - always use `ReportManager.CreateReportQuery()`

### Result
`get_system_version()` method on `GenetecConnection` returns the full version string (e.g. `5.13.3132.18`). Built following Red/Green TDD.

---

## Phase 4: MCP Server

### Goal
Create an MCP server using the official `mcp` Python SDK (FastMCP) and expose `get_system_version` as the first tool.

### Architecture

- **FastMCP lifespan pattern** manages the `GenetecConnection` lifecycle - connects on startup, disposes on shutdown
- **`AppContext` dataclass** holds the connection instance, accessible to tools via `ctx.request_context.lifespan_context`
- **Streamable HTTP transport** (not stdio) allows remote access from Claude Desktop on other machines

### Key Files

- `server.py` - FastMCP server instance, lifespan, and tool definitions
- `__main__.py` - Entry point that calls `mcp.run(transport="streamable-http")`
- `config.py` - `HOST` (default `0.0.0.0`) and `PORT` (default `8000`) from env vars

### FastMCP API Notes

- `host` and `port` go in the `FastMCP()` constructor, not `mcp.run()`
- `mcp.run()` only accepts `transport` and `mount_path` parameters
- Tool functions receiving a `Context` parameter must be `async def`
- Registered tools are stored in `mcp._tool_manager._tools` (private API, used in tests)

### Claude Desktop Configuration

For remote access from a laptop, Claude Desktop requires a stdio bridge since it doesn't natively support HTTP URLs. Use `mcp-proxy` (Python) via `uvx`:

```json
{
  "mcpServers": {
    "genetec": {
      "command": "uvx",
      "args": [
        "mcp-proxy",
        "http://<server-ip>:8000/mcp"
      ]
    }
  }
}
```

Note: `mcp-remote` is a Node.js package and does NOT work with `uvx`. Use `mcp-proxy` for Python or `npx mcp-remote` if Node.js is available.

### Firewall

Windows Server requires a firewall rule for inbound TCP on port 8000:

```powershell
New-NetFirewallRule -DisplayName "MCP Server" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### Running the Server

```bash
cd C:\Users\Administrator\workspace\genetec_mcp_server
~/.local/bin/uv run genetec-mcp-server
```

Server starts on `http://0.0.0.0:8000` with streamable HTTP transport and the MCP endpoint at `/mcp`.

---

## Test Suite

17 tests covering all layers:

- **SDK loader tests (4):** Config validation, SDK loading, version check, Engine class import
- **Connection tests (8):** Engine creation, connection state, certificate acceptance, TLS validation, login, system version query
- **Server tests (5):** FastMCP instance, tool registration, tool behavior (connected/disconnected), lifespan lifecycle

Run with: `uv run python -m pytest tests/ -v`

---

## Commit History

| Commit | Description |
|--------|-------------|
| `afdcf96` | Initial project setup: SDK loader, connection, config, tests |
| `6e12b53` | Add `get_system_version` method to `GenetecConnection` |
| `edc168b` | Add MCP server with streamable HTTP transport |
