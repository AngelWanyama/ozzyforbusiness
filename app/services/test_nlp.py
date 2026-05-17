import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.nlp_parser import nlp_parser

async def test_parser():
    test_cases = [
        "Sold dress 20,000",
        "Paid rent 300,000",
        "Bought 5 boxes of milk for 50000",
        "How much profit did I make yesterday?"
    ]
    
    for case in test_cases:
        print(f"\nParsing: {case}")
        result = await nlp_parser.parse_transaction(case)
        print(f"Result: {result.model_dump()}")

if __name__ == "__main__":
    asyncio.run(test_parser())
