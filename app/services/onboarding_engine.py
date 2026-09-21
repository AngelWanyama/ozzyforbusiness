"""
Onboarding conversation engine, rebuilt against Volume 3 of the Ozzy Behaviour Intelligence
Brain (brain-spec/Ozzy_Behaviour_Intelligence_Brain_v1.md), Angel's exact wording, 2026-09-21.

This replaces a rigid, fixed-order, ten-question wizard (owner_name -> business_name ->
business_location -> ... -> template_choice) with a real conversational state machine per
§3.20: Ozzy tracks what's known, what's missing, and what's been declined on the User record
itself (User.onboarding_state), and every message the entrepreneur sends is interpreted for
every fact it might contain, not just the one field that happened to be asked last.

Design split, deliberately:
- The QUESTION TEXT for every step is the literal wording from the Brain doc (§3.3, §3.6-3.13),
  used verbatim, not model-generated. §3.9/§3.10/§3.11 in particular say "exactly as written."
- The MODEL's only job is extraction and a short, warm acknowledgment of what it understood,
  using the Brain doc's example acknowledgments as style reference, not a script. It never
  decides what gets asked next or in what order, that's owned deterministically here so a
  model having an off turn can never cause a question to go unasked or asked twice.
"""
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.user import User
from app.services.ai_client import ai_client

logger = logging.getLogger(__name__)

# Order matters: this is the priority list Ozzy falls back to for "what's the single most
# relevant missing piece" per §3.20 -- not a rigid sequence the entrepreneur is forced through
# (they can volunteer any of these in any order in a single message), just the tie-breaker for
# what Ozzy asks about next when more than one thing is still missing.
FIELD_ORDER = [
    "owner_name", "business_name", "business_description", "business_location",
    "phone_confirm", "email", "logo", "employees", "stock_items", "pricing",
]

QUESTIONS = {
    "owner_name": "What should I call you?",
    "business_name": "What's the name of your business?",
    "business_description": "Tell me a little about your business. What do you sell or what services do you offer?",
    "business_location": "And where is your business located?",
    "email": "And what email address would you like to use for your business?",
    "logo": "Does your business already have a logo?",
    "employees": "Do you have any employees you'd like to add to your business?",
    "stock_items": "What products do you have in stock right now?",
}

# §3.10 / §3.11: the exact non-blocking language when something isn't available.
EMAIL_DECLINE_REPLY = "No problem. We can leave that for now. You can add one later from your business settings."
LOGO_DECLINE_REPLY = "No problem at all. You don't need one to get started.\n\nOzzy also has a logo creation feature if you'd like to create one later. You can find it in your Settings whenever you're ready."
LOGO_HAS_ONE_REPLY = "Great. You can send it to me here and I'll add it to your business profile."
EMPLOYEES_NO_REPLY = "That's perfectly fine. You can always add employees later if your team grows."


def opening_greeting(local_hour: Optional[int]) -> str:
    """§3.3 / §3.4: a fixed template chosen by local time, never asked for directly. local_hour
    is the entrepreneur's device/browser-local hour (0-23); None means unknown/uncertain, which
    must fall back to the neutral greeting rather than guessing."""
    base = "Welcome to Ozzy for Business. I'm Ozzy, your AI business assistant. \U0001F60A"
    if local_hour is None:
        greeting = base
    elif 5 <= local_hour < 12:
        greeting = "Good morning! " + base
    elif 12 <= local_hour < 18:
        greeting = "Good afternoon! " + base
    else:
        greeting = "Good evening! " + base
    return f"{greeting}\n\nWhat should I call you?"


def resume_message(state: Dict[str, Any]) -> str:
    """§3.21: returning to unfinished onboarding never restarts from scratch."""
    known = state.get("known", {})
    name = known.get("owner_name") or "there"
    business = known.get("business_name")
    have = [label for key, label in (
        ("business_name", "your business name"), ("business_location", "location"),
        ("business_description", "what you sell"), ("stock_items", "products"),
    ) if known.get(key)]
    have_str = ""
    if have:
        if len(have) == 1:
            have_str = f" We've already got {have[0]}."
        else:
            have_str = f" We've already got {', '.join(have[:-1])} and {have[-1]}."
    business_part = f" We were setting up {business}." if business else ""
    return f"Welcome back, {name}. \U0001F60A{business_part}{have_str} Let's continue from where we stopped."


def completion_message(state: Dict[str, Any]) -> str:
    """§3.19, personalised with the real name."""
    known = state.get("known", {})
    name = known.get("owner_name") or "there"
    return (
        f"You're all set, {name}. \U0001F389\n\n"
        "I now have a better understanding of your business and how you operate.\n\n"
        "From here, you can talk to me naturally. Tell me when you make a sale, record an "
        "expense, ask about your business, check your stock, or ask me to help you understand "
        "your numbers.\n\n"
        "You don't need to know accounting. Just tell me what happened, and I'll help with the "
        "rest. \U0001F60A"
    )


def _is_known(state: Dict[str, Any], field: str) -> bool:
    known = state.get("known", {})
    declined = state.get("declined", [])
    if field in declined:
        return True  # declined counts as resolved, not missing
    if field == "employees":
        return "employees_count" in known
    if field == "stock_items":
        if state.get("is_service_business"):
            return True  # §3.13: services skip the inventory conversation entirely
        return bool(known.get("stock_items"))
    if field == "pricing":
        if state.get("is_service_business") or not known.get("stock_items"):
            return True
        return all(item.get("selling_price") is not None for item in known.get("stock_items", []))
    if field == "logo":
        return "logo_status" in known
    return known.get(field) not in (None, "")


def next_missing_field(state: Dict[str, Any]) -> Optional[str]:
    for field in FIELD_ORDER:
        if not _is_known(state, field):
            return field
    return None


def question_for(field: str, state: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Returns {text, kind, choices?} for a given field -- most are plain text, phone_confirm and
    logo are the two places a button genuinely earns its place (Volume 2), matching what's
    already built in the frontend for them."""
    if field == "phone_confirm":
        phone = user.phone_number
        return {
            "kind": "choice", "text": f"I see you're using this phone number to access Ozzy ({phone}). Would you like to continue using this number for your business, or would you like to use a different one?",
            "choices": [{"label": "Use this number", "value": "same"}, {"label": "Use a different one", "value": "different"}],
        }
    if field == "logo":
        return {
            "kind": "logo", "text": QUESTIONS["logo"],
            "choices": [{"label": "I have one", "value": "has_one"}, {"label": "I don't have one yet", "value": "none"}],
        }
    if field == "pricing":
        known = state.get("known", {})
        item = next((i for i in known.get("stock_items", []) if i.get("selling_price") is None), None)
        name = item["name"] if item else "that product"
        return {"kind": "text", "text": f"How much do you normally buy {name} for, and how much do you sell it for?"}
    return {"kind": "text", "text": QUESTIONS[field]}


TOOLS = [{
    "type": "function",
    "function": {
        "name": "extract_onboarding_facts",
        "description": "Pull out every onboarding fact present in the entrepreneur's message, however it's phrased, and write a short acknowledgment.",
        "parameters": {
            "type": "object",
            "properties": {
                "owner_name": {"type": "string", "description": "Just the name itself, e.g. 'My name is Angel' -> 'Angel'. Omit if not present."},
                "business_name": {"type": "string", "description": "Omit if not present."},
                "business_description": {"type": "string", "description": "A short description of what they sell/do, in their own words. Omit if not present."},
                "products_mentioned": {"type": "array", "items": {"type": "string"}, "description": "Product or service names mentioned, e.g. ['dresses', 'shoes']. Omit if none."},
                "is_service_business": {"type": "boolean", "description": "True if this is clearly a services business (no physical stock to track), false if clearly physical products, omit if unclear."},
                "business_location": {"type": "string", "description": "Omit if not present."},
                "employees_count": {"type": "number", "description": "How many employees, 0 if they say they have none. Omit if not mentioned."},
                "email": {"type": "string", "description": "An email address, only if one was actually given."},
                "email_declined": {"type": "boolean", "description": "True if they said they don't have one / want to skip."},
                "stock_items": {
                    "type": "array", "description": "Products currently in stock, with quantity and/or price if given.",
                    "items": {"type": "object", "properties": {
                        "name": {"type": "string"}, "quantity": {"type": "number"},
                        "buying_price": {"type": "number"}, "selling_price": {"type": "number"},
                    }, "required": ["name"]},
                },
                "stock_declined": {"type": "boolean", "description": "True if they said they'll add stock later / want to skip this."},
                "off_topic": {"type": "boolean", "description": "True if this message doesn't answer or relate to onboarding at all (a question back to Ozzy, small talk, confusion)."},
                "acknowledgment": {
                    "type": "string",
                    "description": (
                        "ONE short, warm sentence (or two) acknowledging what you understood, in Ozzy's "
                        "own voice, e.g. \"It's lovely to meet you, Sarah.\" or \"I like that name.\" or "
                        "\"Got it, dresses and shoes.\" If off_topic, respond briefly and genuinely to "
                        "what they actually said instead. Do NOT ask a question here, that's handled "
                        "separately. No em dashes. Never say 'bookkeeping' or 'accounting'. Never sound "
                        "robotic, bureaucratic, clinical, condescending, or overly formal."
                    ),
                },
            },
            "required": ["acknowledgment"],
        },
    },
}]


def _known_summary(state: Dict[str, Any]) -> str:
    known = state.get("known", {})
    if not known:
        return "Nothing yet."
    parts = []
    for k, v in known.items():
        if v not in (None, "", []):
            parts.append(f"{k}: {v}")
    return "; ".join(parts) if parts else "Nothing yet."


async def interpret_onboarding_message(user: User, state: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Returns the updated state plus what Ozzy should say. Never called for the phone/logo
    button choices, those are handled deterministically by the caller."""
    if not ai_client.is_available:
        return {"state": state, "reply": "Sorry, I can't understand messages right now, the AI service isn't configured. Please try again shortly.", "done": False}

    target = next_missing_field(state)
    system_prompt = (
        "IDENTITY: You are Ozzy, warm, friendly, calm, patient, encouraging, respectful, helpful, "
        "human, non-judgmental. Never robotic, bureaucratic, clinical, condescending, overly "
        "formal, or like a financial institution asking compliance questions. Never say "
        "\"bookkeeping\" or \"accounting\". Never use an em dash, use a comma or a period instead. "
        "Plain, everyday language.\n\n"
        "You are getting to know a new business owner during onboarding, building understanding "
        "through conversation, not collecting registration data. Extract every fact the message "
        f"actually contains, however it's phrased. What's already known: {_known_summary(state)}. "
        f"You most recently asked about: {target or 'nothing specific'}. Never re-extract or "
        "contradict something already known unless the entrepreneur is clearly correcting it."
    )
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
    msg = ai_client.chat(messages, tools=TOOLS, tool_choice="required")
    if msg is None or not msg.tool_calls:
        return {"state": state, "reply": "Sorry, I didn't quite catch that.", "done": False}

    try:
        args = json.loads(msg.tool_calls[0].function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}

    known = dict(state.get("known", {}))
    declined = list(state.get("declined", []))
    is_service = state.get("is_service_business")

    if not args.get("off_topic"):
        for field in ("owner_name", "business_name", "business_description", "business_location", "email"):
            if args.get(field):
                known[field] = args[field]
        if args.get("products_mentioned"):
            known["products_mentioned"] = args["products_mentioned"]
        if args.get("employees_count") is not None:
            known["employees_count"] = args["employees_count"]
        if args.get("is_service_business") is not None:
            is_service = args["is_service_business"]
        if args.get("email_declined"):
            declined.append("email")
        if args.get("stock_declined"):
            declined.append("stock_items")
            declined.append("pricing")
        if args.get("stock_items"):
            existing = {i["name"].lower(): i for i in known.get("stock_items", [])}
            for item in args["stock_items"]:
                name_key = item["name"].lower()
                merged = {**existing.get(name_key, {}), **{k: v for k, v in item.items() if v is not None}}
                existing[name_key] = merged
            known["stock_items"] = list(existing.values())

    state = {"known": known, "declined": list(dict.fromkeys(declined)), "is_service_business": is_service}
    acknowledgment = (args.get("acknowledgment") or "").strip()

    nxt = next_missing_field(state)
    if nxt is None:
        reply = f"{acknowledgment}\n\n{completion_message(state)}" if acknowledgment else completion_message(state)
        return {"state": state, "reply": reply, "done": True}

    q = question_for(nxt, state, user)
    reply = f"{acknowledgment}\n\n{q['text']}" if acknowledgment else q["text"]
    return {"state": state, "reply": reply, "done": False, "next_field": nxt, "kind": q["kind"], "choices": q.get("choices")}


def _advance(state: Dict[str, Any], user: User, prefix: str = "") -> Dict[str, Any]:
    """Shared tail end for the deterministic choice/capture paths: move to whatever's next."""
    nxt = next_missing_field(state)
    if nxt is None:
        reply = f"{prefix}{completion_message(state)}" if prefix else completion_message(state)
        return {"state": state, "reply": reply, "done": True}
    q = question_for(nxt, state, user)
    reply = f"{prefix}{q['text']}" if prefix else q["text"]
    return {"state": state, "reply": reply, "done": False, "next_field": nxt, "kind": q["kind"], "choices": q.get("choices")}


def handle_onboarding_choice(user: User, state: Dict[str, Any], field: str, value: str) -> Dict[str, Any]:
    """The two button-driven steps, §3.9 (phone) and §3.11 (logo) -- deterministic, no model call."""
    known = dict(state.get("known", {}))
    declined = list(state.get("declined", []))

    if field == "phone_confirm":
        if value == "same":
            known["phone_confirm"] = "same"
            state = {**state, "known": known}
            return _advance(state, user)
        # "different": stay on this question until the actual number is captured as free text.
        state = {**state, "known": known, "awaiting": "contact_phone_text"}
        return {"state": state, "reply": "What number should we use instead?", "done": False, "next_field": "phone_confirm", "kind": "text"}

    if field == "logo":
        if value == "has_one":
            state = {**state, "known": known, "awaiting": "logo_upload"}
            return {"state": state, "reply": LOGO_HAS_ONE_REPLY, "done": False, "next_field": "logo", "kind": "logo_upload"}
        if value == "uploaded":
            known["logo_status"] = "uploaded"
            state = {**state, "known": known, "awaiting": None}
            return _advance(state, user)
        # "none"
        declined.append("logo")
        state = {**state, "known": known, "declined": declined, "awaiting": None}
        return _advance(state, user, prefix=f"{LOGO_DECLINE_REPLY}\n\n")

    return _advance(state, user)


def handle_awaiting_capture(user: User, state: Dict[str, Any], text: str) -> Optional[Dict[str, Any]]:
    """If the previous turn left something specific pending (the actual phone number after
    choosing 'different'), the next plain message is captured directly rather than run through
    general extraction. Returns None if nothing was pending."""
    awaiting = state.get("awaiting")
    if awaiting != "contact_phone_text":
        return None
    known = dict(state.get("known", {}))
    known["contact_phone"] = text.strip()
    known["phone_confirm"] = "different"
    state = {**state, "known": known, "awaiting": None}
    return _advance(state, user)


async def finalize_onboarding(db: AsyncSession, user: User, state: Dict[str, Any]) -> None:
    """Writes everything gathered in conversation onto the real profile fields and product
    catalog, once onboarding actually reaches §3.19. Buying price is kept in onboarding_state
    only, not persisted onto Item -- there's no buying_price column on the catalog yet, so it's
    captured faithfully in conversation without silently inventing a place to store it."""
    known = state.get("known", {})
    if known.get("owner_name"):
        user.owner_name = known["owner_name"]
    if known.get("business_name"):
        user.business_name = known["business_name"]
    if known.get("business_description"):
        user.business_description = known["business_description"]
    if known.get("business_location"):
        user.business_location = known["business_location"]
    if known.get("email"):
        user.email = known["email"]
    if known.get("contact_phone"):
        user.contact_phone = known["contact_phone"]

    business_id = user.business_id or user.id
    for item in known.get("stock_items", []):
        name = (item.get("name") or "").strip()
        if not name:
            continue
        stmt = select(Item).where(Item.business_id == business_id, Item.name.ilike(name))
        existing = (await db.execute(stmt)).scalars().first()
        selling_price = item.get("selling_price")
        quantity = item.get("quantity")
        if existing:
            if selling_price is not None:
                existing.unit_price = Decimal(str(selling_price))
            if quantity is not None:
                existing.stock_level = Decimal(str(quantity))
        else:
            db.add(Item(
                business_id=business_id, user_id=user.id, name=name,
                unit_price=Decimal(str(selling_price)) if selling_price is not None else None,
                stock_level=Decimal(str(quantity)) if quantity is not None else Decimal(0),
                is_service=bool(state.get("is_service_business")),
            ))

    user.onboarding_completed = True
    user.onboarding_state = state
    await db.commit()
