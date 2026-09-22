"""
Real tool-calling chat engine for 'Ozzy for Business', built to Appendix A of the Ozzy
Behaviour Intelligence Brain (brain-spec/Ozzy_Behaviour_Intelligence_Brain_v1.md).

Implements the full Appendix A function catalog via OpenAI function-calling, and the
PROPOSE/COMMIT state machine: a propose_* (or single L2/L3/L4) tool call only ever computes
and returns a preview, it never writes to the database. The database write only happens once
the application layer (not the model) has verified a real, new confirmation message from the
entrepreneur against the specific stored proposal shown. See ChatProposal for the storage side
of that mechanism.
"""
import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionType
from app.models.item import Item
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invite import Invite
from app.models.chat_proposal import ChatProposal
from app.models.user import User
from app.services.ai_client import ai_client
from app.services.invoice_parser import invoice_parser

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = Decimal(5)
PROPOSAL_EXPIRY_MINUTES = 10

EXPENSE_CATEGORIES = ["Stock/Inventory", "Rent", "Transport", "Utilities", "Salaries", "Other"]

# Volume 17: Workers can record sales/expenses and see the past week's activity. They cannot
# see Reports/profit/totals, activity older than a week, export, Settings, add/remove workers,
# or create documents (kept consistent with the existing owner-only invoicing gate). Enforced
# here in code, independently of whatever the model was told or attempted.
OWNER_ONLY_FUNCTIONS = {
    "get_report_summary",
    "generate_document_preview", "send_document", "mark_document_paid",
    "update_profile_field", "propose_currency_change", "commit_currency_change",
    "generate_worker_invite", "propose_remove_worker", "commit_remove_worker",
}

# Functions that write nothing on the model's PROPOSE turn, they compute a preview, get stored
# as a ChatProposal, and only take effect once a real confirmation message passes the check in
# handle_message. update_profile_field is deliberately absent: Volume 4 makes it L1, instant
# apply with a same-session undo, not a PROPOSE/COMMIT action.
PROPOSAL_FUNCTIONS = {
    "propose_sale", "propose_expense", "add_product", "mark_customer_paid",
    "generate_document_preview", "propose_currency_change",
    "generate_worker_invite", "propose_remove_worker", "mark_document_paid",
}

READ_ONLY_FUNCTIONS = {"get_report_summary", "get_recent_activity", "get_inventory", "list_low_stock"}

# A propose_sale/propose_expense proposal stored before every field is known (still missing an
# amount, or waiting on a new product) is never auto-committable, a "yes" here answers a
# clarifying question, not "record this", so it must always go back through the model with
# full context rather than straight to a commit_* handler.
INCOMPLETE_PROPOSAL_FUNCTIONS = {"propose_sale_incomplete", "propose_expense_incomplete"}

AFFIRMATIVE_RE = re.compile(r"^(yes|yeah|yep|yup|sure|ok(ay)?|confirm(ed)?|correct|right|go ahead|do it|record it|proceed)[.!\s]*$", re.IGNORECASE)
NEGATIVE_RE = re.compile(r"^(no|nah|nope|cancel|stop|wrong|never ?mind|not now|don'?t)[.!\s]*$", re.IGNORECASE)

# Same "how many read-only tool round trips before giving up" cap the old engine used —
# gpt-4o-mini occasionally tries a second, narrower lookup when the first comes back empty.
MAX_TOOL_STEPS = 3


TOOLS = [
    {"type": "function", "function": {
        "name": "propose_sale",
        "description": (
            "PROPOSE step (Volume 6). Parses a sale from the entrepreneur's message and returns a preview. "
            "Never writes to the database.\n"
            "PRICE WORDING IS ALREADY CLEAR, call this normally, when the message uses a word like 'each', "
            "'apiece', '@', or 'per' (e.g. '2 dresses at 30000 each' clearly means unit_price=30000), OR a word "
            "like 'total', 'altogether', or 'in all' (e.g. '2 dresses for a total of 60000' clearly means "
            "line_total=60000), OR quantity is 1. In all of these, set unit_price or line_total directly and "
            "call this function, do not ask anything.\n"
            "PRICE WORDING IS GENUINELY AMBIGUOUS, do NOT call this, ask a plain-text clarifying question "
            "instead, only when quantity is more than 1 AND a single price was given with NEITHER of those "
            "words (e.g. bare '2 sodas for 6000', ask 'Is that 6,000 total, or 6,000 each?'). Do not invent "
            "this ambiguity when the wording already answers it."
        ),
        "parameters": {"type": "object", "properties": {
            "line_items": {"type": "array", "items": {"type": "object", "properties": {
                "product_name": {"type": "string"},
                "quantity": {"type": "number", "description": "Default 1."},
                "unit_price": {"type": "number", "description": "Set when the message says 'each'/'apiece'/'@'/'per', or quantity is 1."},
                "line_total": {"type": "number", "description": "Set when the message says 'total'/'altogether'/'in all', or quantity is 1."},
            }, "required": ["product_name"]}},
            "customer_name": {"type": "string", "description": "Required only for credit sales."},
            "payment_type": {
                "type": "string", "enum": ["cash", "credit", "mobile_money"],
                "description": "Omit entirely if not stated, defaults to cash, per Volume 6's reference example, which never asks payment type for an ordinary sale. Only set to credit when a customer is named or credit is explicitly mentioned.",
            },
            "discount_amount": {"type": "number", "description": "Only when explicitly stated, never inferred."},
        }, "required": ["line_items"]},
    }},
    {"type": "function", "function": {
        "name": "add_product",
        "description": "Adds a new product to the catalog (Volume 5). Used when a sale mentions a product not yet in the catalog.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"},
            "buying_price": {"type": "number", "description": "Omit for a service."},
            "selling_price": {"type": "number"},
            "is_service": {"type": "boolean", "description": "Omit if not stated, defaults to a regular product (false), per Volume 5's reference example, which doesn't ask this for an ordinary item."},
        }, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "propose_expense",
        "description": "PROPOSE step (Volume 7). Parses an expense and returns a preview with an assigned category. Never writes to the database.",
        "parameters": {"type": "object", "properties": {
            "description": {"type": "string"},
            "amount": {"type": "number"},
            "category": {"type": "string", "enum": EXPENSE_CATEGORIES},
        }, "required": ["description", "amount", "category"]},
    }},
    {"type": "function", "function": {
        "name": "mark_customer_paid",
        "description": "Clears some or all of a customer's outstanding balance (Volume 8). Preview only, omit amount to mark the full balance paid.",
        "parameters": {"type": "object", "properties": {
            "customer_name": {"type": "string"},
            "amount": {"type": "number"},
        }, "required": ["customer_name"]},
    }},
    {"type": "function", "function": {
        "name": "generate_document_preview",
        "description": "PROPOSE step (Volume 9). Builds an invoice or receipt preview for a customer. Never writes to the database.",
        "parameters": {"type": "object", "properties": {
            "customer_name": {"type": "string"},
            "items": {"type": "array", "items": {"type": "object", "properties": {
                "description": {"type": "string"}, "quantity": {"type": "number"}, "unit_price": {"type": "number"},
            }}},
            "raw_text": {"type": "string", "description": "The rest of the request cleaned up, e.g. '2 dresses at 30000 each', used if items isn't already broken out."},
            "already_paid": {"type": "boolean", "description": "True if this is a receipt (already paid) rather than an invoice (not yet paid)."},
        }, "required": ["customer_name"]},
    }},
    {"type": "function", "function": {
        "name": "send_document",
        "description": "COMMIT step (Volume 9). Finalises and shares a previously previewed invoice/receipt.",
        "parameters": {"type": "object", "properties": {
            "channel": {"type": "string", "enum": ["whatsapp", "email", "pdf"]},
        }, "required": ["channel"]},
    }},
    {"type": "function", "function": {
        "name": "mark_document_paid",
        "description": "Converts an existing invoice into a receipt (Volume 9). Preview only.",
        "parameters": {"type": "object", "properties": {
            "customer_name": {"type": "string", "description": "Whose invoice to mark paid, the most recent unpaid one for them."},
        }, "required": ["customer_name"]},
    }},
    {"type": "function", "function": {
        "name": "update_profile_field",
        "description": "Instant, low-stakes profile update (Volume 4), business name, type, or logo only. Applies immediately, no confirmation needed.",
        "parameters": {"type": "object", "properties": {
            "field": {"type": "string", "enum": ["name", "type"]},
            "value": {"type": "string"},
        }, "required": ["field", "value"]},
    }},
    {"type": "function", "function": {
        "name": "propose_currency_change",
        "description": "PROPOSE step (Volume 4). Currency changes are account-level and largely irreversible, always confirmed, never instant.",
        "parameters": {"type": "object", "properties": {"new_currency": {"type": "string"}}, "required": ["new_currency"]},
    }},
    {"type": "function", "function": {
        "name": "generate_worker_invite",
        "description": "Creates a 6-digit, single-use, 7-day invite code for a new Worker (Volume 17). Preview only, confirm before creating the real code.",
        "parameters": {"type": "object", "properties": {"worker_phone_number": {"type": "string"}}, "required": ["worker_phone_number"]},
    }},
    {"type": "function", "function": {
        "name": "propose_remove_worker",
        "description": "PROPOSE step (Volume 17). Revokes a Worker's access to the business.",
        "parameters": {"type": "object", "properties": {"worker_phone_number": {"type": "string"}}, "required": ["worker_phone_number"]},
    }},
    {"type": "function", "function": {
        "name": "get_report_summary",
        "description": "Owner-only (Volume 10). Real sales, expenses, and profit for a period, never guess these numbers.",
        "parameters": {"type": "object", "properties": {
            "period": {"type": "string", "enum": ["today", "this_week", "this_month", "custom"]},
            "start_date": {"type": "string"}, "end_date": {"type": "string"},
        }, "required": ["period"]},
    }},
    {"type": "function", "function": {
        "name": "get_recent_activity",
        "description": "Recent recorded sales/expenses (Volume 17). For a Worker sender this is capped at 7 days server-side no matter what is requested here.",
        "parameters": {"type": "object", "properties": {"days": {"type": "number"}}},
    }},
    {"type": "function", "function": {
        "name": "get_inventory",
        "description": "Current stock levels, everything, or one specific item by name.",
        "parameters": {"type": "object", "properties": {"item_name": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "list_low_stock",
        "description": "Items running low and worth restocking soon.",
        "parameters": {"type": "object", "properties": {}},
    }},
]


# ─── System prompt (Appendix A: Identity / Business Context / Product & Customer Context /
# Conversation State / Role Scope / Authority Levels, in that order) ────────────────────────

def _identity_block() -> str:
    return (
        "IDENTITY: You are Ozzy, competent, honest, calm, supportive, direct, respectful. "
        "Your core promise is managing a business as simply as chatting with someone who already "
        "understands it. The only approved way to describe what you do is \"AI-powered financial "
        "management\" — never say \"bookkeeping\" or \"accounting\", in any form, ever. Never open "
        "with a generic \"How can I help?\". Speak in plain, warm, everyday language, never robotic "
        "or formal. Never use an em dash (—) in anything you write — use a comma, a period, or "
        "start a new sentence instead. Understand typos, shorthand, and casual phrasing the way a "
        "person reading a text message naturally would (\"slodd\" means \"sold\"; \"60k\" means "
        "60,000). Only help with things related to this business: sales, expenses, stock, invoices, "
        "receipts, workers, and how the business is doing. Politely redirect anything unrelated. "
        "AIRTIME & FLOAT: judge the direction of money, not just the word \"airtime\". Buying, "
        "topping up, or restocking airtime or float (money OUT) is an expense. Selling airtime to a "
        "customer (money IN) is a sale."
    )


def _business_context_block(user: User) -> str:
    return (
        f"BUSINESS CONTEXT: Business name: {user.business_name or 'not set yet'}. "
        f"Type: {user.business_type or 'not set yet'}. Currency: {user.currency}. "
        f"Owner: {user.owner_name or 'not set yet'}."
    )


async def _product_customer_context_block(db: AsyncSession, business_id) -> str:
    items_stmt = select(Item.name).where(Item.business_id == business_id).limit(100)
    items = [r[0] for r in (await db.execute(items_stmt)).all()]
    customers_stmt = select(Customer.name).where(Customer.business_id == business_id).order_by(Customer.created_at.desc()).limit(20)
    customers = [r[0] for r in (await db.execute(customers_stmt)).all()]
    return (
        f"PRODUCT & CUSTOMER CONTEXT: Known products: {', '.join(items) if items else 'none yet'}. "
        f"Recent customers: {', '.join(customers) if customers else 'none yet'}. "
        "Match typos/near-matches against these before treating something as new."
    )


def _conversation_state_block(pending: Optional[ChatProposal]) -> str:
    if pending is None:
        return "CONVERSATION STATE: No pending transaction is currently awaiting confirmation."

    detail = ""
    line_items = (pending.payload or {}).get("line_items")
    if line_items:
        # The preview text alone ("Sale: dresses x2, total UGX 60,000") isn't enough to correctly
        # recompute a quantity change, only the per-item unit price is. Spell it out explicitly so
        # a correction like "actually make it 3" gets recalculated (90,000), not left at the old
        # total (60,000) or copied forward verbatim.
        parts = []
        for li in line_items:
            qty = li.get("quantity") or 1
            total = li.get("line_total")
            unit = (total / qty) if (total is not None and qty) else None
            unit_str = f"unit price {unit:g}" if unit is not None else "unit price not yet known"
            parts.append(f"{li.get('product_name')}: quantity {qty:g}, {unit_str}")
        detail = " Line items as currently understood: " + "; ".join(parts) + "."

    return (
        f"CONVERSATION STATE: There IS a pending, unconfirmed proposal awaiting a yes/no reply: "
        f"\"{pending.preview_text}\" (type: {pending.function_name}).{detail} If the entrepreneur's "
        "new message is a correction to this (e.g. a different quantity), recompute the total from "
        "the real unit price above, do not just repeat the old total. If it's unrelated, just handle "
        "the new message, the old proposal stays pending in the background."
    )


def _role_scope_block(user: User) -> str:
    if user.role == "worker":
        return (
            "ROLE SCOPE: This sender is a WORKER, not the Owner. Workers may record sales and "
            "expenses and see up to the past 7 days of activity. Workers cannot see Reports, "
            "profit, or totals; cannot see activity older than 7 days; cannot export/download; "
            "cannot touch Settings, currency, or business profile; cannot add or remove workers; "
            "cannot create or send invoices/receipts. If asked for any of this, decline clearly "
            "and say it's Owner-only, do not reveal the restricted data even partially."
        )
    return "ROLE SCOPE: This sender is the business Owner, full access."


def _authority_levels_block() -> str:
    return (
        "AUTHORITY LEVELS: L0 silent/no mention. L1 informational, no confirmation needed. "
        "L2 suggested action, needs an explicit yes. L3 confirmed financial action (money, "
        "inventory, or a customer document), always needs explicit confirmation, no exceptions. "
        "L4 irreversible/account-level action, always needs explicit confirmation. Never call a "
        "propose_*/add_product/mark_*/generate_*/send_*/commit_* function and simultaneously claim "
        "it is already done, the app shows the entrepreneur a preview and waits for a real new "
        "reply before anything is saved. Never guess a number, call the matching read-only tool. "
        "No L3 action is ever taken from an ambiguous message, if you're not certain what a money "
        "detail actually means (not just whether you know it), ask one direct, specific question in "
        "plain text instead of calling a tool with a guessed value. This is the core of what makes "
        "Ozzy conversational rather than a form: a genuinely ambiguous price, quantity, or amount "
        "always gets a real question, every time, never a silent assumption, e.g. '2 sodas for "
        "6000' doesn't say whether that's 6,000 total or 6,000 each, so ask which, don't pick one. "
        "But do not manufacture ambiguity that isn't there: '2 dresses at 30000 each' already says "
        "each, and '2 dresses for a total of 60000' already says total, so proceed normally on both."
    )


async def _system_prompt(db: AsyncSession, user: User, pending: Optional[ChatProposal]) -> str:
    business_id = user.business_id or user.id
    blocks = [
        _identity_block(),
        _business_context_block(user),
        await _product_customer_context_block(db, business_id),
        _conversation_state_block(pending),
        _role_scope_block(user),
        _authority_levels_block(),
    ]
    return "\n\n".join(blocks)


# ─── Proposal store (the PROPOSE/COMMIT mechanism itself) ───────────────────────────────────

async def _get_pending_proposal(db: AsyncSession, user_id) -> Optional[ChatProposal]:
    stmt = select(ChatProposal).where(
        ChatProposal.user_id == user_id,
        ChatProposal.status == "pending",
        ChatProposal.expires_at > datetime.utcnow(),
    ).order_by(ChatProposal.created_at.desc())
    return (await db.execute(stmt)).scalars().first()


async def _create_proposal(db: AsyncSession, user: User, function_name: str, payload: Dict[str, Any], preview_text: str) -> ChatProposal:
    # Only one pending proposal per conversation at a time, a fresh one supersedes any other
    # still-pending proposal for this user, per Appendix A's PROPOSE/COMMIT state machine.
    stmt = select(ChatProposal).where(ChatProposal.user_id == user.id, ChatProposal.status == "pending")
    for stale in (await db.execute(stmt)).scalars().all():
        stale.status = "superseded"

    proposal = ChatProposal(
        business_id=user.business_id or user.id,
        user_id=user.id,
        function_name=function_name,
        payload=payload,
        preview_text=preview_text,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=PROPOSAL_EXPIRY_MINUTES),
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return proposal


def _classify_reply(text: str) -> str:
    t = text.strip()
    if AFFIRMATIVE_RE.match(t):
        return "yes"
    if NEGATIVE_RE.match(t):
        return "no"
    return "other"


# ─── Helpers shared by propose/commit handlers ───────────────────────────────────────────────

async def _match_item(db: AsyncSession, business_id, name: str) -> Optional[Item]:
    stmt = select(Item).where(Item.business_id == business_id, Item.name.ilike(f"%{name}%")).limit(1)
    return (await db.execute(stmt)).scalars().first()


async def _find_or_create_customer(db: AsyncSession, business_id, name: str) -> Customer:
    stmt = select(Customer).where(Customer.business_id == business_id, func.lower(Customer.name) == name.strip().lower())
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        return existing
    customer = Customer(business_id=business_id, name=name.strip(), outstanding_balance=Decimal(0))
    db.add(customer)
    await db.flush()
    return customer


def _fmt(currency: str, amount) -> str:
    return f"{currency} {float(amount):,.0f}"


class ChatEngine:
    # In-memory, session-scoped "last change" per user for update_profile_field's Volume 4
    # same-session undo. Not persisted, an undo only needs to survive the current process,
    # and this never holds more than one entry per active user.
    _last_profile_edit: Dict[str, Dict[str, Any]] = {}

    async def handle_message(self, db: AsyncSession, user: User, text: str) -> Dict[str, Any]:
        if not ai_client.is_available:
            return {"reply": "Sorry, I can't process messages right now, the AI service isn't configured.", "action": "reply"}

        text = text.strip()
        if text.lower() == "undo that" or text.lower() == "undo":
            return await self._handle_undo(db, user)

        pending = await _get_pending_proposal(db, user.id)
        if pending is not None and pending.function_name not in INCOMPLETE_PROPOSAL_FUNCTIONS:
            verdict = _classify_reply(text)
            if verdict == "yes":
                return await self._commit_proposal(db, user, pending)
            if verdict == "no":
                pending.status = "cancelled"
                await db.commit()
                return {"reply": "No problem, cancelled.", "action": "reply"}
            # "other": leave the pending proposal alone (still confirmable later) and let the
            # model handle this new message, it may be a correction, in which case a fresh
            # proposal naturally supersedes the old one.

        # A bare "yes" to "want me to add this product?" is handled directly in app code, not
        # by asking the model to call add_product, in testing (real gpt-4o-mini, not just the
        # Groq fallback), the model would often just chat about the "yes" instead of acting on
        # it. Every other unmatched-item wording ("yes, bought it at 50000", a correction, etc.)
        # still falls through to the model turn below, which can handle price and nuance.
        if pending is not None and pending.function_name == "propose_sale_incomplete" and _classify_reply(text) == "yes":
            resolved = await self._auto_add_unmatched_products(db, user, pending)
            if resolved is not None:
                return resolved
        # An incomplete proposal (still missing an amount, or waiting on a new product) is
        # never auto-committed on "yes", it always falls through to a real model turn below,
        # which has the pending proposal's context and decides what the reply actually means.

        return await self._run_ai_turn(db, user, text, pending)

    async def confirm_proposal_by_id(self, db: AsyncSession, user: User, proposal_id: str) -> Dict[str, Any]:
        """Backs the confirm-card Yes button, an explicit, unambiguous confirmation, the same
        guarantee as a typed 'yes' but without requiring one."""
        try:
            pid = uuid.UUID(proposal_id)
        except ValueError:
            return {"ok": False, "reply": "That confirmation has expired, please send it again."}
        stmt = select(ChatProposal).where(ChatProposal.id == pid, ChatProposal.user_id == user.id)
        proposal = (await db.execute(stmt)).scalars().first()
        if not proposal or proposal.status != "pending" or proposal.expires_at <= datetime.utcnow():
            return {"ok": False, "reply": "That confirmation has expired, please send it again."}
        if proposal.function_name == "propose_sale_incomplete":
            # The only button-confirmable propose_sale_incomplete case is "want me to add this
            # new product?" -- shares the exact handler typed "yes" already uses. If this
            # particular proposal was actually the "how much in total?" sub-case instead, it was
            # never offered as a button in the first place (see _propose_sale, that branch stays
            # action="need_amount"), so this only ever runs for the yes/no case in practice.
            resolved = await self._auto_add_unmatched_products(db, user, proposal)
            if resolved is None:
                return {"ok": False, "reply": "That confirmation has expired, please send it again."}
            return {"ok": True, **resolved}
        if proposal.function_name in INCOMPLETE_PROPOSAL_FUNCTIONS:
            return {"ok": False, "reply": "That confirmation has expired, please send it again."}
        result = await self._commit_proposal(db, user, proposal)
        return {"ok": True, **result}

    async def cancel_proposal_by_id(self, db: AsyncSession, user: User, proposal_id: str) -> Dict[str, Any]:
        """Backs the confirm-card No button (2026-09-22 platform-wide button rule) -- the same
        explicit, unambiguous guarantee as a typed 'no', but without requiring one."""
        try:
            pid = uuid.UUID(proposal_id)
        except ValueError:
            return {"ok": False, "reply": "That's already been handled, no need to cancel."}
        stmt = select(ChatProposal).where(ChatProposal.id == pid, ChatProposal.user_id == user.id)
        proposal = (await db.execute(stmt)).scalars().first()
        if not proposal or proposal.status != "pending":
            return {"ok": False, "reply": "That's already been handled, no need to cancel."}
        proposal.status = "cancelled"
        await db.commit()
        return {"ok": True, "reply": "No problem, cancelled."}

    async def _run_ai_turn(self, db: AsyncSession, user: User, text: str, pending: Optional[ChatProposal]) -> Dict[str, Any]:
        system_prompt = await _system_prompt(db, user, pending)
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        last_result: Optional[Dict[str, Any]] = None

        for _ in range(MAX_TOOL_STEPS):
            msg = ai_client.chat(messages, tools=TOOLS, tool_choice="auto")
            if msg is None:
                if last_result is not None:
                    return {"reply": self._plain_fallback(last_result), "action": "reply"}
                return {"reply": "Sorry, something went wrong. Please try again.", "action": "reply"}

            if not msg.tool_calls:
                return {"reply": msg.content or "Sorry, I didn't quite catch that, could you rephrase?", "action": "reply"}

            # One tool call per turn, keeps the money-confirmation flow unambiguous.
            call = msg.tool_calls[0]
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            if name in OWNER_ONLY_FUNCTIONS and user.role != "owner":
                return {"reply": "That's only available to the business owner. I can still help you record sales and expenses!", "action": "reply"}

            if name in READ_ONLY_FUNCTIONS:
                result = await self._run_read_only_tool(db, user, name, args)
                last_result = result
                messages.append({
                    "role": "assistant", "content": msg.content,
                    "tool_calls": [{"id": call.id, "type": "function", "function": {"name": name, "arguments": call.function.arguments}}],
                })
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})
                continue

            if name in PROPOSAL_FUNCTIONS:
                return await self._handle_propose(db, user, name, args, text)

            if name == "update_profile_field":
                return await self._handle_update_profile_field(db, user, args)

            if name in ("commit_sale", "commit_expense", "commit_currency_change", "commit_remove_worker"):
                # The model should never call a commit_* function directly, commits only ever
                # happen from _commit_proposal, gated on a real confirmation message. If the
                # model tries anyway, treat it as a no-op text turn rather than writing anything.
                return {"reply": msg.content or "Just to confirm first, is that right?", "action": "reply"}

            return {"reply": "Sorry, I didn't quite catch that, could you rephrase?", "action": "reply"}

        return {"reply": self._plain_fallback(last_result), "action": "reply"}

    # ─── PROPOSE handlers: compute + store a preview, never write ──────────────────────────

    async def _handle_propose(self, db: AsyncSession, user: User, name: str, args: Dict[str, Any], text: str = "") -> Dict[str, Any]:
        business_id = user.business_id or user.id

        if name == "propose_sale":
            return await self._propose_sale(db, user, business_id, args, text)
        if name == "add_product":
            return await self._propose_add_product(db, user, business_id, args, text)
        if name == "propose_expense":
            return await self._propose_expense(db, user, business_id, args)
        if name == "mark_customer_paid":
            return await self._propose_mark_customer_paid(db, user, business_id, args)
        if name == "generate_document_preview":
            return await self._propose_document(db, user, business_id, args)
        if name == "propose_currency_change":
            return await self._propose_currency_change(db, user, args)
        if name == "generate_worker_invite":
            return await self._propose_worker_invite(db, user, args)
        if name == "propose_remove_worker":
            return await self._propose_remove_worker(db, user, business_id, args)
        if name == "mark_document_paid":
            return await self._propose_mark_document_paid(db, user, business_id, args)
        if name == "send_document":
            # send_document only makes sense as the COMMIT half of a pending document proposal
            #, if there's nothing pending, there's nothing to send yet.
            return {"reply": "What would you like to invoice or send a receipt for?", "action": "reply"}

        return {"reply": "Sorry, I didn't quite catch that, could you rephrase?", "action": "reply"}

    async def _propose_sale(self, db: AsyncSession, user: User, business_id, args: Dict[str, Any], text: str = "") -> Dict[str, Any]:
        line_items = args.get("line_items") or []
        if not line_items:
            return {"reply": "What did you sell, and how much for?", "action": "reply"}

        resolved = []
        for li in line_items:
            product_name = (li.get("product_name") or "").strip()
            item = await _match_item(db, business_id, product_name) if product_name else None
            qty = float(li.get("quantity") or 1)
            unit_price = li.get("unit_price")
            line_total = li.get("line_total")
            if line_total is None and unit_price is not None:
                line_total = float(unit_price) * qty
            resolved.append({
                "product_name": product_name, "item_id": str(item.id) if item else None,
                "matched": item is not None, "is_service": bool(item.is_service) if item else False,
                "quantity": qty, "line_total": float(line_total) if line_total is not None else None,
            })

        unmatched = [r for r in resolved if not r["matched"]]
        if unmatched and any(r["line_total"] for r in resolved):
            names = ", ".join(r["product_name"] for r in unmatched)
            preview = f"I don't have \"{names}\" in your products yet. Want me to add it? If you know what you paid for it, mention that too, otherwise just say yes."
            # Persisted (as "incomplete" so a bare "yes" never auto-commits it, that "yes"
            # answers this question, not "record the sale") so the sale itself isn't lost once
            # the product gets added, see _commit_add_product, which resumes from exactly this,
            # replaying trigger_text (this original message, NOT whatever short reply, "yes" —
            # ends up being the one that actually invokes add_product a turn or two later).
            proposal = await _create_proposal(db, user, "propose_sale_incomplete", {"line_items": resolved, "payment_type": args.get("payment_type", "cash"), "customer_name": args.get("customer_name"), "trigger_text": text}, preview)
            # Platform-wide button rule (2026-09-22): this is a genuine yes/no question ("want me
            # to add it?"), so it gets the same confirm/cancel button pair as everything else,
            # not just plain text -- typed "yes" still works too, see the dedicated handling in
            # handle_message for _auto_add_unmatched_products.
            return {"reply": preview, "action": "confirm", "proposal_id": str(proposal.id)}

        missing_amount = [r for r in resolved if r["line_total"] is None]
        if missing_amount:
            item_desc = ", ".join(r["product_name"] for r in missing_amount)
            preview = f"Got it, {item_desc}. How much in total?"
            # Persisted (incomplete) so it shows up in Conversation State on the next turn —
            # that's what lets a bare follow-up amount get merged back into this sale.
            await _create_proposal(db, user, "propose_sale_incomplete", {"line_items": resolved, "payment_type": args.get("payment_type", "cash"), "customer_name": args.get("customer_name")}, preview)
            return {
                "reply": preview, "action": "need_amount",
                "draft": {"type": "sale", "description": item_desc, "amount": 0, "quantity": resolved[0]["quantity"] if resolved else 1},
            }

        payment_type = args.get("payment_type", "cash")
        customer_name = args.get("customer_name")
        discount = args.get("discount_amount")
        return await self._finalize_sale_proposal(db, user, resolved, payment_type, customer_name, discount, as_card=True)

    async def _finalize_sale_proposal(
        self, db: AsyncSession, user: User, resolved: List[Dict[str, Any]],
        payment_type: str, customer_name: Optional[str], discount: Optional[float], as_card: bool,
        prefix: str = "",
    ) -> Dict[str, Any]:
        """Builds the preview + stored proposal for a fully-resolved sale (every line item
        matched to the catalog with a known total), shared by a normal propose_sale call and
        by _commit_add_product resuming a sale that was waiting on a new product."""
        currency = user.currency
        total = sum(r["line_total"] for r in resolved)
        if discount:
            total = max(0.0, total - float(discount))

        desc = ", ".join(f"{r['product_name']}" + (f" x{r['quantity']:g}" if r["quantity"] != 1 else "") for r in resolved)
        preview = f"Sale: {desc}, total {_fmt(currency, total)}"
        if payment_type == "credit" and customer_name:
            preview += f", on credit to {customer_name}"
        preview += ". Ready to record?"

        payload = {"line_items": resolved, "total": total, "payment_type": payment_type, "customer_name": customer_name}
        proposal = await _create_proposal(db, user, "propose_sale", payload, preview)
        draft = {"type": "sale", "description": desc, "amount": total, "quantity": resolved[0]["quantity"] if len(resolved) == 1 else 1}

        if as_card:
            return {"reply": None, "action": "confirm_sale", "draft": draft, "proposal_id": str(proposal.id)}
        # Platform-wide button rule (2026-09-22): "Ready to record?" is itself a yes/no question
        # (this path runs when a sale resumes right after a brand-new product just got added), so
        # it gets the same button treatment as everything else -- the resulting proposal is a
        # normal "propose_sale", so tapping Yes on this card commits through the usual sale path.
        return {"reply": f"{prefix}{preview}", "action": "confirm", "proposal_id": str(proposal.id)}

    async def _auto_add_unmatched_products(self, db: AsyncSession, user: User, pending: ChatProposal) -> Optional[Dict[str, Any]]:
        """Deterministic app-code handling of 'yes' to 'want me to add this product?', see the
        call site in handle_message for why this doesn't go through the model."""
        business_id = pending.business_id
        resolved = pending.payload.get("line_items") or []
        added_names = []
        for r in resolved:
            if r["matched"]:
                continue
            item = Item(
                business_id=business_id, user_id=user.id, name=r["product_name"],
                unit_price=Decimal(str(r["line_total"] / r["quantity"])) if r.get("line_total") and r.get("quantity") else None,
                stock_level=Decimal(0), is_service=False,
            )
            db.add(item)
            await db.flush()
            r["matched"] = True
            r["item_id"] = str(item.id)
            r["is_service"] = False
            added_names.append(r["product_name"])

        prefix = "Added " + ", ".join(f'"{n}"' for n in added_names) + " to your products. " if added_names else ""

        if any(r["line_total"] is None for r in resolved):
            item_desc = ", ".join(r["product_name"] for r in resolved if r["line_total"] is None)
            preview = f"{prefix}How much in total?"
            await _create_proposal(db, user, "propose_sale_incomplete", {"line_items": resolved, "payment_type": pending.payload.get("payment_type", "cash"), "customer_name": pending.payload.get("customer_name")}, preview)
            return {
                "reply": preview, "action": "need_amount",
                "draft": {"type": "sale", "description": item_desc, "amount": 0, "quantity": resolved[0]["quantity"] if resolved else 1},
            }

        return await self._finalize_sale_proposal(
            db, user, resolved, pending.payload.get("payment_type", "cash"), pending.payload.get("customer_name"),
            None, as_card=False, prefix=prefix,
        )

    async def _propose_add_product(self, db: AsyncSession, user: User, business_id, args: Dict[str, Any], text: str = "") -> Dict[str, Any]:
        name = (args.get("name") or "").strip()
        if not name:
            return {"reply": "What's the product called?", "action": "reply"}
        is_service = bool(args.get("is_service"))
        selling_price = args.get("selling_price")
        preview = f"Add \"{name}\" to your products" + (f" at {_fmt(user.currency, selling_price)}" if selling_price else "") + "?"
        # trigger_text lets _commit_add_product replay the original sale message once the
        # product exists. If a propose_sale_incomplete proposal is what's actually pending right
        # now (the usual path: propose_sale asked to add the product, and THIS call is answering
        # that), its own trigger_text is the real original message, "sold 2 sodas for 6000",
        # not whatever short reply ("yes") happened to be what invoked add_product just now.
        pending = await _get_pending_proposal(db, user.id)
        if pending and pending.function_name == "propose_sale_incomplete" and pending.payload.get("trigger_text"):
            trigger_text = pending.payload["trigger_text"]
        else:
            trigger_text = text
        payload = {"name": name, "is_service": is_service, "selling_price": selling_price, "trigger_text": trigger_text}
        proposal = await _create_proposal(db, user, "add_product", payload, preview)
        return {"reply": preview, "action": "confirm", "proposal_id": str(proposal.id)}

    async def _propose_expense(self, db: AsyncSession, user: User, business_id, args: Dict[str, Any]) -> Dict[str, Any]:
        description = (args.get("description") or "expense").strip()
        amount = args.get("amount")
        category = args.get("category") or "Other"
        if not amount:
            preview = f"Got it, {description}. How much was it?"
            await _create_proposal(db, user, "propose_expense_incomplete", {"description": description, "category": category}, preview)
            return {
                "reply": preview, "action": "need_amount",
                "draft": {"type": "expense", "description": description, "amount": 0, "quantity": 1, "category": category},
            }
        preview = f"Expense: {description}, {_fmt(user.currency, amount)} ({category}). Recording it?"
        payload = {"description": description, "amount": float(amount), "category": category}
        proposal = await _create_proposal(db, user, "propose_expense", payload, preview)
        draft = {"type": "expense", "description": description, "amount": float(amount), "quantity": 1, "category": category}
        return {"reply": None, "action": "confirm_expense", "draft": draft, "proposal_id": str(proposal.id)}

    async def _propose_mark_customer_paid(self, db: AsyncSession, user: User, business_id, args: Dict[str, Any]) -> Dict[str, Any]:
        customer_name = (args.get("customer_name") or "").strip()
        if not customer_name:
            return {"reply": "Which customer?", "action": "reply"}
        stmt = select(Customer).where(Customer.business_id == business_id, func.lower(Customer.name) == customer_name.lower())
        customer = (await db.execute(stmt)).scalars().first()
        if not customer or customer.outstanding_balance <= 0:
            return {"reply": f"I don't have an outstanding balance on record for {customer_name}.", "action": "reply"}
        amount = args.get("amount")
        pay_amount = float(amount) if amount else float(customer.outstanding_balance)
        preview = f"{customer_name} currently owes {_fmt(user.currency, customer.outstanding_balance)}. Mark {_fmt(user.currency, pay_amount)} as paid now?"
        payload = {"customer_id": str(customer.id), "amount": pay_amount}
        proposal = await _create_proposal(db, user, "mark_customer_paid", payload, preview)
        return {"reply": preview, "action": "confirm", "proposal_id": str(proposal.id)}

    async def _propose_document(self, db: AsyncSession, user: User, business_id, args: Dict[str, Any]) -> Dict[str, Any]:
        customer_name = (args.get("customer_name") or "").strip() or "Customer"
        already_paid = bool(args.get("already_paid"))
        items = args.get("items")
        if not items:
            raw_text = args.get("raw_text") or customer_name
            parsed = await invoice_parser.parse_invoice_text(raw_text, currency=user.currency)
            items = parsed.get("items", [])
            if parsed.get("customer_name") and parsed["customer_name"] != "Customer":
                customer_name = parsed["customer_name"]
        if not items:
            return {"reply": "What are they buying, and for how much?", "action": "reply"}

        total = sum(float(i.get("quantity", 1)) * float(i.get("unit_price", 0)) for i in items)
        doc_word = "Receipt" if already_paid else "Invoice"
        item_desc = ", ".join(f"{i.get('description', 'item')} x{i.get('quantity', 1):g}" for i in items)
        preview = f"{doc_word} for {customer_name}, {item_desc}, total {_fmt(user.currency, total)}. Ready to send it?"
        payload = {"customer_name": customer_name, "items": items, "already_paid": already_paid, "total": total}
        proposal = await _create_proposal(db, user, "generate_document_preview", payload, preview)
        return {"reply": preview, "action": "confirm", "proposal_id": str(proposal.id)}

    async def _propose_currency_change(self, db: AsyncSession, user: User, args: Dict[str, Any]) -> Dict[str, Any]:
        new_currency = (args.get("new_currency") or "").strip().upper()
        if not new_currency:
            return {"reply": "Which currency should I switch you to?", "action": "reply"}
        preview = (
            f"Switch your business currency from {user.currency} to {new_currency}? "
            "Past figures stay recorded in the old currency and are not converted, only the "
            "display currency going forward changes. Confirm?"
        )
        proposal = await _create_proposal(db, user, "propose_currency_change", {"new_currency": new_currency}, preview)
        return {"reply": preview, "action": "confirm", "proposal_id": str(proposal.id)}

    async def _propose_worker_invite(self, db: AsyncSession, user: User, args: Dict[str, Any]) -> Dict[str, Any]:
        phone = (args.get("worker_phone_number") or "").strip()
        if not phone:
            return {"reply": "What's their phone number? I'll generate an invite code valid for 7 days.", "action": "reply"}
        preview = f"Generate a 7-day invite code for {phone}?"
        proposal = await _create_proposal(db, user, "generate_worker_invite", {"worker_phone_number": phone}, preview)
        return {"reply": preview, "action": "confirm", "proposal_id": str(proposal.id)}

    async def _propose_remove_worker(self, db: AsyncSession, user: User, business_id, args: Dict[str, Any]) -> Dict[str, Any]:
        phone = (args.get("worker_phone_number") or "").strip()
        stmt = select(User).where(User.business_id == business_id, User.role == "worker", User.phone_number == phone)
        worker = (await db.execute(stmt)).scalars().first()
        if not worker:
            return {"reply": f"I couldn't find a worker with the number {phone} on this business.", "action": "reply"}
        preview = f"Remove {phone}'s access to this business? They'll keep their own login but lose access to this business's data."
        proposal = await _create_proposal(db, user, "propose_remove_worker", {"worker_id": str(worker.id), "phone": phone}, preview)
        return {"reply": preview, "action": "confirm", "proposal_id": str(proposal.id)}

    async def _propose_mark_document_paid(self, db: AsyncSession, user: User, business_id, args: Dict[str, Any]) -> Dict[str, Any]:
        customer_name = (args.get("customer_name") or "").strip()
        stmt = (
            select(Invoice)
            .where(Invoice.business_id == business_id, Invoice.status != InvoiceStatus.PAID,
                   func.lower(Invoice.customer_name) == customer_name.lower())
            .order_by(Invoice.created_at.desc())
        )
        invoice = (await db.execute(stmt)).scalars().first()
        if not invoice:
            return {"reply": f"I don't have an unpaid invoice on record for {customer_name}.", "action": "reply"}
        preview = f"Mark invoice {invoice.invoice_number} for {customer_name} ({_fmt(invoice.currency, invoice.total_amount)}) as paid?"
        proposal = await _create_proposal(db, user, "mark_document_paid", {"invoice_id": str(invoice.id)}, preview)
        return {"reply": preview, "action": "confirm", "proposal_id": str(proposal.id)}

    async def _handle_update_profile_field(self, db: AsyncSession, user: User, args: Dict[str, Any]) -> Dict[str, Any]:
        field = args.get("field")
        value = (args.get("value") or "").strip()
        if field not in ("name", "type") or not value:
            return {"reply": "What would you like to change it to?", "action": "reply"}
        column = "business_name" if field == "name" else "business_type"
        previous = getattr(user, column)
        setattr(user, column, value)
        await db.commit()
        self._last_profile_edit[str(user.id)] = {"column": column, "previous": previous}
        return {"reply": f"Done, your business {'name' if field == 'name' else 'type'} is now {value}. Anything else?", "action": "reply"}

    async def _handle_undo(self, db: AsyncSession, user: User) -> Dict[str, Any]:
        edit = self._last_profile_edit.pop(str(user.id), None)
        if not edit:
            return {"reply": "There's nothing from this conversation to undo.", "action": "reply"}
        setattr(user, edit["column"], edit["previous"])
        await db.commit()
        return {"reply": "Undone.", "action": "reply"}

    # ─── COMMIT: only ever reached after a verified, real confirmation message ──────────────

    async def _commit_proposal(self, db: AsyncSession, user: User, proposal: ChatProposal) -> Dict[str, Any]:
        proposal.status = "committed"
        name = proposal.function_name
        payload = proposal.payload
        business_id = proposal.business_id

        try:
            if name == "propose_sale":
                reply = await self._commit_sale(db, user, business_id, payload)
            elif name == "add_product":
                reply = await self._commit_add_product(db, user, business_id, payload)
            elif name == "propose_expense":
                reply = await self._commit_expense(db, user, business_id, payload)
            elif name == "mark_customer_paid":
                reply = await self._commit_mark_customer_paid(db, payload)
            elif name == "generate_document_preview":
                reply = await self._commit_document(db, user, business_id, payload)
            elif name == "propose_currency_change":
                reply = await self._commit_currency_change(db, user, payload)
            elif name == "generate_worker_invite":
                reply = await self._commit_worker_invite(db, user, payload)
            elif name == "propose_remove_worker":
                reply = await self._commit_remove_worker(db, payload)
            elif name == "mark_document_paid":
                reply = await self._commit_mark_document_paid(db, payload)
            else:
                reply = "Done."
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception(f"Commit failed for proposal {proposal.id} ({name})")
            return {"reply": "Sorry, something went wrong saving that. Please try again.", "action": "reply"}

        # _commit_add_product returns a full response dict (not just a string) when it resumes
        # a sale that was waiting on this product, pass that straight through.
        if isinstance(reply, dict):
            return reply
        return {"reply": reply, "action": "reply"}

    async def _commit_sale(self, db: AsyncSession, user: User, business_id, payload: Dict[str, Any]) -> str:
        total = Decimal(str(payload["total"]))
        line_items = payload["line_items"]
        desc = ", ".join(li["product_name"] for li in line_items)
        first_item_id = None

        for li in line_items:
            if not li.get("item_id"):
                continue
            item_stmt = select(Item).where(Item.id == uuid.UUID(li["item_id"]))
            item = (await db.execute(item_stmt)).scalars().first()
            if item and not item.is_service:
                item.stock_level = (item.stock_level or Decimal(0)) - Decimal(str(li["quantity"]))
            if first_item_id is None:
                first_item_id = item.id if item else None

        transaction = Transaction(
            user_id=user.id, business_id=business_id, item_id=first_item_id,
            type=TransactionType.SALE, amount=total, currency=user.currency,
            description=desc, category="Sales Revenue", quantity=Decimal(str(line_items[0]["quantity"])),
        )
        db.add(transaction)

        if payload.get("payment_type") == "credit" and payload.get("customer_name"):
            customer = await _find_or_create_customer(db, business_id, payload["customer_name"])
            customer.outstanding_balance = (customer.outstanding_balance or Decimal(0)) + total

        return f"Recorded. {desc}, {_fmt(user.currency, total)}."

    async def _commit_add_product(self, db: AsyncSession, user: User, business_id, payload: Dict[str, Any]) -> Any:
        item = Item(
            business_id=business_id, user_id=user.id, name=payload["name"],
            unit_price=Decimal(str(payload["selling_price"])) if payload.get("selling_price") else None,
            stock_level=Decimal(0), is_service=payload.get("is_service", False),
        )
        db.add(item)
        await db.flush()
        added_line = f"Added \"{payload['name']}\" to your products."

        # If this product was added mid-sale (Volume 5's flagship flow), pick that sale back up
        # now that the product exists, instead of leaving it dropped on the floor, the model
        # sometimes proposes the sale first (which we'd have stored as a pending incomplete
        # proposal) and sometimes reaches for add_product directly with no sale proposed at all,
        # so the most reliable way to cover both is to just replay the original message: the
        # item this just flushed is visible to that fresh turn's product-context lookup.
        trigger_text = (payload.get("trigger_text") or "").strip()
        if trigger_text:
            resumed = await self._run_ai_turn(db, user, trigger_text, None)
            if resumed.get("reply"):
                resumed["reply"] = f"{added_line} {resumed['reply']}"
            return resumed
        return added_line

    async def _commit_expense(self, db: AsyncSession, user: User, business_id, payload: Dict[str, Any]) -> str:
        transaction = Transaction(
            user_id=user.id, business_id=business_id, type=TransactionType.EXPENSE,
            amount=Decimal(str(payload["amount"])), currency=user.currency,
            description=payload["description"], category=payload["category"], quantity=Decimal(1),
        )
        db.add(transaction)
        return f"Recorded. {payload['description']}, {_fmt(user.currency, payload['amount'])} ({payload['category']})."

    async def _commit_mark_customer_paid(self, db: AsyncSession, payload: Dict[str, Any]) -> str:
        stmt = select(Customer).where(Customer.id == uuid.UUID(payload["customer_id"]))
        customer = (await db.execute(stmt)).scalars().first()
        if not customer:
            return "That customer no longer exists."
        customer.outstanding_balance = max(Decimal(0), (customer.outstanding_balance or Decimal(0)) - Decimal(str(payload["amount"])))
        return f"Marked {_fmt('', payload['amount']).strip()} as paid for {customer.name}."

    async def _commit_document(self, db: AsyncSession, user: User, business_id, payload: Dict[str, Any]) -> str:
        from app.api.api_v1.endpoints.invoices import _next_invoice_number, _build_items
        items = _build_items(payload["items"])
        total = sum((i.total_price for i in items), Decimal(0))
        invoice = Invoice(
            business_id=business_id, created_by=user.id,
            invoice_number=await _next_invoice_number(db, business_id),
            customer_name=payload["customer_name"],
            status=InvoiceStatus.PAID if payload.get("already_paid") else InvoiceStatus.DRAFT,
            template=user.receipt_template, total_amount=total, currency=user.currency, items=items,
        )
        db.add(invoice)
        await db.flush()
        doc_word = "Receipt" if payload.get("already_paid") else "Invoice"
        return (
            f"{doc_word} {invoice.invoice_number} created for {invoice.customer_name}, "
            f"total {_fmt(user.currency, total)}. You can view, download, or share it anytime from Invoices."
        )

    async def _commit_currency_change(self, db: AsyncSession, user: User, payload: Dict[str, Any]) -> str:
        old = user.currency
        user.currency = payload["new_currency"]
        return f"Done, your currency is now {payload['new_currency']} (was {old}). Past figures stay in {old}."

    async def _commit_worker_invite(self, db: AsyncSession, user: User, payload: Dict[str, Any]) -> str:
        import random
        code = f"{random.randint(0, 999999):06d}"
        invite = Invite(
            code=code, business_id=user.business_id or user.id, created_by=user.id,
            phone_number=payload["worker_phone_number"], used=False,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.add(invite)
        return f"Invite code {code} generated for {payload['worker_phone_number']}, valid for 7 days."

    async def _commit_remove_worker(self, db: AsyncSession, payload: Dict[str, Any]) -> str:
        stmt = select(User).where(User.id == uuid.UUID(payload["worker_id"]))
        worker = (await db.execute(stmt)).scalars().first()
        if not worker:
            return "That worker no longer exists."
        # Detach rather than delete: the worker keeps their own login but loses access to this
        # business's data, becoming the owner of their own (now empty) business.
        worker.business_id = worker.id
        worker.role = "owner"
        return f"Removed {payload['phone']}'s access to this business."

    async def _commit_mark_document_paid(self, db: AsyncSession, payload: Dict[str, Any]) -> str:
        stmt = select(Invoice).where(Invoice.id == uuid.UUID(payload["invoice_id"]))
        invoice = (await db.execute(stmt)).scalars().first()
        if not invoice:
            return "That invoice no longer exists."
        invoice.status = InvoiceStatus.PAID
        return f"Marked invoice {invoice.invoice_number} for {invoice.customer_name} as paid."

    # ─── Read-only (L1) tools ────────────────────────────────────────────────────────────────

    async def _run_read_only_tool(self, db: AsyncSession, user: User, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        business_id = user.business_id or user.id
        if name == "get_report_summary":
            now = datetime.utcnow()
            period = args.get("period", "today")
            start, end = self._bounds(period, now, args.get("start_date"), args.get("end_date"))
            total_sales = await self._sum_by_type(db, business_id, TransactionType.SALE, start, end)
            total_expenses = await self._sum_by_type(db, business_id, TransactionType.EXPENSE, start, end)
            return {
                "period": period, "currency": user.currency,
                "total_sales": float(total_sales), "total_expenses": float(total_expenses),
                "net_profit": float(total_sales - total_expenses),
            }
        if name == "get_recent_activity":
            days = args.get("days") or 7
            if user.role == "worker":
                days = min(days, 7)
            since = datetime.utcnow() - timedelta(days=days)
            stmt = select(Transaction).where(
                Transaction.business_id == business_id, Transaction.transaction_date >= since,
            ).order_by(Transaction.transaction_date.desc()).limit(50)
            rows = (await db.execute(stmt)).scalars().all()
            return {"activity": [
                {"type": t.type.value, "description": t.description, "amount": float(t.amount), "date": t.transaction_date.isoformat()}
                for t in rows
            ]}
        if name == "get_inventory":
            stmt = select(Item).where(Item.business_id == business_id)
            item_name = args.get("item_name")
            if item_name:
                stmt = stmt.where(Item.name.ilike(f"%{item_name}%"))
            rows = (await db.execute(stmt)).scalars().all()
            return {"items": [{"name": i.name, "stock_level": float(i.stock_level or 0), "unit_price": float(i.unit_price or 0)} for i in rows]}
        # list_low_stock
        stmt = select(Item).where(Item.business_id == business_id, Item.stock_level > 0, Item.stock_level <= LOW_STOCK_THRESHOLD)
        rows = (await db.execute(stmt)).scalars().all()
        return {"low_stock_items": [{"name": i.name, "stock_level": float(i.stock_level or 0)} for i in rows]}

    def _bounds(self, period: str, now: datetime, start_date: Optional[str], end_date: Optional[str]):
        if period == "custom" and start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date) + timedelta(days=1)
                return start, end
            except ValueError:
                pass
        if period == "this_week":
            return now - timedelta(days=7), now
        if period == "this_month":
            return now - timedelta(days=30), now
        return now.replace(hour=0, minute=0, second=0, microsecond=0), now

    async def _sum_by_type(self, db: AsyncSession, business_id, tx_type: TransactionType, start: datetime, end: datetime) -> Decimal:
        stmt = select(func.sum(Transaction.amount)).where(
            Transaction.business_id == business_id, Transaction.type == tx_type,
            Transaction.transaction_date >= start, Transaction.transaction_date <= end,
        )
        return (await db.execute(stmt)).scalar() or Decimal(0)

    def _plain_fallback(self, result: Optional[Dict[str, Any]]) -> str:
        if not result:
            return "Sorry, I couldn't find an answer to that, could you rephrase?"
        if "items" in result:
            items = result["items"]
            if not items:
                return "I couldn't find that in your stock, it may not be added yet."
            return "Here's your current stock: " + ", ".join(f"{i['name']} ({i['stock_level']:g})" for i in items)
        if "low_stock_items" in result:
            items = result["low_stock_items"]
            if not items:
                return "Nothing is running low right now, you're well stocked!"
            return "Running low on: " + ", ".join(f"{i['name']} ({i['stock_level']:g} left)" for i in items)
        if "activity" in result:
            items = result["activity"]
            if not items:
                return "No recent activity to show."
            return f"You've had {len(items)} recent transaction(s)."
        if "total_sales" in result:
            return (
                f"For {result['period']}: sales {result['currency']} {result['total_sales']:,.0f}, "
                f"expenses {result['currency']} {result['total_expenses']:,.0f}, "
                f"profit {result['currency']} {result['net_profit']:,.0f}."
            )
        return "Sorry, I couldn't find an answer to that, could you rephrase?"


chat_engine = ChatEngine()
