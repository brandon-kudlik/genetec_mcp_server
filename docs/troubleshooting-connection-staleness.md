# Troubleshooting: Connection Staleness

**Symptom:** Both `GenetecMCPServer` and `GenetecSdkService` NSSM services are running, but MCP clients are unable to connect.

---

## Architecture Reminder

```
MCP Client → ALB (mcp.acmepavingcorp.com) → Python MCP Server (:8000) → C# SDK Service (:5100) → Genetec SDK → Security Center
```

Check each layer in order, starting from the bottom.

---

## Layer 1 — C# SDK Service (port 5100)

Check if the service is alive and connected to Security Center:

```powershell
Invoke-WebRequest -Uri "http://localhost:5100/api/health" -UseBasicParsing | Select-Object -ExpandProperty Content
```

**Expected:** `{"success":true,"data":{"isConnected":true,"serverVersion":"5.13.x.x"}}`

| Result | Meaning |
|--------|---------|
| `isConnected: true` | C# layer is healthy — move to Layer 2 |
| `isConnected: false` | SDK lost connection to Security Center — C# side is stale |
| Connection refused | C# service is dead despite NSSM showing it as running |

---

## Layer 2 — Python MCP Server (port 8000)

Check if the Python process is alive using the dedicated health endpoint:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing | Select-Object -ExpandProperty Content
```

**Expected:** `{"status":"ok"}` with HTTP 200

| Result | Meaning |
|--------|---------|
| `{"status":"ok"}` (200) | Python process is alive and connected — move to Layer 3 |
| `{"status":"unhealthy"}` (503) | Python is alive but can't reach C# service |
| Connection refused | Python service dead despite NSSM |
| Hangs / timeout | Python process is stuck or deadlocked |

---

## Layer 3 — MCP Transport (streamable-http session layer)

The `streamable-http` transport uses Server-Sent Events. Stale sessions or a stuck event loop can block new client connections even when the process is alive.

Test by establishing a raw MCP session:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/mcp" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{"Accept"="application/json, text/event-stream"} `
  -Body '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}},"id":1}' `
  -UseBasicParsing
```

| Result | Meaning |
|--------|---------|
| Valid JSON with sessionId | MCP transport OK — issue is client-side or ALB |
| Hangs | Python event loop is blocked (deadlock or blocking I/O) |
| 500 error | Internal Python error — check logs |

---

## Layer 4 — ALB / Network (external access via mcp.acmepavingcorp.com)

If Layers 1–3 are healthy but external clients fail:

```powershell
Invoke-WebRequest -Uri "https://mcp.acmepavingcorp.com/health" -UseBasicParsing
```

If this fails while localhost works, the issue is at the ALB level:
- ALB may have dropped the target group registration
- The 600s idle timeout may be cutting SSE connections prematurely
- Check ALB target group health in AWS Console

**ALB health check configuration:**
- Path: `/health`
- Expected status code: `200`
- The `/health` endpoint is a lightweight check that does NOT create MCP sessions

---

## Log Locations

```powershell
# C# SDK Service logs (NSSM stdout/stderr)
Get-Content "C:\mcp\genetec_sdk_service_publish\logs\stdout.log" -Tail 100
Get-Content "C:\mcp\genetec_sdk_service_publish\logs\stderr.log" -Tail 100

# Python MCP Server logs (NSSM stdout/stderr)
Get-Content "C:\mcp\genetec_mcp_server\logs\stdout.log" -Tail 100
Get-Content "C:\mcp\genetec_mcp_server\logs\stderr.log" -Tail 100
```

**Key signals to look for:**

| Service | Signal | Meaning |
|---------|--------|---------|
| C# | `LogonFailed` events | SDK dropped session with Security Center |
| C# | Disconnection events | Network disruption to Security Center |
| Python | `[Errno 24] Too many open files` | File descriptor exhaustion (see below) |
| Python | Repeated `RuntimeError` on `/api/health` | C# service unreachable |
| Python | No recent entries | Python process hung before logging |
| Python | Repeated `Session ... crashed` in stderr | Sessions failing on startup |

---

## Most Likely Root Causes (ranked)

1. **File descriptor exhaustion from session leak** — Each MCP session previously created its own `httpx.Client` with an SSL context and TCP connection pool. ALB health checks or client reconnects accumulated sessions that weren't fully cleaned up, eventually hitting the OS file handle limit (`[Errno 24] Too many open files`). After that, every new session crashes instantly — the process is alive but can't serve anything. **Fixed 2026-04-06:** Connection and logger are now shared singletons; ALB health checks use `/health` which doesn't create sessions.

2. **C# engine silently lost its SDK session** — The Engine process stays running but `IsConnected` goes `false`. No automatic reconnect logic exists. All tool calls return "Not connected to Security Center." **Fix:** Restart `GenetecSdkService`.

3. **Python event loop blocked** — A synchronous/blocking call inside the async FastMCP context froze the event loop. New SSE sessions cannot be established. **Fix:** Restart `GenetecMCPServer`.

4. **httpx connection pool stale** — The shared `httpx.Client` in the Python server has a dead TCP connection to port 5100 that hasn't been detected yet. **Fix:** Restart `GenetecMCPServer`.

5. **ALB idle timeout** — The ALB cut the SSE connection after 600s of inactivity. The Python server may not recover gracefully. **Fix:** Restart `GenetecMCPServer`; verify ALB idle timeout is set to 600s.

---

## Quick Recovery Steps

If you need to restore service immediately without diagnosing the root cause:

```powershell
# Restart C# SDK Service first (Python depends on it)
nssm restart GenetecSdkService
Start-Sleep -Seconds 10

# Then restart Python MCP Server
nssm restart GenetecMCPServer
Start-Sleep -Seconds 5

# Verify both are healthy
Invoke-WebRequest -Uri "http://localhost:5100/api/health" -UseBasicParsing | Select-Object -ExpandProperty Content
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing | Select-Object -ExpandProperty Content
```

---

## Known Architectural Limitations

- **No automatic reconnection** on either side. Any network blip or SDK session drop requires a service restart.
- **No keepalive/heartbeat** between Python MCP server and C# SDK service.
- **No keepalive/heartbeat** between C# service and Genetec Security Center.
- Connection state is checked on-demand per tool call, not proactively monitored.
