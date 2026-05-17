import requests
from app.core.config import settings

class AirtelUGService:
    def __init__(self):
        self.client_id = getattr(settings, 'AIRTEL_UG_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'AIRTEL_UG_CLIENT_SECRET', None)
        self.base_url = "https://openapiapi.airtel.com" # Production/Sandbox base

    async def initiate_payment(self, phone_number: str, amount: int, reference: str):
        # In a real app:
        # 1. Auth (POST /auth/oauth2/token)
        # 2. Push payment (POST /merchant/v1/payments/)
        
        print(f"Initiating Airtel Uganda payment for {phone_number} - {amount} UGX")
        
        # Mocking the response
        return {
            "status": "pending",
            "transaction_id": "airtel_mock_tx_123",
            "message": "Airtel Money payment requested."
        }

airtel_ug_service = AirtelUGService()
