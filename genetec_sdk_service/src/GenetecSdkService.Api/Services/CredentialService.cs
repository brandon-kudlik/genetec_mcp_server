using Genetec.Sdk;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

public class CredentialService
{
    private readonly GenetecEngineService _engineService;

    public CredentialService(GenetecEngineService engineService)
    {
        _engineService = engineService;
    }

    public CredentialResponse CreateCredential(CredentialRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Name))
            throw new ArgumentException("name is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.FormatType))
            throw new ArgumentException("formatType is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;

        // Create the credential format based on formatType
        dynamic credentialFormat = CreateFormat(request);

        // Get the credential builder via reflection (SDK builder/manager pattern)
        var entityManager = engine.EntityManager;
        var builderObj = entityManager.GetType()
            .GetMethod("GetCredentialBuilder")
            .Invoke(entityManager, null);

        // Use dynamic to call builder methods
        dynamic builder = builderObj;
        builder.SetName(request.Name);
        builder.SetFormat(credentialFormat);

        dynamic credential = builder.Build();
        string credentialGuid = credential.Guid.ToString();

        // Assign to cardholder if specified
        if (!string.IsNullOrEmpty(request.CardholderGuid))
        {
            var cardholderGuid = new Guid(request.CardholderGuid);
            dynamic cardholder = engine.GetEntity(cardholderGuid);
            if (cardholder != null)
            {
                cardholder.Credentials.Add(credential.Guid);
            }
        }

        return new CredentialResponse { Guid = credentialGuid };
    }

    private object CreateFormat(CredentialRequest request)
    {
        // Load credential format types from SDK assembly
        var sdkAssembly = typeof(EntityType).Assembly;

        switch (request.FormatType)
        {
            case "WiegandStandard26Bit":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.WiegandStandardCredentialFormat");
                return Activator.CreateInstance(formatType, request.Facility ?? 0, request.CardId ?? 0);
            }
            case "WiegandH10306":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.WiegandH10306CredentialFormat");
                return Activator.CreateInstance(formatType, request.Facility ?? 0, request.CardId ?? 0);
            }
            case "WiegandH10304":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.WiegandH10304CredentialFormat");
                return Activator.CreateInstance(formatType, request.Facility ?? 0, request.CardId ?? 0);
            }
            case "WiegandH10302":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.WiegandH10302CredentialFormat");
                return Activator.CreateInstance(formatType, request.CardId ?? 0);
            }
            case "WiegandCsn32":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.WiegandCsn32CredentialFormat");
                return Activator.CreateInstance(formatType, request.CardId ?? 0);
            }
            case "WiegandCorporate1000":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.WiegandCorporate1000CredentialFormat");
                return Activator.CreateInstance(formatType, request.Facility ?? 0, request.CardId ?? 0);
            }
            case "Wiegand48BitCorporate1000":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.Wiegand48BitCorporate1000CredentialFormat");
                return Activator.CreateInstance(formatType, request.Facility ?? 0, request.CardId ?? 0);
            }
            case "Keypad":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.KeypadCredentialFormat");
                return Activator.CreateInstance(formatType, request.Code ?? 0);
            }
            case "LicensePlate":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.LicensePlateCredentialFormat");
                return Activator.CreateInstance(formatType, request.LicensePlate ?? "");
            }
            case "RawCard":
            {
                var formatType = sdkAssembly.GetType("Genetec.Sdk.Credentials.RawCardCredentialFormat");
                return Activator.CreateInstance(formatType, request.RawData ?? "", request.BitLength ?? 0);
            }
            default:
                throw new ArgumentException($"Unknown formatType '{request.FormatType}'.");
        }
    }
}
