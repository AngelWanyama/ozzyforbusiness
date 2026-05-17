import json
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
from app.schemas.nlp import NLPTransactionResponse
import google.generativeai as genai

class NLPParserService:
    def __init__(self):
        # Configure Gemini
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here":
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    async def parse_transaction(self, text: str) -> NLPTransactionResponse:
        """
        Parses raw text into a structured transaction object using LLM.
        """
        if not self.model:
            # Fallback logic if LLM is not configured
            return NLPTransactionResponse(**self._fallback_parse(text))

        prompt = f"""
        You are an AI assistant for 'Ozzy for Business', a mobile app for small business owners in Africa.
        Your task is to parse unstructured business entries into structured JSON.
        
        User Entry: "{text}"
        Current Date: {datetime.now().strftime('%Y-%m-%d')}
        
        Return a JSON object with the following fields:
        - intent: One of "sale", "expense", "inventory", or "query".
        - amount: Numeric value (integer or float).
        - item: Name of the product or service.
        - quantity: Number of units (default 1).
        - currency: Currency code (default "UGX").
        - transaction_date: ISO 8601 format (YYYY-MM-DD) (default to current date if not specified).
        - confidence: A score from 0 to 1 indicating your confidence in the parsing.

        Rules:
        1. If the entry is about money coming in, intent is "sale".
        2. If the entry is about money going out, intent is "expense".
        3. If the entry is about stock levels or adding stock, intent is "inventory".
        4. If the user asks a question about their data, intent is "query".
        5. For multi-word items, capture the full name (e.g., "blue dress").

        Only return the JSON. No preamble.
        """

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean up potential markdown code blocks
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()

            parsed_json = json.loads(result_text)
            return NLPTransactionResponse(**parsed_json)
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return NLPTransactionResponse(**self._fallback_parse(text))

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """
        Very basic fallback parsing logic using simple rules.
        """
        text = text.lower()
        intent = "sale"
        if "paid" in text or "bought" in text or "expense" in text or "rent" in text:
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
            "quantity": 1,
            "currency": "UGX",
            "transaction_date": datetime.now().strftime('%Y-%m-%d'),
            "confidence": 0.3
        }

nlp_parser = NLPParserService()
