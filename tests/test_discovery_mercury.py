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

    def test_find_unit_entity_type(self, connected):
        """Find the correct EntityType for access control units."""
        import System

        EntityType = connected._import_type("EntityType")
        values = System.Enum.GetValues(EntityType)
        print("\n=== EntityType values containing 'unit' or 'access' ===")
        for v in values:
            name = str(v)
            if "unit" in name.lower() or "access" in name.lower():
                print(f"  {v} = {int(v)}")

    def test_inspect_access_control_units(self, connected):
        """Query Unit entities and inspect their hierarchy."""
        import System
        from Genetec.Sdk import EntityType, ReportType

        # Try 'Unit' instead of 'AccessControlUnit'
        query = connected.engine.ReportManager.CreateReportQuery(
            ReportType.EntityConfiguration
        )
        query.EntityTypeFilter.Add(EntityType.Unit)
        results = query.Query()

        print("\n=== Access Control Units ===")
        for row in results.Data.Rows:
            guid = System.Guid(str(row["Guid"]))
            entity = connected.engine.GetEntity(guid)
            if entity is not None:
                print(f"\n  Unit: {entity.Name} (GUID: {entity.Guid})")
                print(f"    Type: {entity.GetType().FullName}")
                # Look for InterfaceModules property
                for prop in entity.GetType().GetProperties():
                    name = prop.Name
                    if "interface" in name.lower() or "module" in name.lower() or "child" in name.lower() or "peripheral" in name.lower():
                        try:
                            val = prop.GetValue(entity)
                            print(f"    {name} = {val}")
                            # If it's a collection, enumerate it
                            if val is not None and hasattr(val, 'Count'):
                                print(f"      Count: {val.Count}")
                                for item in val:
                                    print(f"      Item: {item}")
                        except Exception as ex:
                            print(f"    {name} = <error: {ex}>")


class TestDiscoverBuilderAPI:
    """Step 2.1: Discover how to obtain and use AccessControlInterfacePeripheralsBuilder."""

    def test_builder_constructors(self, connected):
        """Inspect AccessControlInterfacePeripheralsBuilder constructors (including non-public)."""
        import System
        import System.Reflection

        builder_type = None
        for asm in System.AppDomain.CurrentDomain.GetAssemblies():
            try:
                for t in asm.GetTypes():
                    if t.Name == "AccessControlInterfacePeripheralsBuilder":
                        builder_type = t
                        break
            except Exception:
                pass
            if builder_type:
                break

        if not builder_type:
            pytest.skip("AccessControlInterfacePeripheralsBuilder type not found")

        print(f"\n=== {builder_type.FullName} ===")

        # All constructors including non-public
        all_flags = (System.Reflection.BindingFlags.Public
                     | System.Reflection.BindingFlags.NonPublic
                     | System.Reflection.BindingFlags.Instance)
        ctors = builder_type.GetConstructors(all_flags)
        print("\n  Constructors (including non-public):")
        for ctor in ctors:
            params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in ctor.GetParameters())
            print(f"    ({params})")

        # Static factory methods
        static_flags = (System.Reflection.BindingFlags.Public
                        | System.Reflection.BindingFlags.NonPublic
                        | System.Reflection.BindingFlags.Static)
        static_methods = builder_type.GetMethods(static_flags)
        print("\n  Static methods (including non-public):")
        for m in static_methods:
            params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in m.GetParameters())
            print(f"    {m.ReturnType.Name} {m.Name}({params})")

    def test_unit_entity_methods_for_builder(self, connected):
        """Check if Unit or AccessControlUnit entity has methods to create a builder."""
        import System
        from Genetec.Sdk import EntityType, ReportType

        query = connected.engine.ReportManager.CreateReportQuery(
            ReportType.EntityConfiguration
        )
        query.EntityTypeFilter.Add(EntityType.Unit)
        results = query.Query()

        for row in results.Data.Rows:
            guid = System.Guid(str(row["Guid"]))
            entity = connected.engine.GetEntity(guid)
            if entity is not None:
                entity_type = entity.GetType()
                print(f"\n=== Entity: {entity.Name} ({entity_type.FullName}) ===")

                # Look for methods that return builders or accept peripherals
                import System.Reflection
                all_flags = (System.Reflection.BindingFlags.Public
                             | System.Reflection.BindingFlags.Instance
                             | System.Reflection.BindingFlags.DeclaredOnly)
                for m in entity_type.GetMethods(all_flags):
                    name_lower = m.Name.lower()
                    if ("peripheral" in name_lower or "builder" in name_lower
                            or "interface" in name_lower or "module" in name_lower
                            or "mercury" in name_lower or "add" in name_lower):
                        params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in m.GetParameters())
                        print(f"  {m.ReturnType.Name} {m.Name}({params})")

                # Only check first unit to keep output manageable
                break

    def test_engine_methods_for_peripherals(self, connected):
        """Check Engine for methods related to peripherals or interface modules."""
        import System.Reflection

        engine_type = connected.engine.GetType()
        all_flags = (System.Reflection.BindingFlags.Public
                     | System.Reflection.BindingFlags.Instance)
        print("\n=== Engine methods related to peripherals/interface ===")
        for m in engine_type.GetMethods(all_flags):
            name_lower = m.Name.lower()
            if ("peripheral" in name_lower or "interfacemodule" in name_lower
                    or "builder" in name_lower):
                params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in m.GetParameters())
                print(f"  {m.ReturnType.Name} {m.Name}({params})")

    def test_peripherals_type_enum(self, connected):
        """List AccessControlInterfacePeripheralsType enum values."""
        import System

        try:
            t = connected._import_type("AccessControlInterfacePeripheralsType")
            values = System.Enum.GetValues(t)
            print("\n=== AccessControlInterfacePeripheralsType Enum Values ===")
            for v in values:
                print(f"  {v} = {int(v)}")
        except RuntimeError:
            print("\n  AccessControlInterfacePeripheralsType not found as importable type")

    def test_access_control_interface_type_enum(self, connected):
        """List AccessControlInterfaceType enum values (Mercury-related)."""
        import System

        try:
            t = connected._import_type("AccessControlInterfaceType")
            values = System.Enum.GetValues(t)
            print("\n=== AccessControlInterfaceType Enum Values (filtered) ===")
            for v in values:
                name = str(v)
                if "mercury" in name.lower() or "lp" in name.lower() or "ep" in name.lower() or "mp" in name.lower():
                    print(f"  {v} = {int(v)}")
        except RuntimeError:
            print("\n  AccessControlInterfaceType not found")


class TestDiscoverEvents:
    """Step 1.5: Check events on AccessControlUnitManager."""

    def test_list_events(self, connected):
        """List all events on AccessControlUnitManager."""
        mgr = connected.engine.AccessControlUnitManager
        events = mgr.GetType().GetEvents()
        print("\n=== AccessControlUnitManager Events ===")
        for ev in events:
            print(f"  {ev.EventHandlerType.Name} {ev.Name}")
