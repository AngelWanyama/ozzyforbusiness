import requests
from app.core.config import settings

class FlutterwaveService:
    def __init__(self):
        self.secret_key = getattr(settings, 'FLUTTERWAVE_SECRET_KEY', None)
        self.base_url = "https://api.flutterwave.com/v3"

    async def create_payment_link(self, tx_ref: str, amount: float, currency: str, user_email: str, user_name: str):
        # In a real app, we'd call Flutterwave API here
        # For now, we mock a successful creation
        print(f"Creating Flutterwave payment link for {tx_ref} - {amount} {currency}")
        
        # Mock response
        return {
            "status": "success",
            "message": "Hosted link created",
            "data": {
                "link": f"https://checkout.flutterwave.com/v3/hosted/pay/mock_{tx_ref}"
            }
        }

    async def verify_transaction(self, transaction_id: str):
        # Mock verification
        return {
            "status": "success",
            "data": {
                "status": "successful",
                "tx_ref": "mock_tx_ref",
                "amount": 20000,
                "currency": "UGX"
            }
        }

flutterwave_service = FlutterwaveService()
