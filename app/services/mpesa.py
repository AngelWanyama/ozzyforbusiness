import json
import base64
from datetime import datetime
import requests
from app.core.config import settings

class MpesaService:
    def __init__(self):
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', None)
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', None)
        self.shortcode = getattr(settings, 'MPESA_SHORTCODE', '174379')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
        self.base_url = "https://sandbox.safaricom.co.ke"

    def _get_access_token(self):
        if not self.consumer_key or not self.consumer_secret:
            return "mock_token"
        
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(url, auth=(self.consumer_key, self.consumer_secret))
        return response.json().get('access_token')

    async def initiate_stk_push(self, phone_number: str, amount: int, callback_url: str):
        # In a real app, we'd call Safaricom API here
        # For now, we mock a successful initiation
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        
        # This is where the actual request would go
        print(f"Initiating STK Push to {phone_number} for {amount} {callback_url}")
        
        return {
            "MerchantRequestID": "mock_merchant_id",
            "CheckoutRequestID": "mock_checkout_id",
            "ResponseCode": "0",
            "CustomerMessage": "Success. Request accepted for processing"
        }

mpesa_service = MpesaService()
