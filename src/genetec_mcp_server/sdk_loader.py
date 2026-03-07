"""Load Genetec Security Center SDK assemblies via pythonnet with .NET 8.0 coreclr."""

import os
import sys
from pathlib import Path

from genetec_mcp_server.config import CONFIG_PATH, SDK_PATH, validate_sdk_path

_sdk_loaded = False
_runtime_configured = False

# Path to the runtimeconfig.json relative to the project root.
# This must be resolved before any CLR operations.
_RUNTIMECONFIG = Path(__file__).resolve().parents[2] / "genetec_sdk.runtimeconfig.json"


def _configure_runtime() -> None:
    """Configure pythonnet to use .NET 8.0 coreclr runtime.

    This must be called before any ``import clr`` statement.
    """
    global _runtime_configured
    if _runtime_configured:
        return

    from clr_loader import get_coreclr
    from pythonnet import set_runtime

    if not _RUNTIMECONFIG.exists():
        raise FileNotFoundError(
            f"Runtime config not found at: {_RUNTIMECONFIG}"
        )

    runtime = get_coreclr(runtime_config=str(_RUNTIMECONFIG))
    set_runtime(runtime)
    _runtime_configured = True


def _add_native_dll_paths(sdk_path: str) -> None:
    """Add native library search paths for 64-bit dependencies.

    The SDK ships native DLLs (FFmpeg, DirectShow, etc.) in architecture-
    specific subdirectories. Python needs to find these at runtime.
    """
    for subdir in ("x64", "amd64"):
        native_path = os.path.join(sdk_path, subdir)
        if os.path.isdir(native_path):
            os.add_dll_directory(native_path)
            os.environ["PATH"] = native_path + ";" + os.environ.get("PATH", "")


def _register_assembly_resolver(sdk_path: str) -> None:
    """Register a custom assembly resolver for the Genetec SDK.

    The SDK has 150+ transitive dependencies (Autofac, AutoMapper,
    Castle.Core, CoreWCF, etc.) that must be resolved from the SDK
    directory at runtime.
    """
    import System
    from System.Reflection import Assembly

    def resolve_handler(sender, args):
        assembly_name = args.Name.split(",")[0]
        dll_path = os.path.join(sdk_path, f"{assembly_name}.dll")
        if os.path.exists(dll_path):
            return Assembly.LoadFrom(dll_path)
        return None

    System.AppDomain.CurrentDomain.AssemblyResolve += resolve_handler


def _set_configuration_path() -> None:
    """Set the Genetec configuration folder override via AppDomain data.

    The SDK's Engine constructor reads configuration from a folder
    identified by the AppDomain key ``GENETEC_GCONFIG_PATH_5_13``.
    On machines without a full Security Center installation, this key
    is not set and the constructor fails. We set it directly before
    loading the SDK assembly so the static initializer finds it.
    """
    import System

    config_path = CONFIG_PATH
    os.makedirs(os.path.join(config_path, "ConfigurationFiles"), exist_ok=True)

    # Set the AppDomain data key directly. The key format is
    # GENETEC_GCONFIG_PATH_{major}_{minor} as determined by
    # ConfigurationManager.GetConfigurationPathOverrideAppDomainKey().
    System.AppDomain.CurrentDomain.SetData(
        "GENETEC_GCONFIG_PATH_5_13", config_path
    )


def load_sdk() -> None:
    """Load the Genetec SDK assemblies.

    Configures the .NET 8.0 coreclr runtime, sets up assembly resolution,
    and loads the core Genetec.Sdk.dll assembly.

    Raises:
        FileNotFoundError: If the SDK path, core DLL, or runtimeconfig is missing.
        RuntimeError: If the SDK assembly fails to load.
    """
    global _sdk_loaded
    if _sdk_loaded:
        return

    validate_sdk_path()
    sdk_path = SDK_PATH

    # Step 1: Configure .NET 8.0 runtime (must happen before import clr)
    _configure_runtime()

    import clr  # noqa: E402

    # Step 2: Add SDK to assembly search path
    sys.path.append(sdk_path)

    # Step 3: Add native DLL search paths
    _add_native_dll_paths(sdk_path)

    # Step 4: Register resolver for transitive dependencies
    _register_assembly_resolver(sdk_path)

    # Step 5: Set Genetec configuration path override so Engine() can
    # find its .gconfig files. Without this, the constructor fails with
    # "The path is empty" from ConfigurationManager.
    _set_configuration_path()

    # Step 6: Load core SDK assembly
    try:
        clr.AddReference("Genetec.Sdk")
    except Exception as e:
        raise RuntimeError(
            f"Failed to load Genetec.Sdk.dll from {sdk_path}: {e}"
        ) from e

    _sdk_loaded = True


def get_sdk_version() -> str:
    """Return the loaded Genetec SDK assembly version.

    Returns:
        Version string of the loaded Genetec.Sdk assembly.

    Raises:
        RuntimeError: If SDK is not loaded yet.
    """
    if not _sdk_loaded:
        raise RuntimeError("SDK not loaded. Call load_sdk() first.")

    import System

    for asm in System.AppDomain.CurrentDomain.GetAssemblies():
        name = asm.GetName()
        if name.Name == "Genetec.Sdk":
            return str(name.Version)

    raise RuntimeError("Genetec.Sdk assembly not found in loaded assemblies.")
