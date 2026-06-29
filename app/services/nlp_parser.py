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

    async def parse_invoice(self, text: str) -> Dict[str, Any]:
        """
        Parses raw text into structured invoice data.
        """
        if not self.model:
             return self._fallback_invoice_parse(text)

        prompt = f"""
        You are an AI assistant for 'Ozzy for Business'.
        Your task is to parse an invoice creation request into structured JSON.
        
        User Entry: "{text}"
        Current Date: {datetime.now().strftime('%Y-%m-%d')}
        
        Return a JSON object with the following fields:
        - customer_name: Name of the customer.
        - items: A list of objects, each with:
            - description: Name of the item or service.
            - quantity: Number of units (default 1).
            - unit_price: Price per unit.
        - notes: Any additional notes (default null).
        - due_date: ISO 8601 format (YYYY-MM-DD) (default to 7 days from now if not specified).
        - currency: Currency code (default "UGX").

        Only return the JSON. No preamble.
        """

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()

            return json.loads(result_text)
        except Exception as e:
            print(f"Error calling LLM for invoice: {e}")
            return self._fallback_invoice_parse(text)

    def _fallback_invoice_parse(self, text: str) -> Dict[str, Any]:
        """
        Simple extraction for invoice creation text.
        """
        import re
        customer_name = "Walk-in Customer"
        items = []
        
        # Look for "for [Name]"
        name_match = re.search(r'for\s+([A-Z][a-z]+)', text)
        if name_match:
            customer_name = name_match.group(1)
            
        # Look for numbers
        numbers = re.findall(r'(\d[\d,.]*)', text)
        amount = 0
        if numbers:
            amount = float(numbers[-1].replace(',', ''))
            
        description = "Service/Product"
        # Try to find description between name and amount
        if name_match and numbers:
             start = name_match.end()
             end = text.find(numbers[-1])
             if end > start:
                 desc = text[start:end].strip(', ').strip()
                 if desc:
                     description = desc

        items.append({
            "description": description,
            "quantity": 1.0,
            "unit_price": amount
        })
        
        from datetime import timedelta
        due_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        return {
            "customer_name": customer_name,
            "items": items,
            "notes": None,
            "due_date": due_date,
            "currency": "UGX"
        }

    async def scan_receipt(self, image_data: bytes, content_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Uses Gemini Vision to extract data from a receipt image.
        """
        if not self.model:
            return {
                "vendor_name": "Unknown",
                "total_amount": 0.0,
                "currency": "UGX",
                "date": datetime.now().strftime('%Y-%m-%d'),
                "items": []
            }

        prompt = """
        You are an expert at reading business receipts. 
        Analyze the provided image and extract the following information into a JSON object:
        - vendor_name: The name of the store or business.
        - total_amount: The total amount paid.
        - currency: The currency code (e.g., UGX, KES, USD).
        - date: The date on the receipt (YYYY-MM-DD).
        - items: A list of line items, each with 'description', 'quantity', and 'price'.

        Only return the JSON. No preamble or markdown blocks.
        """

        try:
            # Prepare image part for Gemini
            image_part = {
                "mime_type": content_type,
                "data": image_data
            }
            
            response = self.model.generate_content([prompt, image_part])
            result_text = response.text.strip()
            
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()

            return json.loads(result_text)
        except Exception as e:
            print(f"Error scanning receipt with Gemini: {e}")
            return {
                "vendor_name": "Error",
                "total_amount": 0.0,
                "currency": "UGX",
                "date": datetime.now().strftime('%Y-%m-%d'),
                "items": [],
                "error": str(e)
            }

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """
        Basic fallback parsing logic using simple rules and common business lexicon.
        """
        text = text.lower()
        intent = "sale"
        
        # Intent Lexicon
        expense_keywords = ["paid", "bought", "expense", "rent", "bill", "salary", "salaries", "fuel", "transport", "delivery", "charcoal", "airtime", "data"]
        inventory_keywords = ["stock", "inventory", "added", "check"]
        query_keywords = ["?", "what", "show", "how much", "profit", "sales", "expenses"]
        
        if any(kw in text for kw in expense_keywords):
            intent = "expense"
        elif any(kw in text for kw in inventory_keywords):
            intent = "inventory"
        elif any(kw in text for kw in query_keywords):
            intent = "query"

        # Amount extraction with 'k' suffix support
        amount = 0
        import re
        
        # Handle 'k' suffix (e.g., 300k -> 300000)
        k_matches = re.findall(r'(\d+(?:\.\d+)?)\s*k\b', text)
        if k_matches:
            # Usually the last 'k' amount is the total
            amount = float(k_matches[-1]) * 1000
        else:
            # Fallback to standard numbers
            numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', text)
            if numbers:
                # Use the last number as amount for sales/expenses
                clean_num = numbers[-1].replace(',', '')
                amount = float(clean_num) if intent in ["sale", "expense"] else 0

        # Basic item extraction (first word that isn't a keyword or number)
        item = "unknown"
        words = text.split()
        for word in words:
            word_clean = re.sub(r'[^a-z]', '', word)
            if word_clean and word_clean not in expense_keywords and word_clean not in inventory_keywords and word_clean not in ["sold", "received", "for", "to", "now", "a", "the", "each"]:
                item = word_clean
                break

        # Quantity check (e.g. 3kg, 10eggs)
        quantity = 1.0
        qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|pcs|bags|crates|eggs|items|units|pairs)', text)
        if qty_match:
            quantity = float(qty_match.group(1))

        return {
            "intent": intent,
            "amount": amount,
            "item": item,
            "quantity": quantity,
            "currency": "UGX",
            "transaction_date": datetime.now().strftime('%Y-%m-%d'),
            "confidence": 0.3
        }

nlp_parser = NLPParserService()
