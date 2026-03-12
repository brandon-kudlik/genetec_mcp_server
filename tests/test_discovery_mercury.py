"""SDK API discovery for Mercury sub-controller enrollment.

Run this against a live Security Center to discover the correct SDK API
for adding Mercury EP/LP sub-controllers to Cloudlink units.

Usage:
    uv run python -m pytest tests/test_discovery_mercury.py -v -s
"""

import pytest

from genetec_mcp_server.connection import GenetecConnection


@pytest.fixture(scope="module")
def connected():
    """Provide a connected GenetecConnection for discovery tests."""
    conn = GenetecConnection()
    result = conn.connect()
    if result != "Success":
        pytest.skip(f"Cannot connect to Security Center: {result} ({conn.last_failure})")
    yield conn
    conn.dispose()


class TestDiscoverAccessControlUnitManagerMethods:
    """Step 1.1: Reflect on AccessControlUnitManager methods."""

    def test_list_all_methods(self, connected):
        """List all public methods on AccessControlUnitManager."""
        mgr = connected.engine.AccessControlUnitManager
        methods = mgr.GetType().GetMethods()
        print("\n=== AccessControlUnitManager Methods ===")
        for m in methods:
            params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in m.GetParameters())
            print(f"  {m.ReturnType.Name} {m.Name}({params})")

    def test_filter_relevant_methods(self, connected):
        """Filter methods related to adding interfaces/modules/peripherals."""
        mgr = connected.engine.AccessControlUnitManager
        methods = mgr.GetType().GetMethods()
        keywords = ["AddInterface", "AddModule", "Enroll", "Discover", "AddPeripheral", "AddChild", "Mercury", "Interface"]
        print("\n=== Filtered Methods (keywords: AddInterface, AddModule, Enroll, Discover, AddPeripheral, AddChild, Mercury, Interface) ===")
        for m in methods:
            if any(kw.lower() in m.Name.lower() for kw in keywords):
                params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in m.GetParameters())
                print(f"  {m.ReturnType.Name} {m.Name}({params})")


class TestDiscoverRelevantTypes:
    """Step 1.2: Scan assemblies for relevant types."""

    def test_scan_for_mercury_and_interface_types(self, connected):
        """Search all loaded assemblies for types related to Mercury/InterfaceModule."""
        import System

        keywords = ["InterfaceModule", "Mercury", "Peripheral", "SubController", "AddInterface"]
        print("\n=== Types matching keywords ===")
        for asm in System.AppDomain.CurrentDomain.GetAssemblies():
            try:
                for t in asm.GetTypes():
                    if any(kw.lower() in t.Name.lower() for kw in keywords):
                        print(f"\n  Type: {t.FullName} (Assembly: {asm.GetName().Name})")
                        # Constructors
                        for ctor in t.GetConstructors():
                            params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in ctor.GetParameters())
                            print(f"    Constructor({params})")
                        # Properties
                        for prop in t.GetProperties():
                            print(f"    Property: {prop.PropertyType.Name} {prop.Name}")
                        # Methods (non-inherited)
                        import System.Reflection
                        for m in t.GetMethods(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.DeclaredOnly):
                            params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in m.GetParameters())
                            print(f"    Method: {m.ReturnType.Name} {m.Name}({params})")
            except Exception:
                pass


class TestDiscoverAccessControlExtensionType:
    """Step 1.3: Enumerate AccessControlExtensionType enum values."""

    def test_list_enum_values(self, connected):
        """List all AccessControlExtensionType enum values."""
        import System

        AccessControlExtensionType = connected._import_type("AccessControlExtensionType")
        values = System.Enum.GetValues(AccessControlExtensionType)
        print("\n=== AccessControlExtensionType Enum Values ===")
        for v in values:
            print(f"  {v} = {int(v)}")


class TestDiscoverCloudlinkHierarchy:
    """Step 1.4: Inspect existing Cloudlink unit hierarchy."""

    def test_inspect_access_control_units(self, connected):
        """Query AccessControlUnit entities and inspect their hierarchy."""
        from Genetec.Sdk import EntityType, ReportType

        query = connected.engine.ReportManager.CreateReportQuery(
            ReportType.EntityConfiguration
        )
        query.EntityTypeFilter.Add(EntityType.AccessControlUnit)
        results = query.Query()

        import System

        print("\n=== Access Control Units ===")
        for row in results.Data.Rows:
            guid = System.Guid(str(row["Guid"]))
            entity = connected.engine.GetEntity(guid)
            if entity is not None:
                print(f"\n  Unit: {entity.Name} (GUID: {entity.Guid})")
                print(f"    Type: {entity.GetType().FullName}")
                # Inspect properties
                for prop in entity.GetType().GetProperties():
                    try:
                        val = prop.GetValue(entity)
                        if val is not None and "interface" in prop.Name.lower() or "module" in prop.Name.lower() or "child" in prop.Name.lower():
                            print(f"    {prop.Name} = {val}")
                    except Exception:
                        pass


class TestDiscoverEvents:
    """Step 1.5: Check events on AccessControlUnitManager."""

    def test_list_events(self, connected):
        """List all events on AccessControlUnitManager."""
        mgr = connected.engine.AccessControlUnitManager
        events = mgr.GetType().GetEvents()
        print("\n=== AccessControlUnitManager Events ===")
        for ev in events:
            print(f"  {ev.EventHandlerType.Name} {ev.Name}")
