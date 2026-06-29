import httpx
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from app.core.config import settings
from decimal import Decimal

class CurrencyService:
    def __init__(self):
        self.api_key = getattr(settings, "EXCHANGERATE_API_KEY", None)
        self.base_url = f"https://v6.exchangerate-api.com/v6/{self.api_key}/latest"
        self.rates_cache = {}
        self.last_update = None

    async def get_rates(self, base_currency: str = "USD") -> Dict[str, float]:
        """
        Fetches exchange rates from the API. Uses cache if available (1 hour).
        """
        if self.rates_cache.get(base_currency) and self.last_update and (datetime.now() - self.last_update).total_seconds() < 3600:
             return self.rates_cache[base_currency]
             
        if not self.api_key or self.api_key == "your_api_key_here":
            # Fallback mock rates
            mock_rates = {
                "UGX": 3800.0,
                "KES": 130.0,
                "TZS": 2500.0,
                "RWF": 1200.0,
                "USD": 1.0,
                "EUR": 0.92,
                "GBP": 0.79,
                "ZAR": 18.5,
                "CNY": 7.2
            }
            if base_currency != "USD" and base_currency in mock_rates:
                base_val = mock_rates[base_currency]
                return {k: v / base_val for k, v in mock_rates.items()}
            return mock_rates

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/{base_currency}")
                if response.status_code == 200:
                    data = response.json()
                    if data["result"] == "success":
                        rates = data["conversion_rates"]
                        self.rates_cache[base_currency] = rates
                        self.last_update = datetime.now()
                        return rates
        except Exception as e:
            print(f"Error fetching exchange rates: {e}")
            
        return self.rates_cache.get(base_currency, {})

    async def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Tuple[Decimal, Decimal]:
        """
        Converts amount from one currency to another.
        Returns (converted_amount, exchange_rate)
        """
        if from_currency == to_currency:
            return amount, Decimal("1.0")
            
        rates = await self.get_rates(from_currency)
        if rates and to_currency in rates:
            rate = Decimal(str(rates[to_currency]))
            return (amount * rate).quantize(Decimal("0.01")), rate
        
        # Fallback if from_currency not available as base in free tier
        rates_usd = await self.get_rates("USD")
        if from_currency in rates_usd and to_currency in rates_usd:
            # from -> USD -> to
            rate_from_to_usd = Decimal(str(rates_usd[from_currency]))
            rate_to_from_usd = Decimal(str(rates_usd[to_currency]))
            rate = rate_to_from_usd / rate_from_to_usd
            return (amount * rate).quantize(Decimal("0.01")), rate
            
        return amount, Decimal("1.0")

    def format_currency(self, amount: Decimal, currency_code: str = "UGX") -> str:
        """
        Formats amount with thousands separators.
        e.g., 200000 -> 200,000
        """
        if currency_code == "UGX":
            return "{:,.0f}".format(amount)
        return "{:,.2f}".format(amount)

currency_service = CurrencyService()
