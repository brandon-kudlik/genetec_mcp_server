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
        var getBuilderMethod = entityManager.GetType().GetMethod("GetCredentialBuilder")
            ?? throw new InvalidOperationException("GetCredentialBuilder method not found on EntityManager.");
        var builderObj = getBuilderMethod.Invoke(entityManager, null)
            ?? throw new InvalidOperationException("GetCredentialBuilder returned null.");

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

    private static object CreateFormat(CredentialRequest request)
    {
        // Load credential format types from SDK assembly
        var sdkAssembly = typeof(EntityType).Assembly;

        var typeName = request.FormatType switch
        {
            "WiegandStandard26Bit" => "Genetec.Sdk.Credentials.WiegandStandardCredentialFormat",
            "WiegandH10306" => "Genetec.Sdk.Credentials.WiegandH10306CredentialFormat",
            "WiegandH10304" => "Genetec.Sdk.Credentials.WiegandH10304CredentialFormat",
            "WiegandH10302" => "Genetec.Sdk.Credentials.WiegandH10302CredentialFormat",
            "WiegandCsn32" => "Genetec.Sdk.Credentials.WiegandCsn32CredentialFormat",
            "WiegandCorporate1000" => "Genetec.Sdk.Credentials.WiegandCorporate1000CredentialFormat",
            "Wiegand48BitCorporate1000" => "Genetec.Sdk.Credentials.Wiegand48BitCorporate1000CredentialFormat",
            "Keypad" => "Genetec.Sdk.Credentials.KeypadCredentialFormat",
            "LicensePlate" => "Genetec.Sdk.Credentials.LicensePlateCredentialFormat",
            "RawCard" => "Genetec.Sdk.Credentials.RawCardCredentialFormat",
            _ => throw new ArgumentException($"Unknown formatType '{request.FormatType}'.")
        };

        var formatType = sdkAssembly.GetType(typeName)
            ?? throw new InvalidOperationException($"SDK type '{typeName}' not found in assembly.");

        object[] args = request.FormatType switch
        {
            "WiegandH10302" or "WiegandCsn32" => new object[] { request.CardId ?? 0 },
            "Keypad" => new object[] { request.Code ?? 0 },
            "LicensePlate" => new object[] { request.LicensePlate ?? "" },
            "RawCard" => new object[] { request.RawData ?? "", request.BitLength ?? 0 },
            _ => new object[] { request.Facility ?? 0, request.CardId ?? 0 }
        };

        return Activator.CreateInstance(formatType, args)
            ?? throw new InvalidOperationException($"Failed to create instance of '{typeName}'.");
    }
}
