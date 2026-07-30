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
        Parses raw text into structured invoice data using LLM.
        """
        if not self.model:
             return self._fallback_invoice_parse(text)

        prompt = f"""
        You are an AI assistant for 'Ozzy for Business'.
        Your task is to parse an invoice creation request into structured JSON.
        
        User Entry: "{text}"
        Current Date: {datetime.now().strftime('%Y-%m-%d')}
        
        Return a JSON object with the following fields:
        - customer_name: Name of the customer (required).
        - customer_company: Company name of the customer if mentioned.
        - customer_phone: Phone number of the customer if mentioned.
        - customer_email: Email address of the customer if mentioned.
        - customer_address: Physical address of the customer if mentioned.
        - items: A list of objects, each with:
            - name: Name of the item or service (required).
            - description: Brief description if any.
            - quantity: Number of units (default 1).
            - unit_price: Price per unit.
            - discount_pct: Discount percentage for this item (default 0).
            - tax_pct: Tax percentage for this item (default 0).
        - payment_method: An object with 'type' (e.g., "Mobile Money", "Cash", "Bank Transfer") and 'instructions'.
        - notes: Any additional notes.
        - due_date: ISO 8601 format (YYYY-MM-DD) (default to 7 days from now if not specified).
        - currency: Currency code (default "UGX").

        Rules:
        1. Parse currency amounts with local format support (e.g., "120,000" and "120000" are both 120000).
        2. If the user mentions "each" or "@", use that as the unit_price.
        3. If no customer name is found, use "Walk-in Customer".

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
        Simple extraction for invoice creation text when LLM is unavailable.
        """
        import re
        customer_name = "Walk-in Customer"
        customer_company = None
        items = []
        payment_method = {"type": "Cash", "instructions": "Pay on delivery"}
        
        # Look for customer name after "for "
        name_match = re.search(r'for\s+([A-Z][a-zA-Z\s]+?)(?:\.|\s+at|\s+,|\s+with|$)', text)
        if name_match:
            customer_name = name_match.group(1).strip()
            
        # Basic check for common payment methods
        if re.search(r'mobile\s+money|m-pesa|mtn|airtel', text.lower()):
            payment_method = {"type": "Mobile Money", "instructions": "Pay to business number"}
        elif re.search(r'bank|transfer', text.lower()):
            payment_method = {"type": "Bank Transfer", "instructions": "See bank details below"}

        # Attempt to split into items if multiple sentences or commas
        parts = re.split(r'\.|\n|,', text)
        for part in parts:
            part = part.strip()
            if not part or any(kw in part.lower() for kw in ["invoice", "create", "for"]):
                continue
                
            # Extract number and possible "each"
            numbers = re.findall(r'(\d[\d,.]*)', part)
            if not numbers:
                continue
                
            qty = 1.0
            price = 0.0
            
            if len(numbers) >= 2:
                # Often "qty [item] price each"
                qty_match = re.search(r'(\d[\d,.]*)\s*(?:bags|litres|kg|items|units|pcs|dresses)', part.lower())
                if qty_match:
                    qty = float(qty_match.group(1).replace(',', ''))
                    # Price is likely the other number
                    other_nums = [n for n in numbers if n != qty_match.group(1)]
                    if other_nums:
                        price = float(other_nums[0].replace(',', ''))
                else:
                    qty = float(numbers[0].replace(',', ''))
                    price = float(numbers[1].replace(',', ''))
            elif len(numbers) == 1:
                price = float(numbers[0].replace(',', ''))
                
            # Description is words that aren't numbers
            name = re.sub(r'\d[\d,.]*|each|at|tax|%', '', part).strip()
            if not name:
                name = "Item"
                
            items.append({
                "name": name,
                "description": part,
                "quantity": qty,
                "unit_price": price,
                "discount_pct": 0,
                "tax_pct": 18 if "tax" in part.lower() else 0
            })

        if not items:
            items.append({
                "name": "General Service/Product",
                "quantity": 1.0,
                "unit_price": 0.0
            })
        
        from datetime import timedelta
        due_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        return {
            "customer_name": customer_name,
            "customer_company": customer_company,
            "items": items,
            "payment_method": payment_method,
            "notes": None,
            "due_date": due_date,
            "currency": "UGX"
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
