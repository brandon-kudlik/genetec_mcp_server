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


class TestDebugBuilderExecution:
    """Debug the actual builder execution to understand failures."""

    def test_inspect_build_method(self, connected):
        """Inspect Build() return type and any error-related methods on the builder."""
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

        all_flags = (System.Reflection.BindingFlags.Public
                     | System.Reflection.BindingFlags.NonPublic
                     | System.Reflection.BindingFlags.Instance
                     | System.Reflection.BindingFlags.DeclaredOnly)

        print(f"\n=== ALL methods on {builder_type.Name} ===")
        for m in builder_type.GetMethods(all_flags):
            params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in m.GetParameters())
            print(f"  {m.ReturnType.Name} {m.Name}({params})")

        print(f"\n=== ALL properties on {builder_type.Name} ===")
        for p in builder_type.GetProperties(all_flags):
            print(f"  {p.PropertyType.Name} {p.Name}")

    def test_inspect_mercury_class_properties(self, connected):
        """Inspect all properties on a Mercury controller class."""
        import System
        import System.Reflection

        MercuryLP1502 = connected._import_type("MercuryLP1502")
        t = MercuryLP1502().GetType()

        print(f"\n=== {t.FullName} Properties ===")
        for p in t.GetProperties():
            print(f"  {p.PropertyType.Name} {p.Name}")

        print(f"\n=== {t.FullName} base type chain ===")
        current = t
        while current is not None:
            print(f"  {current.FullName}")
            current = current.BaseType

    def test_try_build_and_capture_exception(self, connected):
        """Attempt a real build with a known Cloudlink unit and capture any exception details."""
        import System
        from System.Net import IPAddress as NetIPAddress

        # Query for existing units to find a Cloudlink
        from Genetec.Sdk import EntityType, ReportType

        query = connected.engine.ReportManager.CreateReportQuery(
            ReportType.EntityConfiguration
        )
        query.EntityTypeFilter.Add(EntityType.Unit)
        results = query.Query()

        unit_guid = None
        for row in results.Data.Rows:
            guid = System.Guid(str(row["Guid"]))
            entity = connected.engine.GetEntity(guid)
            if entity is not None:
                print(f"\n  Found unit: {entity.Name} ({entity.Guid})")
                print(f"    Type: {entity.GetType().FullName}")
                unit_guid = entity.Guid
                break

        if unit_guid is None:
            pytest.skip("No units found to test with")

        MercuryLP1502 = connected._import_type("MercuryLP1502")
        AccessControlInterfacePeripheralsBuilder = connected._import_type(
            "AccessControlInterfacePeripheralsBuilder"
        )

        mercury = MercuryLP1502()
        mercury.IpAddress = NetIPAddress.Parse("192.168.1.50")
        mercury.Port = 3001
        mercury.Channel = 0

        print(f"\n  Mercury object type: {mercury.GetType().FullName}")
        print(f"  Mercury IpAddress: {mercury.IpAddress}")
        print(f"  Mercury Port: {mercury.Port}")
        print(f"  Mercury Channel: {mercury.Channel}")

        builder = AccessControlInterfacePeripheralsBuilder(
            connected.engine, unit_guid
        )
        print(f"\n  Builder type: {builder.GetType().FullName}")

        # Check if builder has any status/error properties before build
        for prop in builder.GetType().GetProperties():
            try:
                val = prop.GetValue(builder)
                print(f"  Builder.{prop.Name} = {val}")
            except Exception as ex:
                print(f"  Builder.{prop.Name} = <error: {ex}>")

        builder.AddAccessControlBusInterface("Test-Mercury-LP1502", mercury)

        # Check state after add
        print("\n  === After AddAccessControlBusInterface ===")
        for prop in builder.GetType().GetProperties():
            try:
                val = prop.GetValue(builder)
                print(f"  Builder.{prop.Name} = {val}")
            except Exception as ex:
                print(f"  Builder.{prop.Name} = <error: {ex}>")

        try:
            result = builder.Build()
            print(f"\n  Build() returned: {result} (type: {type(result)})")
            if result is not None:
                print(f"  Result type: {result.GetType().FullName}")
                for prop in result.GetType().GetProperties():
                    try:
                        val = prop.GetValue(result)
                        print(f"  Result.{prop.Name} = {val}")
                    except Exception as ex:
                        print(f"  Result.{prop.Name} = <error: {ex}>")
        except Exception as ex:
            print(f"\n  Build() raised: {type(ex).__name__}: {ex}")
            # Try to get inner exception details
            if hasattr(ex, 'InnerException') and ex.InnerException:
                print(f"  InnerException: {ex.InnerException}")

    def test_inspect_add_bus_interface_overloads(self, connected):
        """Check all overloads of AddAccessControlBusInterface."""
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
            pytest.skip("Builder type not found")

        all_flags = (System.Reflection.BindingFlags.Public
                     | System.Reflection.BindingFlags.NonPublic
                     | System.Reflection.BindingFlags.Instance)

        print("\n=== AddAccessControlBusInterface overloads ===")
        for m in builder_type.GetMethods(all_flags):
            if "AddAccessControl" in m.Name or "Add" in m.Name:
                params = ", ".join(
                    f"{p.ParameterType.FullName} {p.Name}" for p in m.GetParameters()
                )
                print(f"  {m.ReturnType.FullName} {m.Name}({params})")


class TestDiscoverEvents:
    """Step 1.5: Check events on AccessControlUnitManager."""

    def test_list_events(self, connected):
        """List all events on AccessControlUnitManager."""
        mgr = connected.engine.AccessControlUnitManager
        events = mgr.GetType().GetEvents()
        print("\n=== AccessControlUnitManager Events ===")
        for ev in events:
            print(f"  {ev.EventHandlerType.Name} {ev.Name}")
