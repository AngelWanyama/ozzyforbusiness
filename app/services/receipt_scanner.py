import json
import base64
from datetime import datetime
from typing import Dict, Any
from app.services.ai_client import ai_client


class ReceiptScannerService:
    """Reads a photo of a paper receipt and pulls out the expense details, using a
    vision-capable Groq model — the same "AI figures it out" pattern as nlp_parser,
    just starting from an image instead of typed text."""

    async def scan_receipt(self, image_bytes: bytes, mime_type: str, user_currency: str = "UGX") -> Dict[str, Any]:
        if not ai_client.is_available:
            return self._fallback()

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = f"""
        You are an AI assistant for 'Ozzy for Business', helping a small business owner in Africa record an
        expense from a photo of a paper receipt.

        Look at the receipt in the image and return a JSON object with:
        - vendor: the shop or company name on the receipt, or "Unknown" if not legible.
        - item: a short description of what was bought (e.g. "transport", "fuel", "office supplies").
        - amount: the total amount paid, as a number (no currency symbol or commas).
        - currency: the currency code if visible on the receipt, otherwise "{user_currency}".
        - category: one of "Utilities", "Transport", "Rent", "Supplies", "Salaries", "Marketing", "Equipment", "Other" — pick the closest match.
        - transaction_date: the date on the receipt in YYYY-MM-DD format, or today's date ({datetime.now().strftime('%Y-%m-%d')}) if not legible.
        - confidence: a score from 0 to 1 for how confident you are this reading is accurate.

        Only return the JSON. No preamble.
        """

        result_text = ai_client.generate_from_image(prompt, image_base64, mime_type=mime_type, json_mode=True)
        if result_text is None:
            return self._fallback()

        try:
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()
            parsed = json.loads(result_text)
            parsed.setdefault("vendor", "Unknown")
            parsed.setdefault("item", "expense")
            parsed.setdefault("amount", 0)
            parsed.setdefault("currency", user_currency)
            parsed.setdefault("category", "Other")
            parsed.setdefault("transaction_date", datetime.now().strftime("%Y-%m-%d"))
            parsed.setdefault("confidence", 0.5)
            return parsed
        except Exception:
            return self._fallback()

    def _fallback(self) -> Dict[str, Any]:
        return {
            "vendor": "Unknown",
            "item": "expense",
            "amount": 0,
            "currency": "UGX",
            "category": "Other",
            "transaction_date": datetime.now().strftime("%Y-%m-%d"),
            "confidence": 0.0,
        }


receipt_scanner = ReceiptScannerService()
