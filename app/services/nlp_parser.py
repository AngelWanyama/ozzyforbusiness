import json
from typing import Dict, Any, Optional
from datetime import datetime
from app.schemas.nlp import NLPTransactionResponse
from app.services.ai_client import ai_client

class NLPParserService:
    async def parse_transaction(self, text: str, user_currency: str = "UGX") -> NLPTransactionResponse:
        """
        Parses raw text into a structured transaction object using LLM.
        user_currency: the logged-in user's preferred currency, used as the default
        when no currency is mentioned in the text itself.
        """
        if not ai_client.is_available:
            # Fallback logic if LLM is not configured
            return NLPTransactionResponse(**self._fallback_parse(text, user_currency))

        prompt = f"""
        You are an AI assistant for 'Ozzy for Business', a mobile app for small business owners in Africa.
        Your task is to parse unstructured business entries into structured JSON.
        
        User Entry: "{text}"
        Current Date: {datetime.now().strftime('%Y-%m-%d')}
        User's Default Currency: {user_currency}
        
        Return a JSON object with the following fields:
        - intent: One of "sale", "expense", "inventory", or "query".
        - amount: Numeric value (integer or float).
        - item: Name of the product or service. For non-physical expenses (like utilities), use the specific thing paid for (e.g., "electricity", "water", "internet").
        - category: One of "Sales Revenue", "Utilities", "Transport", "Rent", "Supplies", "Salaries", "Marketing", "Equipment", "Other". Choose the closest match even if not explicitly stated.
        - quantity: Number of units (default 1).
        - currency: Currency code. Only override the User's Default Currency if the text explicitly mentions a different one (e.g., "dollars" or "USD").
        - transaction_date: ISO 8601 format (YYYY-MM-DD) (default to current date if not specified).
        - confidence: A score from 0 to 1 indicating your confidence in the parsing.

        Rules:
        1. If the entry is about money coming in, intent is "sale", category is "Sales Revenue".
        2. If the entry is about money going out, intent is "expense". Assign the most fitting category:
           - Electricity, water, internet, phone bills -> "Utilities"
           - Fuel, boda-boda, taxi, delivery costs -> "Transport"
           - Shop or office rent -> "Rent"
           - Raw materials, stock, packaging -> "Supplies"
           - Staff wages/payments -> "Salaries"
           - Ads, promotions -> "Marketing"
           - Tools, machinery, furniture -> "Equipment"
           - Anything else -> "Other"
        3. If the entry is about stock levels or adding stock, intent is "inventory".
        4. If the user asks a question about their data, intent is "query".
        5. For multi-word items, capture the full name (e.g., "blue dress").
        6. Airtime and mobile money float work like any other product the owner resells — judge the
           direction of money, not just the word "airtime": if the owner BOUGHT, topped up, or
           restocked airtime/float (money going OUT to the network), intent is "expense", category
           "Supplies". If the owner SOLD airtime to a customer (money coming IN), intent is "sale".
           When an entry mentions both (e.g. buying stock to then sell it), classify by whichever verb
           describes what actually happened in this entry, not the general nature of the business.

        Examples:
        User Entry: "paid 20000 for water"
        Output: {{"intent": "expense", "amount": 20000, "item": "water", "category": "Utilities", "quantity": 1, "currency": "{user_currency}", "transaction_date": "{datetime.now().strftime('%Y-%m-%d')}", "confidence": 0.9}}

        User Entry: "sold 3 bags of sugar for 15000"
        Output: {{"intent": "sale", "amount": 15000, "item": "sugar", "category": "Sales Revenue", "quantity": 3, "currency": "{user_currency}", "transaction_date": "{datetime.now().strftime('%Y-%m-%d')}", "confidence": 0.9}}

        User Entry: "bought airtime 50000"
        Output: {{"intent": "expense", "amount": 50000, "item": "airtime", "category": "Supplies", "quantity": 1, "currency": "{user_currency}", "transaction_date": "{datetime.now().strftime('%Y-%m-%d')}", "confidence": 0.9}}

        User Entry: "sold airtime 2000"
        Output: {{"intent": "sale", "amount": 2000, "item": "airtime", "category": "Sales Revenue", "quantity": 1, "currency": "{user_currency}", "transaction_date": "{datetime.now().strftime('%Y-%m-%d')}", "confidence": 0.9}}

        Only return the JSON. No preamble.
        """

        result_text = ai_client.generate(prompt, json_mode=True)
        if result_text is None:
            return NLPTransactionResponse(**self._fallback_parse(text, user_currency))

        try:
            # Clean up potential markdown code blocks
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()

            parsed_json = json.loads(result_text)
            return NLPTransactionResponse(**parsed_json)
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return NLPTransactionResponse(**self._fallback_parse(text, user_currency))

    def _fallback_parse(self, text: str, user_currency: str = "UGX") -> Dict[str, Any]:
        """
        Very basic fallback parsing logic using simple rules.
        """
        text = text.lower()
        intent = "sale"
        if "paid" in text or "bought" in text or "expense" in text or "rent" in text or "topped up" in text or "top up" in text or "restock" in text:
            intent = "expense"
        elif "stock" in text or "inventory" in text:
            intent = "inventory"
        elif "?" in text or "what" in text or "show" in text:
            intent = "query"

        # Try to find a number
        amount = 0
        import re
        numbers = re.findall(r'\d+', text.replace(',', ''))
        if numbers:
            amount = float(numbers[-1]) if intent == "sale" or intent == "expense" else 0
            if len(numbers) > 1 and intent == "sale":
                # Maybe first number is quantity
                pass 

        return {
            "intent": intent,
            "amount": amount,
            "item": "unknown",
            "category": "Other",
            "quantity": 1,
            "currency": user_currency,
            "transaction_date": datetime.now().strftime('%Y-%m-%d'),
            "confidence": 0.3
        }

nlp_parser = NLPParserService()