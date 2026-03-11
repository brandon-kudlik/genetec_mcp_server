# AWS EC2 Windows Server 2022 — Genetec MCP Deployment Guide

**Two-Instance Architecture with Genetec Remote MCP Server**
*Prepared: March 2026 — Reflects actual deployment on acmepavingcorp.com*

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Recommended EC2 Instance Type](#2-recommended-ec2-instance-type)
3. [Monthly Cost Estimate](#3-monthly-cost-estimate)
4. [Pre-Requisites](#4-pre-requisites)
5. [Manual Deployment via AWS Console](#5-manual-deployment-via-aws-console)
6. [Security Best Practices](#6-security-best-practices)
7. [Deployment Checklist](#7-deployment-checklist)
8. [Configuring WIN-SERVER-02 as the Genetec Remote MCP Server](#8-configuring-win-server-02-as-the-genetec-remote-mcp-server)
9. [Security Best Practices — Implementation Guide](#9-security-best-practices--implementation-guide)

---

## 1. Architecture Overview

This document covers deploying two Windows Server 2022 EC2 instances on AWS, with WIN-SERVER-02 acting as a remote MCP server for Claude Desktop using the [Genetec MCP Server](https://github.com/brandon-kudlik/genetec_mcp_server).

**Architecture Summary:**

- Two EC2 instances (WIN-SERVER-01 and WIN-SERVER-02) in the same AWS Region
- Placed within a single VPC and subnet
- A single Security Group governs all inbound/outbound traffic
- Both instances attached to the same Security Group for peer-to-peer communication
- EBS gp3 volumes for persistent OS and application storage
- Elastic IPs for stable public addressing
- WIN-SERVER-02 is the Genetec MCP server, accessible over HTTPS via an Application Load Balancer

> **NOTE:** Windows Firewall blocks ICMP (ping) by default on Windows Server 2022. If inter-server ping fails, see [Enabling Ping](#enabling-ping-between-servers) below — this does not affect actual application connectivity.

---

## 2. Recommended EC2 Instance Type

Recommended: **t3.large** (US East — N. Virginia)

| Requirement | Specified Minimum | AWS t3.large Provides |
|---|---|---|
| Processor | Intel Core 2 Duo E6850 @ 3.0 GHz | 2x Intel Xeon Platinum vCPU (up to 3.1 GHz) |
| RAM | 4 GB | 8 GiB |
| OS Architecture | 64-bit | 64-bit (x86_64) |
| Storage | 80 GB | 100 GB gp3 EBS |
| Network | 100/1000 Mbps | Up to 5 Gbps |
| Operating System | Windows Server 2022 64-bit | Windows Server 2022 Base AMI |

> **NOTE:** If workloads consistently max out CPU, upgrade to `m6i.large` (fixed CPU) or `t3.xlarge` (4 vCPU, 16 GiB).

---

## 3. Monthly Cost Estimate

All pricing for US East (N. Virginia), On-Demand, USD, excluding tax.

### 3.1 Per-Instance Cost Breakdown

| Component | Unit Cost | Monthly (1 instance) | Monthly (2 instances) |
|---|---|---|---|
| EC2 t3.large (Windows) | ~$0.166/hr | ~$121.18 | ~$242.36 |
| EBS gp3 100 GB | $0.08/GB-mo | $8.00 | $16.00 |
| Data Transfer IN | Free | $0.00 | $0.00 |
| Data Transfer OUT — first 100 GB | Free | $0.00 | $0.00 |
| Data Transfer OUT — beyond 100 GB | $0.09/GB | Variable | Variable |
| Inter-instance traffic (same VPC/AZ) | Free | $0.00 | $0.00 |
| Elastic IP (per IP, if allocated) | $0.005/hr idle | ~$3.60 | ~$7.20 |
| ALB (WIN-SERVER-02 MCP) | ~$0.008/hr + LCU | ~$16–25 | Included |
| **Estimated Total (no EIP, no ALB)** | | ~$129.18 | ~$258.36 |
| **Estimated Total (with 2 EIPs + ALB)** | | | ~$290–300 |

*Windows Server licensing is included in the On-Demand rate.*

### 3.2 Annual Cost & Savings Options

| Pricing Model | Hourly Rate (per instance) | Monthly (2 instances) | Annual (2 instances) |
|---|---|---|---|
| On-Demand | ~$0.166/hr | ~$242.36 | ~$2,908 |
| 1-Year Reserved (No Upfront) | ~$0.105/hr | ~$153.24 | ~$1,839 |
| 1-Year Reserved (All Upfront) | ~$0.097/hr | ~$141.58 | ~$1,699 |
| 3-Year Reserved (All Upfront) | ~$0.066/hr | ~$96.36 | ~$1,156 avg/yr |

---

## 4. Pre-Requisites

- Active AWS account with EC2 permissions
- IAM user or role with at minimum `AmazonEC2FullAccess`
- A Key Pair created in the target region
- A VPC with at least one subnet (default VPC works for initial setup)
- AWS Console access via a supported browser
- A registered domain name (required for TLS on WIN-SERVER-02)
- Genetec Security Center installed and licensed (DAP program required)
- Genetec Platform SDK installer downloaded from the Genetec Portal

---

## 5. Manual Deployment via AWS Console

Complete all steps for WIN-SERVER-01 first, then repeat for WIN-SERVER-02.

### Step 1: Create a Key Pair (Do Once)

1. Navigate to **EC2 > Network & Security > Key Pairs**
2. Click **Create key pair**
3. Name: `windows-servers-key`
4. Type: **RSA**, Format: **.pem**
5. Click **Create key pair** — the `.pem` file downloads automatically. Store it securely.

> **NOTE:** You only need one Key Pair for both servers. The `.pem` file cannot be re-downloaded and is required to retrieve your Windows RDP password.

### Step 2: Create a Security Group

1. Navigate to **EC2 > Network & Security > Security Groups**
2. Click **Create security group**
3. Name: `windows-servers-sg`, VPC: your target VPC
4. Add the following inbound rules:

| Type | Protocol | Port | Source | Purpose |
|---|---|---|---|---|
| RDP | TCP | 3389 | Your IP (e.g. 203.0.113.45/32) | Admin RDP access |
| All Traffic | All | All | windows-servers-sg (self) | Server-to-server communication |
| HTTPS | TCP | 443 | 0.0.0.0/0 | MCP server public access |
| HTTP | TCP | 80 | 0.0.0.0/0 | Let's Encrypt / ALB health checks |

5. Leave outbound as default (Allow All)
6. Click **Create security group**

### Step 3: Launch WIN-SERVER-01

1. Navigate to **EC2 > Instances > Launch instances**
2. Name: `WIN-SERVER-01`
3. AMI: **Microsoft Windows Server 2022 Base** (64-bit x86)
4. Instance type: **t3.large**
5. Key pair: `windows-servers-key`
6. Network settings → Edit:
   - VPC: your target VPC
   - Subnet: choose a subnet (note the AZ)
   - Auto-assign public IP: **Enable**
   - Security group: **windows-servers-sg**
7. Storage: **100 GB gp3**
8. Click **Launch instance**

### Step 4: Launch WIN-SERVER-02

Repeat Step 3 with:
- Name: `WIN-SERVER-02`
- All other settings identical

WIN-SERVER-02 will be configured as the Genetec MCP server in Section 8.

### Step 5: Connect via RDP

1. Select the instance in EC2 > Instances
2. Click **Connect > RDP client tab**
3. Click **Get password**, upload your `.pem` file, click **Decrypt password**
4. Use the Public IP, username `Administrator`, and the decrypted password to RDP in

### Step 6: Verify Connectivity Between Instances

RDP into WIN-SERVER-01 and run in PowerShell:

```powershell
Test-NetConnection -ComputerName <WIN-SERVER-02 Private IP> -Port 3389
```

`TcpTestSucceeded : True` confirms the Security Group self-referencing rule is working.

#### Enabling Ping Between Servers

ICMP (ping) is blocked by default on Windows Server 2022. To enable it, run this on **both servers** in PowerShell (Run as Administrator):

```powershell
New-NetFirewallRule -DisplayName "Allow ICMPv4 Inbound" `
  -Direction Inbound `
  -Protocol ICMPv4 `
  -IcmpType 8 `
  -Action Allow `
  -Profile Any
```

After running on both servers, `ping <private IP>` will work. Note that ping is not required for the Genetec MCP deployment — TCP connectivity is what matters.

---

## 6. Security Best Practices

The following security measures should be applied to both instances. Full implementation instructions are in [Section 9](#9-security-best-practices--implementation-guide).

| # | Practice | Applies To | Frequency |
|---|---|---|---|
| 1 | Restrict RDP (3389) to specific IP ranges only — never 0.0.0.0/0 | Both | Per-server |
| 2 | Enable AWS Systems Manager Session Manager | Both | Per-server |
| 3 | Enable CloudTrail | AWS account | One-time |
| 4 | Enable automatic Windows Updates / Patch Manager | Both | Per-server |
| 5 | Configure daily EBS Snapshots via AWS Backup | Both | One-time setup |
| 6 | Apply least-privilege IAM roles | Both | Per-server |
| 7 | Tag instances with Environment, Project, Owner | Both | Per-server |
| 8 | Implement authentication for WIN-SERVER-02 MCP endpoint | WIN-SERVER-02 | Per-server |

---

## 7. Deployment Checklist

| Task | WIN-SERVER-01 | WIN-SERVER-02 |
|---|---|---|
| Create Key Pair | [ ] | N/A (reuse) |
| Create Security Group | [ ] | N/A (reuse) |
| Launch EC2 t3.large Windows 2022 | [ ] | [ ] |
| Configure 100 GB gp3 EBS | [ ] | [ ] |
| Attach windows-servers-sg | [ ] | [ ] |
| Retrieve RDP password | [ ] | [ ] |
| Verify RDP connectivity | [ ] | [ ] |
| Verify TCP connectivity to other server | [ ] | [ ] |
| Enable Windows Updates | [ ] | [ ] |
| Configure CloudTrail & billing alarm | [ ] (account-level) | N/A |
| Configure EBS Snapshot schedule | [ ] | [ ] |
| Install .NET 8 Runtime | N/A | [ ] |
| Install NuGet dependencies in SDK directory (Step 1d) | N/A | [ ] |
| Place SDK certificate in SDK directory (Step 1e) | N/A | [ ] |
| Install Python / uv | N/A | [ ] |
| Clone genetec_mcp_server repo | N/A | [ ] |
| Configure .env file | N/A | [ ] |
| uv sync dependencies | N/A | [ ] |
| Test server manually | N/A | [ ] |
| Verify SDK connection to Security Center (Step 6a) | N/A | [ ] |
| Install NSSM service | N/A | [ ] |
| Configure Windows Firewall port 8000 | N/A | [ ] |
| Register domain in Route 53 | N/A | [ ] (one-time) |
| Request ACM certificate | N/A | [ ] |
| Create Target Group (mcp-server-tg) | N/A | [ ] |
| Create ALB (mcp-alb) | N/A | [ ] |
| Set ALB idle timeout to 600s | N/A | [ ] |
| Add Route 53 alias to ALB | N/A | [ ] |
| Verify ALB target healthy | N/A | [ ] |
| Test /mcp endpoint end-to-end | N/A | [ ] |
| Add connector in Claude Desktop | N/A | [ ] |

---

## 8. Configuring WIN-SERVER-02 as the Genetec Remote MCP Server

This section deploys [brandon-kudlik/genetec_mcp_server](https://github.com/brandon-kudlik/genetec_mcp_server) on WIN-SERVER-02. The server is a Python application managed by `uv` that connects to a Genetec Security Center directory and exposes tools to Claude Desktop over HTTPS using the Streamable HTTP MCP transport.

> **NOTE:** All steps are performed on WIN-SERVER-02 via RDP unless stated otherwise. Complete Sections 1–7 first.

### 8.1 Target Architecture

| Layer | Component | Purpose |
|---|---|---|
| Internet-facing | AWS ALB (port 443) | TLS termination, ACM certificate, idle-timeout control |
| DNS | Route 53 alias to ALB | mcp.yourdomain.com → ALB DNS name |
| TLS | AWS Certificate Manager (ACM) | Free auto-renewing certificate |
| Application | Python FastMCP (uvicorn, port 8000) | Streamable HTTP MCP transport |
| Genetec SDK | .NET 8 runtime + Genetec.Sdk.dll | Platform SDK connection to Security Center |
| Python runtime | uv (managed Python 3.12+) | Dependency isolation, reproducible installs |
| Service management | NSSM Windows Service | Auto-start, auto-restart on failure, log rotation |
| Certificates folder | `C:\mcp\Certificates\` | Genetec SDK TLS/identity certificates |

> **WARNING:** Do NOT use IIS or IIS ARR as a reverse proxy. IIS buffers HTTP responses which breaks SSE streaming. The Python server listens on plain HTTP port 8000 internally. All external HTTPS is handled by the ALB.

---

### 8.2 Step 1: Genetec Security Center Pre-Requisites

#### 1a. Join the Genetec Development Acceleration Program (DAP)

1. Visit [https://developer.genetec.com](https://developer.genetec.com) and register
2. Download the Security Center installer and SDK installer from the Genetec Portal
3. You will receive a development license for Security Center

#### 1b. Install Security Center (WIN-SERVER-01 or separate machine)

1. Run the Security Center installer
2. Activate the DAP development license
3. Note the Directory hostname or IP and port (default: `4502`)
4. Note the admin username and password — these go in the `.env` file

#### 1c. Install the Genetec Platform SDK on WIN-SERVER-02

1. Copy the SDK installer to WIN-SERVER-02 via RDP file transfer
2. Run the SDK installer
3. The SDK installs `Genetec.Sdk.dll` and supporting .NET assemblies
4. Default SDK path: `C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows`

#### 1d. Install Missing NuGet Dependencies in the SDK Directory

The Genetec SDK 5.13 ships without several required NuGet packages. Without these DLLs, the SDK's `SecurityTokenHelper` static constructor fails silently, causing every login attempt to return a generic `Failed` error code regardless of whether credentials are correct. This is the most common cause of connection failures on fresh deployments.

> **WARNING:** This step is mandatory. The SDK installer does not include these DLLs, and they are not part of the git repository. Every new machine that runs the MCP server must have these DLLs manually placed in the SDK directory.

Since WIN-SERVER-02 only has the .NET 8 runtime (not the SDK), download each package directly from NuGet.org:

```powershell
$sdkPath = "C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
New-Item -ItemType Directory -Path C:\Temp\nuget -Force

# Define all required packages: Name, Version, TFM subfolder
$packages = @(
    @("Microsoft.Extensions.Caching.Memory", "2.1.23", "netstandard2.0"),
    @("Microsoft.Extensions.Caching.Abstractions", "2.1.2", "netstandard2.0"),
    @("Microsoft.Extensions.Options", "2.1.1", "netstandard2.0"),
    @("BouncyCastle.Cryptography", "2.4.0", "net6.0"),
    @("System.ServiceModel.Primitives", "4.10.3", "net6.0"),
    @("System.ServiceModel.Http", "4.10.3", "net6.0"),
    @("System.ServiceModel.NetTcp", "4.10.3", "net6.0"),
    @("System.ServiceModel.Security", "4.10.3", "net6.0"),
    @("System.ServiceModel.Duplex", "4.10.3", "net6.0"),
    @("System.Private.ServiceModel", "4.10.3", "net6.0"),
    @("System.Security.Cryptography.Pkcs", "8.0.0", "net8.0"),
    @("System.Formats.Asn1", "8.0.0", "net8.0"),
    @("System.Security.Cryptography.Xml", "6.0.1", "net6.0"),
    @("Microsoft.Extensions.ObjectPool", "5.0.10", "net5.0")
)

foreach ($pkg in $packages) {
    $name = $pkg[0]; $version = $pkg[1]; $tfm = $pkg[2]
    $zipPath = "C:\Temp\nuget\$name.zip"
    $extractPath = "C:\Temp\nuget\$name"
    $dllPath = "$extractPath\lib\$tfm\$name.dll"
    $destPath = Join-Path $sdkPath "$name.dll"

    if (Test-Path $destPath) {
        Write-Host "SKIP $name (already exists)"
        continue
    }

    Write-Host "Downloading $name v$version..."
    Invoke-WebRequest -Uri "https://www.nuget.org/api/v2/package/$name/$version" `
        -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

    if (Test-Path $dllPath) {
        Copy-Item $dllPath $destPath -Force
        Write-Host "OK $name"
    } else {
        Write-Host "WARNING: $dllPath not found — check TFM subfolder manually"
    }
}
```

**Verify all DLLs are present:**

```powershell
$sdkPath = "C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows"
@(
    "Microsoft.Extensions.Caching.Memory.dll",
    "Microsoft.Extensions.Caching.Abstractions.dll",
    "Microsoft.Extensions.Options.dll",
    "BouncyCastle.Cryptography.dll",
    "System.ServiceModel.Primitives.dll",
    "System.Private.ServiceModel.dll",
    "System.Security.Cryptography.Pkcs.dll",
    "System.Formats.Asn1.dll",
    "System.Security.Cryptography.Xml.dll",
    "Microsoft.Extensions.ObjectPool.dll"
) | ForEach-Object {
    $exists = Test-Path (Join-Path $sdkPath $_)
    Write-Host "$_ : $exists"
}
```

All entries must show `True`. If any show `False`, the SDK connection will fail silently.

#### 1e. Place the SDK Certificate in the SDK Directory

The SDK resolves its certificate from `<SDK_PATH>/certificates/Genetec.Sdk.Engine.cert` at runtime (via `SdkCertificateHelpers.GetCertificatePath()`). The repo ships a development certificate at `Certificates/python.exe.cert`, but it must also be copied to the SDK's expected location.

> **NOTE:** This step must be done after cloning the repository (Step 4b). If performing these steps in order, return to this step after cloning.

```powershell
$sdkPath = "C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows"
$certDir = Join-Path $sdkPath "certificates"

New-Item -ItemType Directory -Path $certDir -Force
Copy-Item "C:\mcp\genetec_mcp_server\Certificates\python.exe.cert" `
    (Join-Path $certDir "Genetec.Sdk.Engine.cert") -Force

# Verify
Get-Content (Join-Path $certDir "Genetec.Sdk.Engine.cert")
```

You should see the XML certificate with the DAP development `ApplicationId`.

---

### 8.3 Step 2: Install the .NET 8 Runtime on WIN-SERVER-02

The Genetec Platform SDK requires .NET 8. Run all commands in PowerShell (Run as Administrator).

**Check if .NET 8 is already installed:**
```powershell
dotnet --list-runtimes
```
If you see `Microsoft.NETCore.App 8.x.x`, skip to Step 3.

**If `dotnet` is not recognized or the runtime is missing:**

```powershell
# Step 1 — Create temp folder and force TLS 1.2
New-Item -ItemType Directory -Path C:\Temp -Force
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Step 2 — Download the official Microsoft install script
# If Invoke-WebRequest fails, use: curl.exe -L "https://dot.net/v1/dotnet-install.ps1" -o "C:\Temp\dotnet-install.ps1"
Invoke-WebRequest -Uri "https://dot.net/v1/dotnet-install.ps1" `
  -OutFile "C:\Temp\dotnet-install.ps1" `
  -UseBasicParsing

# Step 3 — Allow the script to run and install .NET 8 system-wide
Set-ExecutionPolicy Bypass -Scope Process -Force
& C:\Temp\dotnet-install.ps1 -Channel 8.0 -Runtime dotnet -InstallDir "C:\Program Files\dotnet"

# Step 4 — Add dotnet to the system PATH permanently
$existingPath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
if ($existingPath -notlike "*C:\Program Files\dotnet*") {
    [System.Environment]::SetEnvironmentVariable(
        "Path", "$existingPath;C:\Program Files\dotnet", "Machine"
    )
}

# Step 5 — Reload PATH in current session and verify
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")
dotnet --list-runtimes
```

You should see `Microsoft.NETCore.App 8.0.x` in the output.

> **NOTE:** The original `.msi` direct download approach is unreliable — Microsoft's CDN URLs change with each patch release. The `dotnet-install.ps1` script is the official Microsoft-recommended automation method and always pulls the latest 8.0.x patch.

---

### 8.4 Step 3: Install Python and uv on WIN-SERVER-02

The Genetec MCP server uses `uv` for Python version management and dependency installation. `uv` reads `.python-version` and `uv.lock` from the repo to create a fully reproducible environment.

**Install uv:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell, then verify:
```powershell
uv --version
```

> **NOTE:** Do not attempt to manually check `.python-version` before cloning the repo — that file doesn't exist yet. `uv` will automatically detect and use the correct Python version when you run `uv sync` in Step 5.

---

### 8.5 Step 4: Clone the Repository and Configure Environment

All commands run in PowerShell (Run as Administrator) on WIN-SERVER-02.

#### 4a. Install Git (if not already present)

```powershell
git --version
```

If Git is not found:
```powershell
$url = 'https://github.com/git-for-windows/git/releases/download/v2.47.0.windows.1/Git-2.47.0-64-bit.exe'
Invoke-WebRequest -Uri $url -OutFile 'C:\Temp\git.exe'
Start-Process 'C:\Temp\git.exe' -ArgumentList '/VERYSILENT /NORESTART' -Wait
```

Reopen PowerShell and verify: `git --version`

#### 4b. Clone the repository

```powershell
New-Item -ItemType Directory -Path C:\mcp -Force
Set-Location C:\mcp
git clone https://github.com/brandon-kudlik/genetec_mcp_server.git
Set-Location C:\mcp\genetec_mcp_server
```

Verify the structure:
```powershell
Get-ChildItem -Name
```

You should see: `Certificates`, `src`, `tests`, `.env.example`, `.python-version`, `CLAUDE.md`, `README.md`, `genetec_sdk.runtimeconfig.json`, `pyproject.toml`, `uv.lock`

#### 4c. Create and configure the .env file

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill in all values. The `.env` file contains the following variables:

| Variable | Example Value | Description |
|---|---|---|
| `GENETEC_SDK_PATH` | `C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows` | Path to the Genetec SDK DLLs |
| `GENETEC_CONFIG_PATH` | `C:\ProgramData\Genetec Security Center 5.13` | Path for .gconfig files (auto-created if missing) |
| `GENETEC_SERVER` | `172.31.25.170` | IP or hostname of the Security Center Directory server |
| `GENETEC_USERNAME` | `api` | Security Center username |
| `GENETEC_PASSWORD` | `YourPassword` | Security Center password |
| `GENETEC_CLIENT_CERTIFICATE` | *(commented out by default)* | SDK client certificate ApplicationId — leave commented to use the default development cert |

> **NOTE:** `GENETEC_SERVER` uses a private IP in the `172.31.x.x` range — the AWS default VPC subnet. This means your Security Center directory is inside AWS and WIN-SERVER-02 reaches it directly over the private network with no internet hop. Leave `GENETEC_CLIENT_CERTIFICATE` commented out for development.

> **NOTE:** There is no `MCP_TOKEN` or HTTP authentication layer in this server. The MCP endpoint is currently unauthenticated at the HTTP level — access control is provided by the ALB Security Group and network-level restrictions. See Section 9, Item 8 for hardening options.

#### 4d. Copy Certificates

```powershell
Get-ChildItem C:\mcp\genetec_mcp_server\Certificates
```

If the Certificates folder is empty, obtain the required Genetec certificates from your Security Center installation and place them here. Consult the Genetec DAP documentation for your SDK version.

---

### 8.6 Step 5: Install Python Dependencies with uv

```powershell
Set-Location C:\mcp\genetec_mcp_server
uv sync
```

`uv` will create a `.venv` virtual environment, install the required Python version from `.python-version`, and install all packages pinned in `uv.lock`.

Verify:
```powershell
Get-Item .venv
```

---

### 8.7 Step 6: Test the Server Manually

Always test interactively before installing as a service — errors appear directly in the console.

#### 6a. Verify SDK Connection to Security Center

Before starting the MCP server, verify the SDK can connect to Security Center. This isolates SDK/credential/certificate issues from MCP transport issues.

```powershell
Set-Location C:\mcp\genetec_mcp_server
uv run python -c "
from genetec_mcp_server.connection import GenetecConnection
conn = GenetecConnection()
result = conn.connect()
print(f'Connect result: {result}')
print(f'Is connected: {conn.is_connected}')
print(f'Last failure: {conn.last_failure}')
if conn.is_connected:
    version = conn.get_system_version()
    print(f'Version: {version}')
conn.dispose()
"
```

**Expected output:**
```
Connect result: Success
Is connected: True
Last failure: None
Version: 5.13.3132.18
```

**If you see `Connect result: Failed`:**
- A generic `Failed` code that occurs regardless of correct/wrong credentials means the failure is **pre-authentication** — caused by a missing NuGet DLL or certificate, not credentials
- Verify all NuGet DLLs are present (Step 1d verification script)
- Verify the SDK certificate exists at `<SDK_PATH>\certificates\Genetec.Sdk.Engine.cert` (Step 1e)
- Test network connectivity: `Test-NetConnection -ComputerName 172.31.25.170 -Port 4502`

**If you see `Connect result: Timeout`:**
- The Directory server is unreachable — check network, Security Group, and Windows Firewall

> **WARNING:** The MCP server's `app_lifespan` does not log or check the return value of `conn.connect()`. The server will start and appear healthy even if the SDK connection fails. Always run this verification step on a new deployment before proceeding.

Do not proceed to 6b until this step returns `Success`.

#### 6b. Start the server interactively

**Window 1 — Start the server:**
```powershell
Set-Location C:\mcp\genetec_mcp_server
uv run genetec-mcp-server
```

Watch for:
- A line confirming it's listening on port 8000
- A successful connection message to the Genetec Security Center directory
- Any certificate or authentication errors — resolve these before continuing

**Window 2 — Test the MCP endpoint:**

The Streamable HTTP transport requires the correct `Accept` header. Test with:

```powershell
$headers = @{
  "Content-Type"         = "application/json"
  "Accept"               = "application/json, text/event-stream"
  "MCP-Protocol-Version" = "2025-03-26"
}
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
Invoke-WebRequest -Uri "http://localhost:8000/mcp" `
  -Method POST -Headers $headers -Body $body -UseBasicParsing
```

Expected response: **HTTP 200** with an `Mcp-Session-Id` header containing a UUID.

> **NOTE:** If you see `ASGI callable returned without completing response` with a `ClosedResourceError`, this is a known race condition in the MCP Python SDK's stateful Streamable HTTP mode. The POST handler tries to write to a session stream that isn't open yet. This does not occur when Claude Desktop connects because it opens the GET SSE stream first. For manual testing use the MCP Inspector instead:
> ```powershell
> npx @modelcontextprotocol/inspector http://localhost:8000/mcp
> ```

Press **Ctrl+C** in Window 1 to stop the server before proceeding.

---

### 8.8 Step 7: Install NSSM and Register as a Windows Service

All commands run in PowerShell (Run as Administrator).

#### 7a. Install NSSM

```powershell
New-Item -ItemType Directory -Path C:\Temp -Force
$url = 'https://nssm.cc/release/nssm-2.24.zip'
Invoke-WebRequest -Uri $url -OutFile C:\Temp\nssm.zip
Expand-Archive -Path C:\Temp\nssm.zip -DestinationPath C:\Temp\nssm -Force
Copy-Item 'C:\Temp\nssm\nssm-2.24\win64\nssm.exe' 'C:\Windows\System32\nssm.exe' -Force
nssm version
```

#### 7b. Find the uv executable path

```powershell
(Get-Command uv).Source
```

Note the full path (e.g. `C:\Users\Administrator\.local\bin\uv.exe`).

#### 7c. Register the service

```powershell
# Replace <UV_PATH> with the path from 7b
nssm install GenetecMCPServer "<UV_PATH>"

nssm set GenetecMCPServer AppDirectory   "C:\mcp\genetec_mcp_server"
nssm set GenetecMCPServer AppParameters  "run genetec-mcp-server"
nssm set GenetecMCPServer AppExit        Default Restart
nssm set GenetecMCPServer AppRestartDelay 5000
nssm set GenetecMCPServer Start          SERVICE_DELAYED_AUTO_START
nssm set GenetecMCPServer DisplayName    "Genetec MCP Server"
nssm set GenetecMCPServer Description    "Genetec Security Center MCP server for Claude Desktop"
```

#### 7d. Configure logging

```powershell
New-Item -ItemType Directory -Path C:\mcp\genetec_mcp_server\logs -Force
nssm set GenetecMCPServer AppStdout      "C:\mcp\genetec_mcp_server\logs\stdout.log"
nssm set GenetecMCPServer AppStderr      "C:\mcp\genetec_mcp_server\logs\stderr.log"
nssm set GenetecMCPServer AppRotateFiles 1
nssm set GenetecMCPServer AppRotateSeconds 86400
nssm set GenetecMCPServer AppRotateBytes 10485760
```

#### 7e. Set service account

```powershell
nssm set GenetecMCPServer ObjectName LocalSystem
```

> **NOTE:** If `uv` is installed per-user (e.g., under `C:\Users\Administrator`), LocalSystem may not find it. In that case run:
> ```powershell
> nssm set GenetecMCPServer ObjectName .\Administrator
> ```
> You will be prompted for the Administrator password.

#### 7f. Start and verify

```powershell
nssm start GenetecMCPServer
Get-Service GenetecMCPServer
Start-Sleep 5
Get-Content C:\mcp\genetec_mcp_server\logs\stdout.log -Tail 20
Invoke-WebRequest -Uri http://localhost:8000/mcp -Method GET -UseBasicParsing
```

A `406` response on the GET confirms the server is running and responding correctly — the MCP endpoint only accepts POST with the correct `Accept` header, so 406 on a plain GET is expected healthy behavior.

**Verify auto-start after reboot:**
```powershell
Restart-Computer -Force
```

After the instance restarts, RDP back in and run `Get-Service GenetecMCPServer` — it must show `Running` automatically.

---

### 8.9 Step 8: Configure Windows Firewall

```powershell
New-NetFirewallRule -DisplayName 'Genetec MCP Server Port 8000' `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8000 `
  -Action Allow `
  -Profile Any `
  -Description 'Allows ALB to forward HTTPS traffic to uvicorn'

# Verify
Get-NetFirewallRule -DisplayName 'Genetec MCP Server Port 8000' | Select-Object Name,Enabled,Action
```

> **NOTE:** Port 443 does not need a Windows Firewall rule. TLS is terminated at the ALB — the Python server only receives plain HTTP on port 8000 from the ALB's internal VPC forwarding.

---

### 8.10 Step 9: Register a Domain and Request an ACM Certificate

A domain name is required to issue a TLS certificate for the ALB.

#### 9a. Register a domain in Route 53

1. Navigate to **Route 53 > Registered domains > Register domain**
2. Search for your preferred domain name (e.g., `genetec-mcp.com`)
3. Select an available domain, click **Proceed to checkout**
4. Fill in registrant contact details (required by ICANN)
5. Leave **Auto-renew** enabled
6. Click **Complete order**

Registration takes 5–30 minutes. Route 53 automatically creates a Hosted Zone when registration completes.

#### 9b. Confirm the Hosted Zone exists

1. Navigate to **Route 53 > Hosted zones**
2. Your domain should appear with type **Public hosted zone**
3. It will contain NS and SOA records by default — this is correct

#### 9c. Request an ACM Certificate

> **IMPORTANT:** Ensure you are in the same AWS region as your ALB (e.g., `us-east-1`) before requesting the certificate.

1. Navigate to **AWS Certificate Manager > Request a certificate**
2. Select **Request a public certificate**, click **Next**
3. Fully qualified domain name: `mcp.yourdomain.com`
4. Validation method: **DNS validation**
5. Click **Request**
6. On the certificate details page, click **Create records in Route 53**
7. Wait 5–10 minutes for status to show **Issued**

> **NOTE:** The DNS validation CNAME record must remain in Route 53 permanently — it is used for auto-renewal.

---

### 8.11 Step 10: Create the Target Group and ALB

#### 10a. Create the Target Group

1. Navigate to **EC2 > Load Balancing > Target Groups > Create target group**
2. Target type: **Instances**
3. Name: `mcp-server-tg`
4. Protocol: **HTTP**, Port: **8000**
5. VPC: same VPC as WIN-SERVER-02
6. Protocol version: **HTTP1**
7. Health check settings:
   - Protocol: HTTP
   - Path: `/mcp`
   - **Success codes: `200-406`** — the server returns 406 on a plain GET to `/mcp` (no Accept header), which is correct healthy behavior
   - Healthy threshold: 2
   - Unhealthy threshold: 3
   - Interval: 30 seconds
8. Click **Next**, select WIN-SERVER-02, click **Include as pending below**
9. Click **Create target group**

#### 10b. Create the Application Load Balancer Security Group

1. Navigate to **EC2 > Security Groups > Create security group**
2. Name: `mcp-alb-sg`
3. Inbound rules:
   - HTTPS TCP 443 from `0.0.0.0/0`
   - HTTP TCP 80 from `0.0.0.0/0`
4. Outbound: leave default (Allow All)
5. Click **Create security group**

#### 10c. Allow the ALB to reach WIN-SERVER-02 on port 8000

1. Navigate to **EC2 > Security Groups > windows-servers-sg**
2. Click **Edit inbound rules > Add rule**
3. Type: Custom TCP, Port: **8000**, Source: **mcp-alb-sg**
4. Click **Save rules**

This ensures port 8000 is only reachable from the ALB — not directly from the internet.

#### 10d. Create the Application Load Balancer

1. Navigate to **EC2 > Load Balancing > Load Balancers > Create load balancer > Application Load Balancer**
2. Name: `mcp-alb`, Scheme: **Internet-facing**, IP type: **IPv4**
3. VPC and subnets: select your VPC and at least **two Availability Zone subnets**
4. Security group: select **mcp-alb-sg** (remove any pre-selected default SG)
5. Listener: **HTTPS, port 443**, forward to `mcp-server-tg`
6. Certificate: **From ACM** → select `mcp.yourdomain.com`
7. Click **Create load balancer**
8. Note the ALB DNS name (e.g., `mcp-alb-123456789.us-east-1.elb.amazonaws.com`)

#### 10e. CRITICAL: Increase the ALB Idle Timeout

The default ALB idle timeout is 60 seconds. SSE connections idle longer than this will be dropped. This must be changed before the MCP server will work reliably.

1. Select `mcp-alb` in the load balancers list
2. Click **Attributes > Edit**
3. Change **Idle timeout** from `60` to `600`
4. Click **Save changes**

Or via AWS CLI:
```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <your ALB ARN> \
  --attributes Key=idle_timeout.timeout_seconds,Value=600
```

#### 10f. Create the Route 53 DNS record

1. Navigate to **Route 53 > Hosted zones > your domain > Create record**
2. Record name: `mcp`
3. Record type: **A**
4. Enable **Alias**
5. Route traffic to: **Alias to Application and Classic Load Balancer**
6. Select your region, select `mcp-alb`
7. Click **Create records**

---

### 8.12 Step 11: Verify End-to-End Connectivity

#### 11a. Verify ALB target health

1. Navigate to **EC2 > Load Balancing > Target Groups > mcp-server-tg > Targets tab**
2. WIN-SERVER-02 should show **Status: healthy**

If unhealthy, check in order:
- `Get-Service GenetecMCPServer` on WIN-SERVER-02 — must show Running
- `Get-NetFirewallRule -DisplayName "Genetec MCP Server Port 8000"` — must be enabled
- Security Group `windows-servers-sg` has inbound TCP 8000 from `mcp-alb-sg`
- Target group health check path is `/mcp` with success codes `200-406`

#### 11b. Test from your local machine (macOS/Linux)

```zsh
curl -X POST https://mcp.yourdomain.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  -v
```

**Expected output includes:**
- `HTTP/2 200`
- `mcp-session-id: <uuid>` in the response headers
- `content-type: text/event-stream`
- `server: uvicorn`

The curl error `HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR (err 2)` at the end is **not a real error** — it occurs because curl immediately closes the SSE stream connection after receiving the response. Claude Desktop keeps the connection open and does not trigger this. If you see a 200 and an `Mcp-Session-Id` header, the server is working correctly.

#### 11b. Test from your local machine (Windows PowerShell)

```powershell
$headers = @{
  "Content-Type" = "application/json"
  "Accept"       = "application/json, text/event-stream"
}
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
Invoke-WebRequest -Uri "https://mcp.yourdomain.com/mcp" `
  -Method POST -Headers $headers -Body $body -UseBasicParsing
```

---

### 8.13 Step 12: Add the Genetec MCP Server to Claude Desktop

Remote MCP servers are added through the **Connectors UI** — not via `claude_desktop_config.json`, which only supports local stdio servers.

**Via Claude Desktop:**

1. Open Claude Desktop
2. Click profile icon (top-right) → **Settings → Connectors**
3. Click **Add connector**
4. Fill in:
   - **Name:** `Genetec Security Center`
   - **URL:** `https://mcp.yourdomain.com/mcp`
   - **Authentication:** None
5. Click **Save**
6. A green indicator confirms a successful connection
7. Start a new conversation and ask: *"What tools do you have?"* — Claude should list the Genetec tools

**Via claude.ai (web):**

1. Sign in → Profile icon → **Settings → Connectors → Add connector**
2. Enter the URL and click **Save**

> **NOTE:** Free plan accounts are limited to 1 custom connector. Pro, Max, Team, and Enterprise plans support multiple connectors.

---

### 8.14 Step 13: Updating the Server

When the repository receives updates:

```powershell
nssm stop GenetecMCPServer
Set-Location C:\mcp\genetec_mcp_server
git pull origin main
uv sync
nssm start GenetecMCPServer
Get-Service GenetecMCPServer
Get-Content .\logs\stdout.log -Tail 30
```

---

### 8.15 Troubleshooting Reference

| Symptom | Root Cause | Fix |
|---|---|---|
| Service starts then stops | Python import error or missing .env variable | Run `uv run genetec-mcp-server` manually; read stderr output directly |
| Cannot connect to Genetec directory | Wrong `GENETEC_SERVER`, port, or credentials | Verify values; test: `Test-NetConnection -ComputerName <ip> -Port 4502` |
| Genetec SDK DLL not found | .NET 8 runtime missing or SDK not installed | Run `dotnet --list-runtimes`; reinstall SDK if needed |
| ALB target shows unhealthy | Port 8000 blocked or server not running | Check service, firewall rule, SG rule, and health check path/codes |
| `dotnet` not recognized after install | PATH not updated in current session | Run: `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")` |
| `Invoke-WebRequest` SSL error downloading scripts | TLS version mismatch | Add: `[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12` |
| Connection drops after ~5 min | ALB idle timeout at default 60s | Confirm ALB idle timeout is set to 600s (Step 10e) |
| uv command not found in service | uv installed per-user; LocalSystem can't see it | Set service to run as Administrator: `nssm set GenetecMCPServer ObjectName .\Administrator` |
| Certificate errors on Genetec connection | Certificates folder empty | Place correct Genetec certificates in `C:\mcp\genetec_mcp_server\Certificates\` |
| Generic `Failed` login — same error with correct and wrong credentials | Missing NuGet DLL in SDK directory (pre-auth failure) | Run Step 1d verification script; most commonly `Microsoft.Extensions.Caching.Abstractions.dll` is missing. Download from NuGet.org and place in SDK directory (see Step 1d) |
| SDK cert file not found at runtime | `Genetec.Sdk.Engine.cert` missing from `<SDK_PATH>/certificates/` | Copy `Certificates/python.exe.cert` to `<SDK_PATH>/certificates/Genetec.Sdk.Engine.cert` (see Step 1e) |
| Server starts, ALB healthy, but tool calls return "Not connected to Security Center" | `conn.connect()` failed silently during startup | Run the SDK connection verification script (Step 6a) to see the actual failure code; the MCP server does not log connection failures |
| ALB target shows `Target.Timeout` after reboot | NSSM service did not auto-start | Check `Get-Service GenetecMCPServer`; verify start type with `nssm get GenetecMCPServer Start`; check Windows Event Log: `Get-EventLog -LogName System -Source "Service Control Manager" -Newest 20` |
| ASGI ClosedResourceError on POST | Race condition in MCP SDK stateful mode | Use MCP Inspector for testing: `npx @modelcontextprotocol/inspector http://localhost:8000/mcp` |
| 406 on GET to /mcp | Expected — MCP endpoint requires POST + Accept header | Not an error; set ALB health check success codes to `200-406` |
| curl INTERNAL_ERROR after 200 | curl closes SSE stream abruptly | Not an error; if you got 200 + Mcp-Session-Id the server is working |

---

## 9. Security Best Practices — Implementation Guide

### Item 1: Restrict RDP to Specific IP Ranges

RDP (TCP 3389) exposed to `0.0.0.0/0` is one of the most frequently brute-forced attack surfaces on Windows servers. Restrict it immediately.

**Find your public IP:**
```zsh
# macOS/Linux
curl ifconfig.me
```
```powershell
# Windows
Invoke-WebRequest -Uri "https://ifconfig.me" -UseBasicParsing
```

**Update the Security Group:**

1. Navigate to **EC2 > Security Groups > windows-servers-sg > Inbound rules > Edit inbound rules**
2. Find the RDP row (TCP 3389)
3. Change Source from `0.0.0.0/0` to your IP in CIDR notation (e.g., `203.0.113.45/32`)
4. For multiple admin locations, add a second RDP rule for each IP range
5. Click **Save rules**

> **WARNING:** Never leave RDP open to `0.0.0.0/0`. Automated bots scan the internet for open RDP ports and attempt brute-force logins within minutes.

**Verify:** Attempt RDP from a machine outside your allowed range — it should time out (not refuse).

---

### Item 2: Enable AWS Systems Manager Session Manager

Session Manager provides browser-based shell access without opening any inbound ports, without RDP passwords, and with full audit logging.

**Create an IAM Role:**

1. Navigate to **IAM > Roles > Create role**
2. Trusted entity: **AWS service > EC2**
3. Attach policy: `AmazonSSMManagedInstanceCore`
4. Role name: `EC2-SSM-Role`
5. Click **Create role**

**Attach to each instance:**

1. Select WIN-SERVER-01 in EC2
2. **Actions > Security > Modify IAM role**
3. Select `EC2-SSM-Role`, click **Update IAM role**
4. Repeat for WIN-SERVER-02

**Verify SSM Agent is running (on each server via RDP):**

```powershell
Get-Service AmazonSSMAgent
# If stopped:
Start-Service AmazonSSMAgent
Set-Service AmazonSSMAgent -StartupType Automatic
```

**Connect via Session Manager:**

1. Navigate to **Systems Manager > Session Manager > Start session**
2. Select WIN-SERVER-01, click **Start session**
3. A PowerShell window opens in the browser — no RDP, no open port, no password

> **NOTE:** Enable session logging under Systems Manager > Session Manager > Preferences > CloudWatch Logs for a full audit trail of all commands.

---

### Item 3: Enable AWS CloudTrail

CloudTrail records every API call in your AWS account — instance launches, security group changes, IAM modifications, S3 access.

1. Navigate to **AWS CloudTrail > Create trail**
2. Trail name: `account-audit-trail`
3. Storage: **Create new S3 bucket** (e.g., `cloudtrail-logs-youraccountid-2026`)
4. CloudWatch Logs: **Enable**, log group: `CloudTrail/AccountAuditTrail`
5. Event type: **Management events**, API activity: **Read and Write**
6. Click **Create trail**

**Verify:** Confirm Status shows **Logging: On**. Perform a test action (stop/start an instance) and check **CloudTrail > Event history** after 5–10 minutes.

---

### Item 4: Enable Windows Updates / AWS Patch Manager

**Option A — Direct PowerShell (simpler):**

```powershell
# Enable automatic updates
$AUSettings = (New-Object -ComObject 'Microsoft.Update.AutoUpdate').Settings
$AUSettings.NotificationLevel = 4       # Auto download and schedule install
$AUSettings.ScheduledInstallDay = 0     # Every day
$AUSettings.ScheduledInstallTime = 3    # 3 AM
$AUSettings.IncludeRecommendedUpdates = $true
$AUSettings.Save()

# Verify
(New-Object -ComObject 'Microsoft.Update.AutoUpdate').Settings.NotificationLevel
# Should return: 4

# Run updates immediately (may reboot)
Install-Module PSWindowsUpdate -Force -Scope AllUsers
Get-WindowsUpdate -AcceptAll -Install -AutoReboot
```

**Option B — AWS Systems Manager Patch Manager (recommended for managing both servers centrally):**

1. Navigate to **Systems Manager > Patch Manager > Configure patching**
2. Select both instances
3. Schedule: `cron(0 3 ? * SUN *)` — 3 AM every Sunday
4. Operation: **Install**
5. Click **Configure patching**

View compliance: **Systems Manager > Patch Manager > Dashboard**

---

### Item 5: Configure Daily EBS Snapshots via AWS Backup

#### Create a Backup Vault

1. Navigate to **AWS Backup > Backup vaults > Create backup vault**
2. Name: `windows-servers-vault`
3. Encryption: default AWS managed key
4. Click **Create backup vault**

#### Create a Backup Plan

1. Navigate to **AWS Backup > Backup plans > Create backup plan > Build a new plan**
2. Plan name: `windows-servers-daily`
3. Add backup rule:
   - Rule name: `DailySnapshots`
   - Vault: `windows-servers-vault`
   - Frequency: **Daily**
   - Start time: **02:00 UTC**
   - Retention: **30 days**
4. Click **Create plan**

#### Assign Resources

1. On the plan page, click **Assign resources**
2. Name: `both-windows-servers`
3. IAM role: `AWSBackupDefaultServiceRole`
4. Resource type: **EC2**, select both instances
5. Click **Assign resources**

> **NOTE:** EBS snapshot storage costs ~$0.05/GB-month. Two 100 GB volumes with 30-day daily snapshots typically cost $10–$30/month depending on change rate.

---

### Item 6: Apply Least-Privilege IAM Roles

**Verify no overly broad policies are attached:**

1. Navigate to **IAM > Roles > EC2-SSM-Role > Permissions tab**
2. Confirm ONLY `AmazonSSMManagedInstanceCore` is attached
3. If `AdministratorAccess`, `AmazonEC2FullAccess`, or `PowerUserAccess` appear — remove them immediately

> **WARNING:** A compromised EC2 instance with `AdministratorAccess` can delete all AWS resources, create backdoor IAM users, and exfiltrate data from S3.

**Create a dedicated scoped role for WIN-SERVER-02:**

1. **IAM > Roles > Create role > AWS service > EC2**
2. Attach: `AmazonSSMManagedInstanceCore` + optionally `CloudWatchAgentServerPolicy`
3. Role name: `EC2-SSM-MCP-Role`
4. Attach to WIN-SERVER-02: **EC2 > Actions > Security > Modify IAM role**

**Enable IAM Access Analyzer (one-time, account-level):**

1. Navigate to **IAM > Access Analyzer > Create analyzer**
2. Name: `AccountAccessAnalyzer`, Type: **Account**
3. Click **Create analyzer**
4. Review the **Findings** tab — any findings indicate resources accessible from outside your account

---

### Item 7: Tag Both EC2 Instances

Tags enable cost allocation, resource filtering, and automated operations.

**Apply tags via console:**

1. Select the instance in EC2
2. **Actions > Instance settings > Manage tags**
3. Apply the following tags:

| Tag Key | WIN-SERVER-01 | WIN-SERVER-02 |
|---|---|---|
| Name | WIN-SERVER-01 | WIN-SERVER-02 |
| Environment | Production | Production |
| Project | Genetec-MCP-Deployment | Genetec-MCP-Deployment |
| Owner | your-email@company.com | your-email@company.com |
| Role | Application-Server | MCP-Server |
| CostCenter | IT-Ops | IT-Ops |

**Apply the same tags to EBS volumes:**

1. Navigate to **EC2 > Elastic Block Store > Volumes**
2. Identify volumes by the Attached Instances column
3. Apply matching tags to each volume

**Enable cost allocation tags in Billing:**

1. Navigate to **AWS Billing > Cost allocation tags**
2. Activate: `Project`, `Environment`, `Owner`, `CostCenter`

---

### Item 8: Harden the MCP Endpoint (WIN-SERVER-02)

The Genetec MCP server has no built-in HTTP authentication. The following options provide increasing levels of protection.

#### Option A: Static IP Allowlist on the ALB Security Group (Quickest)

If Claude Desktop is always run from a fixed IP (e.g., a corporate network):

1. Navigate to **EC2 > Security Groups > mcp-alb-sg > Edit inbound rules**
2. Change the HTTPS (TCP 443) Source from `0.0.0.0/0` to your fixed IP range (e.g., `203.0.113.0/28`)
3. Click **Save rules**

> **WARNING:** This does not work with claude.ai (web) — claude.ai connects from dynamic AWS infrastructure IPs. Use this only with Claude Desktop from a fixed-IP location.

#### Option B: Amazon Cognito OAuth 2.1 (Recommended for Production)

Amazon Cognito provides a fully managed OAuth 2.1 authorization server with PKCE support and a free tier of 50,000 MAUs.

**Create a Cognito User Pool:**

1. Navigate to **Amazon Cognito > Create user pool**
2. Sign-in: **Username and Email**
3. MFA: **Optional MFA**, enable Authenticator apps
4. Self-service sign-up: **Disable** (admin-only account creation)
5. Click **Create user pool**, note the User Pool ID

**Create an App Client:**

1. In the User pool → **App integration tab > Create app client**
2. Name: `genetec-mcp-client`, Type: **Public client**
3. Grant type: **Authorization code grant**
4. Scopes: `openid`, `profile`
5. Callback URL: `https://claude.ai/api/mcp/auth_callback`
6. Click **Create app client**, note the Client ID

**Create a Cognito Domain:**

1. In App integration → **Domain > Create Cognito domain**
2. Prefix: `genetec-mcp-yourname`
3. Auth server URL: `https://genetec-mcp-yourname.auth.us-east-1.amazoncognito.com`

**Create a User:**

1. User pool → **Users tab > Create user**
2. Enter username and email, set temporary password
3. Click **Create user**

**Verify authentication is enforced:**

```zsh
# This should return 401
curl -X POST https://mcp.yourdomain.com/mcp \
  -H "Content-Type: application/json" \
  -d '{}' -v
```

---

*Pricing figures are approximate On-Demand rates for US East (N. Virginia) as of March 2026. Verify current prices at https://aws.amazon.com/ec2/pricing/on-demand/ before finalising budgets.*

*Genetec MCP server source: https://github.com/brandon-kudlik/genetec_mcp_server*

*MCP specification: https://modelcontextprotocol.io/specification/2025-03-26*
