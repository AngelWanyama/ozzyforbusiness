import asyncio
import os
import sys
import json
from datetime import datetime, date

# Add project root to sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.nlp_parser import nlp_parser

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)

async def validate_nlp():
    # Format: (input_text, expected_dict)
    test_cases = [
        ("Sold dress 20,000", {"intent": "sale", "amount": 20000, "item": "dress", "quantity": 1}),
        ("Bought 3kg onions 5000", {"intent": "expense", "amount": 5000, "item": "onions", "quantity": 3}),
        ("Paid mama rent 300k", {"intent": "expense", "amount": 300000, "item": "rent", "quantity": 1}),
        ("Stock now 10 dresses", {"intent": "inventory", "amount": 0, "item": "dresses", "quantity": 10}),
        ("Sold 2 bags of sugar 10k each", {"intent": "sale", "amount": 20000, "item": "sugar", "quantity": 2}),
        ("Received 100k for catering", {"intent": "sale", "amount": 100000, "item": "catering", "quantity": 1}),
        ("Paid for water 15k", {"intent": "expense", "amount": 15000, "item": "water", "quantity": 1}),
        ("Electricity bill 40,000", {"intent": "expense", "amount": 40000, "item": "electricity", "quantity": 1}),
        ("Bought 5 crates of soda for 150k", {"intent": "expense", "amount": 150000, "item": "soda", "quantity": 5}),
        ("Paid transport 5000", {"intent": "expense", "amount": 5000, "item": "transport", "quantity": 1}),
        ("Customer paid 20k for hair", {"intent": "sale", "amount": 20000, "item": "hair", "quantity": 1}),
        ("Bought new shelf 200k", {"intent": "expense", "amount": 200000, "item": "shelf", "quantity": 1}),
        ("Sold 3 shirts 60,000", {"intent": "sale", "amount": 60000, "item": "shirts", "quantity": 3}),
        ("Stocked 20 more soaps", {"intent": "inventory", "amount": 0, "item": "soaps", "quantity": 20}),
        ("How much did I sell today?", {"intent": "query"}),
        ("Show me my expenses for this week", {"intent": "query"}),
        ("Paid staff salaries 500k", {"intent": "expense", "amount": 500000, "item": "salaries", "quantity": 1}),
        ("Sold phone case 15000", {"intent": "sale", "amount": 15000, "item": "phone case", "quantity": 1}),
        ("Bought 2kg rice 12000", {"intent": "expense", "amount": 12000, "item": "rice", "quantity": 2}),
        ("Sold bread 5000", {"intent": "sale", "amount": 5000, "item": "bread", "quantity": 1}),
        ("Paid for cleaning 10k", {"intent": "expense", "amount": 10000, "item": "cleaning", "quantity": 1}),
        ("Added 15 bags of flour to stock", {"intent": "inventory", "amount": 0, "item": "flour", "quantity": 15}),
        ("What is my profit?", {"intent": "query"}),
        ("Sold milk 3000", {"intent": "sale", "amount": 3000, "item": "milk", "quantity": 1}),
        ("Bought 10 eggs 5000", {"intent": "expense", "amount": 5000, "item": "eggs", "quantity": 10}),
        ("Paid loan 100k", {"intent": "expense", "amount": 100000, "item": "loan", "quantity": 1}),
        ("Sold dress 45k", {"intent": "sale", "amount": 45000, "item": "dress", "quantity": 1}),
        ("Bought 3m of fabric 90k", {"intent": "expense", "amount": 90000, "item": "fabric", "quantity": 3}),
        ("Paid for parking 2000", {"intent": "expense", "amount": 2000, "item": "parking", "quantity": 1}),
        ("Sold juice 2500", {"intent": "sale", "amount": 2500, "item": "juice", "quantity": 1}),
        ("Bought 2 pens 1000", {"intent": "expense", "amount": 1000, "item": "pens", "quantity": 2}),
        ("Paid data 5000", {"intent": "expense", "amount": 5000, "item": "data", "quantity": 1}),
        ("Stock check 5 watches", {"intent": "inventory", "amount": 0, "item": "watches", "quantity": 5}),
        ("Sold watch 150k", {"intent": "sale", "amount": 150000, "item": "watch", "quantity": 1}),
        ("Bought battery 5000", {"intent": "expense", "amount": 5000, "item": "battery", "quantity": 1}),
        ("Paid for repairs 30k", {"intent": "expense", "amount": 30000, "item": "repairs", "quantity": 1}),
        ("Sold 5 books 45k", {"intent": "sale", "amount": 45000, "item": "books", "quantity": 5}),
        ("Bought 2 chairs 80k", {"intent": "expense", "amount": 80000, "item": "chairs", "quantity": 2}),
        ("Paid for delivery 7000", {"intent": "expense", "amount": 7000, "item": "delivery", "quantity": 1}),
        ("Sold bag 35k", {"intent": "sale", "amount": 35000, "item": "bag", "quantity": 1}),
        ("Bought 3 notebooks 6000", {"intent": "expense", "amount": 6000, "item": "notebooks", "quantity": 3}),
        ("Paid for light 12k", {"intent": "expense", "amount": 12000, "item": "light", "quantity": 1}),
        ("Stock now 12 hats", {"intent": "inventory", "amount": 0, "item": "hats", "quantity": 12}),
        ("Sold hat 8k", {"intent": "sale", "amount": 8000, "item": "hat", "quantity": 1}),
        ("Bought 5 shirts 100k", {"intent": "expense", "amount": 100000, "item": "shirts", "quantity": 5}),
        ("Paid for tea 2000", {"intent": "expense", "amount": 2000, "item": "tea", "quantity": 1}),
        ("Sold 2 plates of food 15k", {"intent": "sale", "amount": 15000, "item": "food", "quantity": 2}),
        ("Bought 1kg meat 14k", {"intent": "expense", "amount": 14000, "item": "meat", "quantity": 1}),
        ("Paid for charcoal 10k", {"intent": "expense", "amount": 10000, "item": "charcoal", "quantity": 1}),
        ("Sold 3 sodas 6k", {"intent": "sale", "amount": 6000, "item": "sodas", "quantity": 3}),
        ("Bought 10kg beans 40k", {"intent": "expense", "amount": 40000, "item": "beans", "quantity": 10}),
        ("Paid for airtime 5000", {"intent": "expense", "amount": 5000, "item": "airtime", "quantity": 1}),
        ("Sold 2 pairs of socks 10k", {"intent": "sale", "amount": 10000, "item": "socks", "quantity": 2})
    ]
    
    results = []
    stats = {
        "intent": 0,
        "amount": 0,
        "item": 0,
        "quantity": 0
    }
    
    total = len(test_cases)
    
    print(f"Testing {total} samples...")
    print(f"Gemini API Configured: {nlp_parser.model is not None}")
    
    for text, expected in test_cases:
        try:
            parsed = await nlp_parser.parse_transaction(text)
            parsed_dict = parsed.model_dump()
            
            # Record matches
            match = {
                "input": text,
                "expected": expected,
                "actual": parsed_dict,
                "matches": {
                    "intent": parsed_dict["intent"] == expected["intent"],
                    "amount": parsed_dict.get("amount") == expected.get("amount") if "amount" in expected else True,
                    "item": parsed_dict.get("item") == expected.get("item") if "item" in expected else True,
                    "quantity": parsed_dict.get("quantity") == expected.get("quantity") if "quantity" in expected else True
                }
            }
            
            if match["matches"]["intent"]: stats["intent"] += 1
            if match["matches"]["amount"]: stats["amount"] += 1
            if match["matches"]["item"]: stats["item"] += 1
            if match["matches"]["quantity"]: stats["quantity"] += 1
            
            results.append(match)
            
        except Exception as e:
            print(f"Error parsing '{text}': {e}")
            
    print(f"\nValidation Complete.")
    print(f"Intent Accuracy: {(stats['intent']/total)*100:.2f}%")
    print(f"Amount Accuracy: {(stats['amount']/total)*100:.2f}%")
    print(f"Item Accuracy: {(stats['item']/total)*100:.2f}%")
    print(f"Quantity Accuracy: {(stats['quantity']/total)*100:.2f}%")
    
    # Save results to a report file
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_samples": total,
        "accuracies": {
            "intent": (stats['intent']/total),
            "amount": (stats['amount']/total),
            "item": (stats['item']/total),
            "quantity": (stats['quantity']/total)
        },
        "gemini_enabled": nlp_parser.model is not None,
        "details": results
    }
    
    with open("/home/team/shared/backend/nlp_validation_report.json", "w") as f:
        json.dump(report, f, indent=2, cls=DateTimeEncoder)
    
    print(f"Report saved to /home/team/shared/backend/nlp_validation_report.json")

if __name__ == "__main__":
    asyncio.run(validate_nlp())
