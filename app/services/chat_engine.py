"""
Real tool-calling chat engine for 'Ozzy for Business'.

Replaces the old fixed-category classifier (sale/expense/inventory/query only) with a
proper toolbox the AI chooses from based on genuinely understanding what was typed —
including typos, shorthand, and casual phrasing — rather than exact keyword matching.
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionType
from app.models.item import Item
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.services.ai_client import ai_client
from app.services.invoice_parser import invoice_parser

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = Decimal(5)

EXPENSE_CATEGORIES = ["Utilities", "Transport", "Rent", "Supplies", "Salaries", "Marketing", "Equipment", "Other"]

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "record_sale",
            "description": (
                "Record money coming into the business from selling a product or service. "
                "Only include the amount if the user actually mentioned it — if not, omit it "
                "and Ozzy will ask for it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "What was sold"},
                    "amount": {"type": "number", "description": "Total money received. Omit if not mentioned."},
                    "quantity": {"type": "number", "description": "Number of units sold. Default 1."},
                },
                "required": ["item"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_expense",
            "description": (
                "Record money going out of the business — a purchase, bill, or payment. "
                "Only include the amount if the user actually mentioned it — if not, omit it "
                "and Ozzy will ask for it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "What the money was spent on"},
                    "amount": {"type": "number", "description": "Total amount spent. Omit if not mentioned."},
                    "quantity": {"type": "number", "description": "Number of units bought. Default 1."},
                    "category": {
                        "type": "string",
                        "enum": EXPENSE_CATEGORIES,
                        "description": "The best-fitting expense category.",
                    },
                },
                "required": ["item"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_summary",
            "description": (
                "Get real sales, expenses, profit, and best-selling products for a time period. "
                "Use this for any question about how the business is doing, revenue, spending, "
                "or which products sell best — never guess these numbers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["today", "week", "month", "custom"],
                        "description": "Which period to summarize. Default 'today' unless the user implies a longer view.",
                    },
                    "start_date": {"type": "string", "description": "YYYY-MM-DD, only when period is 'custom'."},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD, only when period is 'custom'."},
                },
                "required": ["period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Look up current stock levels — everything in stock, or one specific item by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "A specific product to look up, e.g. 'dresses'. Leave this field out entirely (not null) to list everything."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_low_stock",
            "description": "List items that are running low and may need restocking soon.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_invoice",
            "description": "Create an invoice (a bill sent before payment) for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "raw_text": {
                        "type": "string",
                        "description": "The customer name and item/quantity/price details, cleaned up from the user's message, e.g. 'Grace, 2 dresses at 30000 each'.",
                    },
                },
                "required": ["raw_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_receipt",
            "description": "Create a receipt (proof of a sale that has already been paid) for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "raw_text": {
                        "type": "string",
                        "description": "The customer name and item/quantity/price details, cleaned up from the user's message.",
                    },
                },
                "required": ["raw_text"],
            },
        },
    },
]


def _system_prompt(user: User) -> str:
    business = user.business_name or "their business"
    owner = user.owner_name or "the owner"
    categories_list = ", ".join(EXPENSE_CATEGORIES)
    return f"""You are Ozzy, a friendly AI assistant built into 'Ozzy for Business', a chat-first \
financial app for African small business owners. You're talking with {owner}, who runs {business}.

PERSONALITY: Speak in plain, warm, everyday language, like a helpful friend who already knows \
this business well — never robotic or formal.

UNDERSTANDING THE USER: People type quickly and casually. Understand typos, shorthand, and \
casual phrasing the way a person reading a text message naturally would — for example "slodd" \
clearly means "sold", and "brought" often means "bought" when the context is about a purchase. \
Don't require exact keyword matches; use judgment.

STAYING ON TOPIC: Only help with things related to {business} — sales, expenses, stock, \
invoices, receipts, and how the business is doing. If asked something with no connection to the \
business (general knowledge, unrelated topics), politely say you can only help with things \
related to their business, and redirect back to it. Do not answer unrelated questions.

TOOLS: Use the tools available whenever the message calls for one. Never guess or invent \
numbers — always call get_summary, get_inventory, or list_low_stock to get real figures before \
answering questions about performance or stock. When recording a sale or expense, just call \
record_sale or record_expense with what you understood — the app already shows the owner a \
Yes/No confirmation before anything is saved, so you don't need to ask "are you sure?" yourself.

EXPENSE CATEGORIES: When recording an expense, choose the closest fit: Electricity/water/\
internet/phone -> Utilities; fuel/boda-boda/taxi/delivery -> Transport; shop or office rent -> \
Rent; raw materials/stock/packaging -> Supplies; staff wages -> Salaries; ads/promotions -> \
Marketing; tools/machinery/furniture -> Equipment; anything else -> Other. (Full list: {categories_list}.)

AIRTIME & FLOAT: Airtime and mobile money float work like any product the owner resells. Judge \
the direction of money, not just the word "airtime": buying/topping up/restocking airtime (money \
OUT) is an expense, category Supplies. Selling airtime to a customer (money IN) is a sale.

The business's currency is {user.currency}. Use it in any amounts you mention.
"""


def _bounds(period: str, now: datetime, start_date: Optional[str], end_date: Optional[str]):
    if period == "custom" and start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date) + timedelta(days=1)
            return start, end
        except ValueError:
            pass  # fall through to a sane default below
    if period == "week":
        return now - timedelta(days=7), now
    if period == "month":
        return now - timedelta(days=30), now
    # "today" (default)
    return now.replace(hour=0, minute=0, second=0, microsecond=0), now


async def _sum_by_type(db: AsyncSession, business_id, tx_type: TransactionType, start: datetime, end: datetime) -> Decimal:
    stmt = select(func.sum(Transaction.amount)).where(
        Transaction.business_id == business_id,
        Transaction.type == tx_type,
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= end,
    )
    result = await db.execute(stmt)
    return result.scalar() or Decimal(0)


async def _best_sellers(db: AsyncSession, business_id, start: datetime, end: datetime, limit: int = 5) -> List[Dict[str, Any]]:
    stmt = (
        select(
            func.coalesce(Transaction.description, "Item"),
            func.sum(Transaction.quantity),
            func.sum(Transaction.amount),
        )
        .where(
            Transaction.business_id == business_id,
            Transaction.type == TransactionType.SALE,
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
        .group_by(func.coalesce(Transaction.description, "Item"))
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [{"name": row[0], "units": float(row[1] or 0), "revenue": float(row[2] or 0)} for row in result.all()]


async def _get_inventory(db: AsyncSession, user_id, item_name: Optional[str]) -> List[Dict[str, Any]]:
    stmt = select(Item).where(Item.user_id == user_id)  # Items aren't business-scoped yet (pre-existing gap)
    if item_name:
        stmt = stmt.where(Item.name.ilike(f"%{item_name}%"))
    result = await db.execute(stmt)
    return [
        {"name": i.name, "stock_level": float(i.stock_level or 0), "unit_price": float(i.unit_price or 0), "category": i.category}
        for i in result.scalars().all()
    ]


async def _list_low_stock(db: AsyncSession, user_id) -> List[Dict[str, Any]]:
    stmt = select(Item).where(Item.user_id == user_id, Item.stock_level > 0, Item.stock_level <= LOW_STOCK_THRESHOLD)
    result = await db.execute(stmt)
    return [{"name": i.name, "stock_level": float(i.stock_level or 0)} for i in result.scalars().all()]


async def _create_invoice(db: AsyncSession, user: User, raw_text: str, mark_paid: bool) -> Invoice:
    # Local imports to avoid a hard import-time cycle between the chat engine and the invoices
    # router — reusing its numbering/item-building helpers so both paths stay in sync.
    from app.api.api_v1.endpoints.invoices import _next_invoice_number, _build_items

    parsed = await invoice_parser.parse_invoice_text(raw_text, currency=user.currency)
    effective_business_id = user.business_id or user.id
    items = _build_items(parsed.get("items", []))
    total = sum((i.total_price for i in items), Decimal(0))

    invoice = Invoice(
        business_id=effective_business_id,
        created_by=user.id,
        invoice_number=await _next_invoice_number(db, effective_business_id),
        customer_name=parsed.get("customer_name") or "Customer",
        customer_email=parsed.get("customer_email"),
        customer_phone=parsed.get("customer_phone"),
        status=InvoiceStatus.PAID if mark_paid else InvoiceStatus.DRAFT,
        template=user.receipt_template,
        total_amount=total,
        currency=user.currency,
        notes=parsed.get("notes"),
        items=items,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice, attribute_names=["items"])
    return invoice


# How many rounds of "call a read-only tool, look at the result, maybe call another" to allow
# before giving up and answering from whatever was last found. gpt-oss-120b sometimes tries a
# second lookup (e.g. a narrower search term) when the first comes back empty, so one round trip
# isn't always enough — but this must still terminate.
MAX_TOOL_STEPS = 3

READ_ONLY_HANDLERS = {"get_summary", "get_inventory", "list_low_stock"}


class ChatEngine:
    async def handle_message(self, db: AsyncSession, user: User, text: str) -> Dict[str, Any]:
        if not ai_client.is_available:
            return {"reply": "Sorry, I can't process messages right now — the AI service isn't configured.", "action": "reply"}

        messages = [{"role": "system", "content": _system_prompt(user)}, {"role": "user", "content": text}]
        last_result: Optional[Dict[str, Any]] = None

        for _ in range(MAX_TOOL_STEPS):
            msg = ai_client.chat(messages, tools=TOOLS, tool_choice="auto")
            if msg is None:
                # Groq occasionally rejects a follow-up generation outright (e.g. the model
                # emitting an explicit null for an omitted optional argument). If we already
                # have a real tool result from an earlier step in this same message, answer
                # from that instead of surfacing a generic error over good data.
                if last_result is not None:
                    return {"reply": self._plain_fallback(last_result), "action": "reply"}
                return {"reply": "Sorry, something went wrong. Please try again.", "action": "reply"}

            if not msg.tool_calls:
                return {"reply": msg.content or "Sorry, I didn't quite catch that — could you rephrase?", "action": "reply"}

            # Only act on one tool call per turn — keeps the money-confirmation flow unambiguous.
            call = msg.tool_calls[0]
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            if name == "record_sale":
                return self._handle_record(user, "sale", args)
            if name == "record_expense":
                return self._handle_record(user, "expense", args)
            if name == "create_invoice":
                return await self._handle_invoice(db, user, args, mark_paid=False)
            if name == "create_receipt":
                return await self._handle_invoice(db, user, args, mark_paid=True)

            if name not in READ_ONLY_HANDLERS:
                return {"reply": "Sorry, I didn't quite catch that — could you rephrase?", "action": "reply"}

            if name == "get_summary" and user.role != "owner":
                return {"reply": "Profit and totals are only visible to the business owner. I can still help you record sales and expenses!", "action": "reply"}

            result = await self._run_read_only_tool(db, user, name, args)
            last_result = result

            # Feed the tool result back so the model can either answer in plain language, or —
            # if the first lookup came back empty — try again with a different search term.
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [{"id": call.id, "type": "function", "function": {"name": name, "arguments": call.function.arguments}}],
            })
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})

        # Ran out of tool-call rounds without a plain-language answer — fall back to a plain
        # sentence built from whatever the last lookup actually found, never raw JSON.
        return {"reply": self._plain_fallback(last_result), "action": "reply"}

    def _handle_record(self, user: User, tx_type: str, args: Dict[str, Any]) -> Dict[str, Any]:
        item = (args.get("item") or "item").strip() or "item"
        amount = float(args.get("amount") or 0)
        quantity = float(args.get("quantity") or 1)
        category = args.get("category") if tx_type == "expense" else "Sales Revenue"

        if amount <= 0:
            return {
                "reply": f"Got it — {item}. How much was it?",
                "action": "need_amount",
                "draft": {"type": tx_type, "description": item, "amount": 0, "quantity": quantity, "category": category},
            }
        return {
            "reply": None,
            "action": f"confirm_{tx_type}",
            "draft": {"type": tx_type, "description": item, "amount": amount, "quantity": quantity, "category": category},
        }

    async def _run_read_only_tool(self, db: AsyncSession, user: User, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name == "get_summary":
            business_id = user.business_id or user.id
            now = datetime.utcnow()
            period = args.get("period", "today")
            start, end = _bounds(period, now, args.get("start_date"), args.get("end_date"))
            total_sales = await _sum_by_type(db, business_id, TransactionType.SALE, start, end)
            total_expenses = await _sum_by_type(db, business_id, TransactionType.EXPENSE, start, end)
            best_sellers = await _best_sellers(db, business_id, start, end)
            return {
                "period": period,
                "currency": user.currency,
                "total_sales": float(total_sales),
                "total_expenses": float(total_expenses),
                "net_profit": float(total_sales - total_expenses),
                "best_sellers": best_sellers,
            }
        if name == "get_inventory":
            return {"items": await _get_inventory(db, user.id, args.get("item_name"))}
        # list_low_stock
        return {"low_stock_items": await _list_low_stock(db, user.id)}

    def _plain_fallback(self, result: Optional[Dict[str, Any]]) -> str:
        if not result:
            return "Sorry, I couldn't find an answer to that — could you rephrase?"
        if "items" in result:
            items = result["items"]
            if not items:
                return "I couldn't find that in your stock — it may not be added yet."
            return "Here's your current stock: " + ", ".join(f"{i['name']} ({i['stock_level']:g})" for i in items)
        if "low_stock_items" in result:
            items = result["low_stock_items"]
            if not items:
                return "Nothing is running low right now — you're well stocked!"
            return "Running low on: " + ", ".join(f"{i['name']} ({i['stock_level']:g} left)" for i in items)
        if "total_sales" in result:
            return (
                f"For {result['period']}: sales {result['currency']} {result['total_sales']:,.0f}, "
                f"expenses {result['currency']} {result['total_expenses']:,.0f}, "
                f"profit {result['currency']} {result['net_profit']:,.0f}."
            )
        return "Sorry, I couldn't find an answer to that — could you rephrase?"

    async def _handle_invoice(self, db: AsyncSession, user: User, args: Dict[str, Any], mark_paid: bool) -> Dict[str, Any]:
        if user.role != "owner":
            return {"reply": "Only the business owner can create invoices and receipts.", "action": "reply"}

        raw_text = (args.get("raw_text") or "").strip()
        if not raw_text:
            return {"reply": "Who is this for, and what are they buying?", "action": "reply"}

        invoice = await _create_invoice(db, user, raw_text, mark_paid=mark_paid)
        doc = "Receipt" if mark_paid else "Invoice"
        reply = (
            f"🧾 {doc} {invoice.invoice_number} created for {invoice.customer_name} — "
            f"total {invoice.currency} {float(invoice.total_amount):,.0f}. "
            f"You can view, download, or share it anytime from Invoices."
        )
        return {"reply": reply, "action": "reply"}


chat_engine = ChatEngine()
