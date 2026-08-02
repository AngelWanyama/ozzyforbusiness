import json
import re
from typing import Dict, Any
from app.services.ai_client import ai_client


class InvoiceParserService:
    """Turns a plain-language invoice request ("Invoice for Grace, 3 dresses @ 35,000")
    into structured customer + line-item data, the same way the chat engine does for transactions."""

    async def parse_invoice_text(self, text: str, currency: str = "UGX") -> Dict[str, Any]:
        if not ai_client.is_available:
            return self._fallback_parse(text)

        prompt = f"""
        You are an AI assistant for 'Ozzy for Business', helping small business owners in Africa create invoices
        from a plain-language description.

        User Entry: "{text}"
        Default Currency: {currency}

        Return a JSON object with:
        - customer_name: the person or business being billed. If not stated, use "Customer".
        - customer_phone: phone number if mentioned, else null.
        - customer_email: email if mentioned, else null.
        - items: a list of {{"description": str, "quantity": number, "unit_price": number}}.
          "@ 35,000" means unit_price is 35000. If a total is given instead of a per-unit price
          (e.g. "3 dresses for 90,000"), divide by quantity to get unit_price.
        - notes: any extra instructions mentioned (payment terms, delivery notes), else null.

        Example:
        User Entry: "Invoice for Grace, 3 dresses @ 35,000, 2 scarves @ 15,000"
        Output: {{"customer_name": "Grace", "customer_phone": null, "customer_email": null, "items": [{{"description": "dresses", "quantity": 3, "unit_price": 35000}}, {{"description": "scarves", "quantity": 2, "unit_price": 15000}}], "notes": null}}

        Only return the JSON. No preamble.
        """

        result_text = ai_client.generate(prompt, json_mode=True)
        if result_text is None:
            return self._fallback_parse(text)

        try:
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()
            parsed = json.loads(result_text)
            if not parsed.get("items"):
                return self._fallback_parse(text)
            return parsed
        except Exception:
            return self._fallback_parse(text)

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """Very basic rule-based parsing when the AI isn't available or fails."""
        name_match = re.search(r'(?:for|customer:?)\s+([A-Za-z][\w\s]{1,30}?)(?:,|$)', text, re.IGNORECASE)
        customer_name = name_match.group(1).strip() if name_match else "Customer"

        # Look for "<qty> <item> @ <price>" segments; fall back to one line item with the last number found.
        items = []
        for qty, desc, price in re.findall(r'(\d+)\s*([A-Za-z][\w\s]*?)\s*@\s*([\d,]+(?:\.\d+)?)', text):
            items.append({
                "description": desc.strip() or "Item",
                "quantity": float(qty),
                "unit_price": float(price.replace(',', '')),
            })

        if not items:
            numbers = re.findall(r'[\d,]+(?:\.\d+)?', text)
            amount = float(numbers[-1].replace(',', '')) if numbers else 0
            items = [{"description": "Item", "quantity": 1, "unit_price": amount}]

        return {
            "customer_name": customer_name,
            "customer_phone": None,
            "customer_email": None,
            "items": items,
            "notes": None,
        }


invoice_parser = InvoiceParserService()
