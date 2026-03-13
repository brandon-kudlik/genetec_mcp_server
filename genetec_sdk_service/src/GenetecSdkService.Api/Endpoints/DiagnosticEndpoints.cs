using System.Reflection;
using GenetecSdkService.Api.Models;
using GenetecSdkService.Api.Services;

namespace GenetecSdkService.Api.Endpoints;

public static class DiagnosticEndpoints
{
    public static void MapDiagnosticEndpoints(this WebApplication app)
    {
        app.MapGet("/api/diagnostics/sdk-introspection", (GenetecEngineService engineService) =>
        {
            try
            {
                var result = new DiagnosticResult();

                // Scan all loaded assemblies for relevant types
                var assemblies = AppDomain.CurrentDomain.GetAssemblies();

                foreach (var asm in assemblies)
                {
                    Type[] types;
                    try
                    {
                        types = asm.GetTypes();
                    }
                    catch (ReflectionTypeLoadException)
                    {
                        continue;
                    }

                    foreach (var t in types)
                    {
                        var fullName = t.FullName ?? t.Name;

                        // AccessControlUnitManager methods
                        if (t.Name == "AccessControlUnitManager" || t.Name == "IAccessControlUnitManager")
                        {
                            var methods = t.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                                .Select(m => $"{m.ReturnType.Name} {m.Name}({string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"))})");
                            result.AccessControlUnitManagerMethods.Add(fullName, methods.ToList());
                        }

                        // EntityManager builder methods
                        if (t.Name == "EntityManager" || t.Name == "IEntityManager")
                        {
                            var builderMethods = t.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                                .Where(m => m.Name.Contains("Builder") || m.Name.Contains("Get") && m.Name.Contains("Builder"))
                                .Select(m => $"{m.ReturnType.Name} {m.Name}({string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"))})");
                            result.EntityManagerBuilderMethods.Add(fullName, builderMethods.ToList());
                        }

                        // AccessControlInterfacePeripheralsBuilder details
                        if (t.Name == "AccessControlInterfacePeripheralsBuilder"
                            && !result.BuilderDetails.ContainsKey($"{fullName}:constructors"))
                        {
                            var ctors = t.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                                .Select(c => $"({string.Join(", ", c.GetParameters().Select(p => $"{p.ParameterType.FullName} {p.Name}"))})");
                            var methods = t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static)
                                .Where(m => !m.IsSpecialName) // skip property getters/setters
                                .Select(m => $"{(m.IsStatic ? "static " : "")}{m.ReturnType.Name} {m.Name}({string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"))})");
                            var properties = t.GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                                .Select(p => $"{p.PropertyType.Name} {p.Name} {{ {(p.CanRead ? "get; " : "")}{(p.CanWrite ? "set; " : "")}}}");

                            result.BuilderDetails[$"{fullName}:constructors"] = ctors.ToList();
                            result.BuilderDetails[$"{fullName}:methods"] = methods.ToList();
                            result.BuilderDetails[$"{fullName}:properties"] = properties.ToList();
                            result.BuilderDetails[$"{fullName}:baseType"] = new List<string> { t.BaseType?.FullName ?? "none" };
                        }

                        // Unit entity methods related to peripherals/interface modules
                        if (t.Name == "Unit" && t.Namespace?.Contains("Genetec") == true
                            && !result.UnitEntityInfo.ContainsKey($"{fullName}:methods"))
                        {
                            var methods = t.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                                .Select(m => $"{m.ReturnType.Name} {m.Name}({string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"))})");
                            var properties = t.GetProperties(BindingFlags.Public | BindingFlags.Instance)
                                .Select(p => $"{p.PropertyType.Name} {p.Name}");
                            result.UnitEntityInfo[$"{fullName}:methods"] = methods.ToList();
                            result.UnitEntityInfo[$"{fullName}:properties"] = properties.ToList();
                        }

                        // Scan for types containing relevant keywords
                        if (fullName.Contains("Peripheral") ||
                            fullName.Contains("InterfaceBuilder") ||
                            fullName.Contains("BusInterface") ||
                            (fullName.Contains("Mercury") && t.Namespace?.Contains("Genetec") == true))
                        {
                            result.RelevantTypes.Add(fullName);
                        }
                    }
                }

                // Also inspect the engine's AccessControlUnitManager at runtime via dynamic
                if (engineService.IsConnected)
                {
                    try
                    {
                        dynamic engine = engineService.Engine;
                        dynamic mgr = engine.AccessControlUnitManager;
                        var mgrType = ((object)mgr).GetType();
                        var methods = mgrType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                            .Cast<MethodInfo>()
                            .Select(m => $"{m.ReturnType.Name} {m.Name}({string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"))})");
                        result.RuntimeManagerMethods = methods.ToList();
                    }
                    catch (Exception ex)
                    {
                        result.RuntimeManagerMethods = new List<string> { $"Error: {ex.Message}" };
                    }
                }

                return Results.Ok(ApiResponse<DiagnosticResult>.Ok(result));
            }
            catch (Exception ex)
            {
                return Results.Ok(ApiResponse<DiagnosticResult>.Fail(ex.Message));
            }
        });
    }
}
