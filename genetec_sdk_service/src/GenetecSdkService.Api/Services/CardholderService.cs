using Genetec.Sdk;
using GenetecSdkService.Api.Models;

namespace GenetecSdkService.Api.Services;

/// <summary>
/// Service for cardholder operations against the Genetec SDK.
/// </summary>
public class CardholderService
{
    private readonly GenetecEngineService _engineService;

    public CardholderService(GenetecEngineService engineService)
    {
        _engineService = engineService;
    }

    public CardholderResponse CreateCardholder(CardholderRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.FirstName))
            throw new ArgumentException("firstName is required and cannot be empty.");
        if (string.IsNullOrWhiteSpace(request.LastName))
            throw new ArgumentException("lastName is required and cannot be empty.");
        if (!_engineService.IsConnected)
            throw new InvalidOperationException("Not connected to Security Center.");

        var engine = _engineService.Engine;
        var entityName = $"{request.FirstName} {request.LastName}";
        var cardholder = engine.CreateEntity(entityName, EntityType.Cardholder);

        cardholder.FirstName = request.FirstName;
        cardholder.LastName = request.LastName;

        if (!string.IsNullOrEmpty(request.Email))
            cardholder.EmailAddress = request.Email;
        if (!string.IsNullOrEmpty(request.MobilePhone))
            cardholder.MobilePhoneNumber = request.MobilePhone;

        return new CardholderResponse { Guid = cardholder.Guid.ToString() };
    }
}
