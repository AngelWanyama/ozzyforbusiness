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
import re
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
    if field == "business_description":
        # A plain product/service list genuinely answers "what do you sell or what services do
        # you offer" -- the model doesn't reliably classify a bare list as a "description" too
        # (confirmed live: gpt-4o-mini regularly extracts products_mentioned alone for a message
        # like "I sell shoes and bags"), so don't make the entrepreneur repeat themselves just
        # because the model filed it under a different field name.
        return bool(known.get("business_description")) or bool(known.get("products_mentioned"))
    return known.get(field) not in (None, "")


def next_missing_field(state: Dict[str, Any]) -> Optional[str]:
    for field in FIELD_ORDER:
        if not _is_known(state, field):
            return field
    return None


def question_for(field: str, state: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Returns {text, kind, choices?} for a given field. Platform-wide rule (2026-09-22): any
    question with a genuine yes/no answer shows a button pair, matching phone_confirm/logo's
    existing style -- a button is always the easy, obvious path, typed language is still a full
    equal alternative (see handle_onboarding_choice and the model's own extraction for each)."""
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
    if field == "email":
        return {
            "kind": "choice", "text": QUESTIONS["email"],
            "choices": [{"label": "Add an email", "value": "add"}, {"label": "Just my phone is fine", "value": "skip"}],
        }
    if field == "employees":
        return {
            "kind": "choice", "text": QUESTIONS["employees"],
            "choices": [{"label": "Yes", "value": "yes"}, {"label": "Not right now", "value": "no"}],
        }
    if field == "stock_items":
        # Design gap fixed 2026-09-23: this used to be a required inline question with no way to
        # defer, per the bug report. Now offered as a choice first, matching the platform-wide
        # button rule -- "later" is handled in handle_onboarding_choice exactly like declining
        # logo/email, "now" falls straight through to the free-text question below.
        return {
            "kind": "choice", "text": "Would you like to set up your stock now, or add products as you go?",
            "choices": [{"label": "Set it up now", "value": "now"}, {"label": "I'll add products as I go", "value": "later"}],
        }
    if field == "pricing":
        known = state.get("known", {})
        item = next((i for i in known.get("stock_items", []) if i.get("selling_price") is None), None)
        name = item["name"] if item else "that product"
        return {"kind": "text", "text": f"How much do you normally buy {name} for, and how much do you sell it for?"}
    return {"kind": "text", "text": QUESTIONS[field]}


# strict structured-outputs mode: every property listed in "properties" MUST appear in
# "required" and every object (including nested ones) MUST set "additionalProperties": false.
# A field that's genuinely optional is expressed via a nullable type (["string", "null"]), not
# by leaving it out of "required" -- that's what makes strict mode different from a normal
# schema. This is the fix for a real, confirmed failure mode: without "strict": True, a plain
# OpenAI function-calling schema's "required" list is advisory only, and gpt-4o-mini was
# regularly omitting the "response" key from its tool call entirely (not empty -- the key
# genuinely absent from the JSON), silently falling back to a generic "Got it." with zero real
# engagement. Strict mode makes the API itself guarantee the key exists on every single call.
TOOLS = [{
    "type": "function",
    "function": {
        "name": "extract_onboarding_facts",
        "description": "Pull out every onboarding fact present in the entrepreneur's message, however it's phrased, and write Ozzy's genuine response to what they actually said.",
        "strict": True,
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "response": {
                    "type": "string",
                    "description": (
                        "Write this FIRST, before working out any of the fields below. Ozzy's real "
                        "response to this specific message, in Ozzy's own voice. This field is NEVER an "
                        "empty string, no matter what the message says -- always write something real.\n"
                        "- If you learned something new (a name, business name, products, etc.), acknowledge "
                        "it naturally and warmly, e.g. \"It's lovely to meet you, Sarah.\" or \"I like that "
                        "name.\" or \"Got it, dresses and shoes.\"\n"
                        "- If the message hands you several facts at once, acknowledge the whole picture in "
                        "one warm sentence, don't skip this just because there's a lot to acknowledge, e.g. "
                        "\"Wonderful, Sarah! Sarah's Fashion in Kampala, got it.\"\n"
                        "- If the message asks Ozzy a real question (e.g. \"what's my name\", \"why are you "
                        "asking this\"), answer it directly and correctly using ONLY the known facts you were "
                        "given below, never invent an answer.\n"
                        "- If the message is a comment, complaint, refusal, or anything else that isn't an "
                        "answer, respond to it genuinely and specifically, the way an attentive, warm, calm "
                        "person actually would, not a deflection.\n"
                        "- NEVER use generic customer-service filler. Banned, do not write anything like "
                        "these: \"I'm sorry to hear that you're feeling this way\", \"I'm here to help with "
                        "any questions you have\", \"How can I assist you\", \"I understand your concern\", "
                        "\"I apologize for any inconvenience\". These are not Ozzy's voice.\n"
                        "Do NOT ask anything here, not the onboarding question and not a follow-up question "
                        "of your own invention either (e.g. \"Do you focus on any specific styles?\" or \"What "
                        "else do you have in mind?\") -- the next onboarding question is ALWAYS handled "
                        "separately and appended right after your response, so a question here doubles up "
                        "and confuses the flow. This field is a statement, never a question, it should not "
                        "contain a question mark. No em dashes. Never say 'bookkeeping' or 'accounting'. "
                        "Never sound robotic, bureaucratic, clinical, condescending, or overly formal."
                    ),
                },
                "owner_name": {"type": ["string", "null"], "description": "Just the name itself, e.g. 'My name is Angel' -> 'Angel'. Fix obvious typos silently, don't comment on them. Null if not present in this message."},
                "business_name": {"type": ["string", "null"], "description": "Null if not present in this message."},
                "business_description": {"type": ["string", "null"], "description": "A short description of what they sell/do, in their own words, e.g. 'sells dresses and shoes'. Set this whenever the message says what the business sells or does, even if it's just a plain list of products or services (a product list IS a description). Null only if the message says nothing at all about what the business does."},
                "products_mentioned": {"type": ["array", "null"], "items": {"type": "string"}, "description": "Product or service names mentioned, e.g. ['dresses', 'shoes']. Null if none."},
                "is_service_business": {"type": ["boolean", "null"], "description": "True if this is clearly a services business (no physical stock to track), false if clearly physical products, null if unclear."},
                "business_location": {"type": ["string", "null"], "description": "Null if not present in this message."},
                "employees_count": {"type": ["number", "null"], "description": "How many employees, 0 if they say they have none. Null if not mentioned."},
                "email": {"type": ["string", "null"], "description": "An email address, only if one was actually given, otherwise null."},
                "email_declined": {"type": ["boolean", "null"], "description": "True if they said they don't have one / want to skip, otherwise null."},
                "stock_items": {
                    "type": ["array", "null"], "description": "Products currently in stock, with quantity and/or price if given. Null if none mentioned.",
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": ["number", "null"]},
                            "buying_price": {"type": ["number", "null"]},
                            "selling_price": {"type": ["number", "null"]},
                        },
                        "required": ["name", "quantity", "buying_price", "selling_price"],
                    },
                },
                "stock_declined": {"type": ["boolean", "null"], "description": "True if they said they'll add stock later / want to skip this, otherwise null."},
                "off_topic": {"type": ["boolean", "null"], "description": "True if this message doesn't answer or relate to the current onboarding question at all (a comment, a question back to Ozzy, small talk, a complaint, confusion). Set this whenever nothing above should be extracted from it."},
                "sale_or_expense_mentioned": {"type": ["boolean", "null"], "description": "True if the message describes something that ALREADY HAPPENED -- an actual sale made or money spent, e.g. 'Sold shoes at 50,000, one pair' or 'Paid 10,000 for transport'. This is NOT the same as describing what the business generally sells (e.g. 'I sell shoes' is business_description, not this). Onboarding cannot record transactions yet, so setting this true suppresses your own response text in favor of an honest one. Null/false otherwise."},
            },
            "required": [
                "response",
                "owner_name", "business_name", "business_description", "products_mentioned",
                "is_service_business", "business_location", "employees_count", "email",
                "sale_or_expense_mentioned",
                "email_declined", "stock_items", "stock_declined", "off_topic",
            ],
        },
    },
}]

# §3.5/§3.6/§3.13: exact scripted acknowledgments. Applied deterministically, not left to the
# model, for the single most common case (one clean fact just given, nothing else going on) --
# the same reliability lesson as everywhere else in this codebase: anything that MUST happen
# every time is code, not a hope that the model remembers to say it.
def _stock_ack(items: List[Dict[str, Any]]) -> str:
    names = [i["name"] for i in items]
    if len(names) == 1:
        joined = names[0]
    elif len(names) == 2:
        joined = f"{names[0]} and {names[1]}"
    else:
        joined = ", ".join(names[:-1]) + f", and {names[-1]}"
    return f"Got it. {joined}. \U0001F44D\U0001F3FD"


SCRIPTED_ACK = {
    "owner_name": lambda v: f"It's lovely to meet you, {v}. \U0001F60A",
    "business_name": lambda v: "I like that name. \U0001F60A",
}

# Confirmed live (2026-09-21, and again 2026-09-22 for business_description via "I run a small
# boutique"): even with strict structured outputs, gpt-4o-mini occasionally still misses
# extracting a clean, unambiguous one-line answer into its matching field (e.g. the model
# answers "Rinah Fashions" with a plain echo but leaves the business_name argument null). When
# that happens the state machine correctly re-asks the same question forever, since nothing was
# ever recorded as known. For these plain single-value text fields, a short, non-question,
# not-flagged-off-topic reply is accepted as the literal answer to whatever was just asked,
# rather than trusting model extraction alone for something this fundamental to get right.
# business_description gets a longer allowance since a genuine description runs longer than a
# name or a place ("I sell homemade cakes and pastries for special occasions" is a real answer,
# not a comment).
FALLBACK_MAX_WORDS = {"owner_name": 4, "business_name": 6, "business_location": 6, "business_description": 16}
FALLBACK_ELIGIBLE_FIELDS = set(FALLBACK_MAX_WORDS)

# Confirmed live (2026-09-22): this fallback has a real failure mode of its own -- "You are
# rude." (3 words, no "?", and the model occasionally fails to flag it off_topic) got accepted
# as a literal business_name once, producing "I like that name. :)" in response to an insult. A
# genuine name/place/description never addresses Ozzy in the second person, so this is a cheap,
# safe guard against exactly that kind of remark slipping through the word-count/question-mark
# check alone.
_SECOND_PERSON_RE = re.compile(r"\byou\b|\byour\b|\byou're\b|\byou'll\b|\byou've\b", re.IGNORECASE)

# Confirmed live (2026-09-22, second occurrence): "Answer my question first." -- one of the
# original bug report's own test cases -- also slipped through once (it has no "you", so the
# guard above didn't catch it) and got accepted as a literal business_name. A real name/place
# never opens with an imperative verb aimed at Ozzy, so this is a second, narrow guard for
# exactly that shape of sentence.
_IMPERATIVE_OPENER_RE = re.compile(
    r"^\s*(answer|tell|explain|stop|wait|listen|give|show|help|respond|reply)\b", re.IGNORECASE
)

# Confirmed live (2026-09-22): a plain "No" / "Not right now" / "Not yet" answer to the
# employees question is consistently marked off_topic=true with nothing extracted at all --
# gpt-4o-mini doesn't reliably map a short decline to employees_count=0. Rather than add
# another unreliable extracted boolean, this matches the decline directly against the raw
# text, deterministically, per §3.12 ("If no ... Ozzy continues naturally", i.e. must not
# repeat the question).
_EMPLOYEES_DECLINE_RE = re.compile(
    r"^\s*(no+|nope|nah|none|not\s+(right\s+)?now|not\s+yet|no\s+employees?)\b", re.IGNORECASE
)

# Confirmed live (2026-09-22): email_declined is usually extracted correctly (a "just my phone
# is fine" answer got email_declined=true 8/8 times tested in isolation), but a single live
# end-to-end run still hit the same intermittent miss as employees -- the model's own response
# text even acknowledged the decline while the structured field stayed unset, so onboarding
# re-asked the same email question right after appearing to accept the answer. Same fix as
# employees: a direct, deterministic match on top of (not instead of) the model's own
# extraction, since even an occasional miss here is a real dead end for the user.
_EMAIL_DECLINE_RE = re.compile(
    r"^\s*(no+|nope|nah|none|skip|not\s+(right\s+)?now|not\s+yet|"
    r"(just|only)\s+(my\s+)?(phone|number)|i\s+don'?t\s+have\s+(one|an?\s+email))\b",
    re.IGNORECASE,
)

# Confirmed live (2026-09-22): "I buy them at 10000 and sell at 20000" -- a completely normal
# answer to the pricing question -- failed to extract into stock_items about 1 in 6 tries even
# after naming the specific pending item in the prompt (see target_label in
# interpret_onboarding_message), because the strict schema requires a "name" per stock item and
# a bare "them" gives the model nothing to anchor it to on an off turn. A plain two-number
# answer to "how much do you buy/sell X for" has exactly one sane reading -- buy price, then
# sell price, in that order -- so this is deterministic rather than leaving the last onboarding
# question able to block completion forever.
_TWO_NUMBERS_RE = re.compile(r"[\d][\d,]*(?:\.\d+)?")


def _extract_two_numbers(text: str) -> Optional[tuple]:
    nums = [float(n.replace(",", "")) for n in _TWO_NUMBERS_RE.findall(text)]
    if len(nums) == 2:
        return nums[0], nums[1]
    return None

# Confirmed live (2026-09-22): a message describing a completed sale/expense sent mid-onboarding
# ("Sold shoes at 50,000 ugx, one pair") gets a warm-sounding conversational acknowledgment from
# the model ("Got it, a pair of shoes sold for 50,000 UGX") with NOTHING actually written to the
# transactions table -- onboarding has no integration with the real PROPOSE/COMMIT sale flow at
# all. That phrasing is a false confirmation: it implies money was recorded when nothing was.
# Per the Brain doc, Ozzy must never state something as done unless it actually is, so this
# field lets the model flag the case and a deterministic, honest reply replaces whatever the
# model would otherwise have said, rather than trusting free text not to imply completion.


def _pending_pricing_item_name(state: Dict[str, Any]) -> Optional[str]:
    """Same lookup question_for's pricing branch uses -- which stock item is still missing a
    selling price. Shared so the model can be told explicitly what a bare "them"/"it" answer to
    the pricing question refers to (see target_label in interpret_onboarding_message)."""
    known = state.get("known", {})
    item = next((i for i in known.get("stock_items", []) if i.get("selling_price") is None), None)
    return item["name"] if item else None


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
    target_label = target or "nothing specific"
    if target == "pricing":
        # Confirmed live (2026-09-22): without this, "I buy them at 10000 and sell at 20000"
        # failed to extract into stock_items at all -- the schema requires a "name" per item, and
        # a bare "them"/"it" answer gives the model nothing to fill it with, so it produced
        # nothing rather than guess. Naming the specific pending item removes the ambiguity.
        pending_item = _pending_pricing_item_name(state)
        if pending_item:
            target_label = f"the buying and selling price for '{pending_item}' -- if they answer with just numbers, or say 'them'/'it', they mean the price of '{pending_item}'"
    elif target == "employees" and state.get("awaiting") == "employees_count_text":
        # Reached only when handle_awaiting_capture found no plain digit (e.g. "three" spelled
        # out) -- same ambiguity problem as pricing above, name what's actually being asked.
        target_label = "how many employees they have -- expect a number (a word like 'three' counts too), set employees_count to it"
    system_prompt = (
        "IDENTITY: You are Ozzy, warm, friendly, calm, patient, encouraging, respectful, helpful, "
        "human, non-judgmental -- talk like a friend getting to know someone's business, never "
        "robotic, bureaucratic, clinical, condescending, overly formal, or like a financial "
        "institution asking compliance questions. Never say \"bookkeeping\" or \"accounting\", in "
        "any form, including as an ordinary verb (\"accounting for\"). Never use an idiom, "
        "metaphor, or figure of speech that assumes native English fluency, say the literal thing "
        "directly instead. Never use an em dash, use a comma or a period instead. Plain, everyday "
        "language.\n\n"
        "You are getting to know a new business owner during onboarding, building understanding "
        "through conversation, not collecting registration data. Extract every fact the message "
        f"actually contains, however it's phrased (fix obvious typos silently). What's already "
        f"known: {_known_summary(state)}. You most recently asked about: {target_label}. Never "
        "re-extract or contradict something already known unless the "
        "entrepreneur is clearly correcting it.\n\n"
        "Whatever the message actually is, even a question, a complaint, a refusal to answer, "
        "or something with nothing to extract at all, you must genuinely engage with it in the "
        "'response' field. Silently ignoring what someone said and only producing the next "
        "question is never acceptable. If they ask you something answerable from the known "
        "facts above, answer it correctly right there. If they're short with you or dismissive, "
        "stay warm but actually respond to them as a person would, don't hide behind a script."
    )
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
    msg = ai_client.chat(messages, tools=TOOLS, tool_choice="required")
    if msg is None or not msg.tool_calls:
        # ai_client.chat already retried once internally -- this is a genuine, still-unresolved
        # failure, most commonly a connectivity problem reaching OpenAI, not the model failing to
        # understand plain English (confirmed live 2026-09-22: a real "Connection error" got
        # surfaced as if Ozzy hadn't understood "I sale ladies clothes", when the message never
        # reached the model at all). Re-show whatever was pending so there's an actual next step
        # instead of a dead end with nothing further to do.
        note = "Sorry, I'm having a little trouble connecting right now. Could you try sending that again?"
        if target is not None:
            q = question_for(target, state, user)
            reply = f"{note}\n\n{q['text']}"
            return {"state": state, "reply": reply, "done": False, "next_field": target, "kind": q["kind"], "choices": q.get("choices")}
        return {"state": state, "reply": note, "done": False}

    try:
        args = json.loads(msg.tool_calls[0].function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}

    old_known = state.get("known", {})
    known = dict(old_known)
    declined = list(state.get("declined", []))
    is_service = state.get("is_service_business")
    newly_filled: List[str] = []

    # Deliberately NOT gated on `not args.get("off_topic")` -- confirmed live, gpt-4o-mini
    # regularly sets off_topic true on the very same call where it also correctly extracts a
    # real fact (e.g. a bare "Shoes" answer to "what's in stock" comes back with
    # products_mentioned=["shoes"] AND off_topic=true). Every field below is already null-guarded
    # by the model itself, so trust each one independently rather than discarding genuinely
    # extracted data because of one unreliable, self-contradicting flag.
    for field in ("owner_name", "business_name", "business_description", "business_location", "email"):
        if args.get(field):
            if not old_known.get(field):
                newly_filled.append(field)
            known[field] = args[field]
    if args.get("products_mentioned"):
        known["products_mentioned"] = args["products_mentioned"]
    if args.get("employees_count") is not None:
        known["employees_count"] = args["employees_count"]
    if args.get("is_service_business") is not None:
        is_service = args["is_service_business"]
    email_declined_by_model = bool(args.get("email_declined"))
    if email_declined_by_model:
        declined.append("email")
    if args.get("stock_declined"):
        declined.append("stock_items")
        declined.append("pricing")
    if args.get("stock_items"):
        if not old_known.get("stock_items"):
            newly_filled.append("stock_items")
        existing = {i["name"].lower(): i for i in known.get("stock_items", [])}
        for item in args["stock_items"]:
            name_key = item["name"].lower()
            merged = {**existing.get(name_key, {}), **{k: v for k, v in item.items() if v is not None}}
            existing[name_key] = merged
        known["stock_items"] = list(existing.values())
    elif args.get("products_mentioned") and not is_service:
        # Confirmed live: a bare product-name answer to "what's in stock" (e.g. "Shoes") is
        # consistently filed under products_mentioned, not stock_items. A product/service
        # business's product list IS its stock list, so fold any new names in here too rather
        # than leaving the stock question blocked on a field the model won't reliably populate
        # for a plain one-word answer.
        existing = {i["name"].lower(): i for i in known.get("stock_items", [])}
        added_any = False
        for name in args["products_mentioned"]:
            key = name.lower()
            if key not in existing:
                existing[key] = {"name": name}
                added_any = True
        if added_any:
            known["stock_items"] = list(existing.values())
            if not old_known.get("stock_items"):
                newly_filled.append("stock_items")

    # See FALLBACK_ELIGIBLE_FIELDS: extraction missed the pending field entirely, but this reads
    # like a direct one-line answer, not a question or a comment -- take it as the answer.
    if (
        target in FALLBACK_ELIGIBLE_FIELDS
        and not known.get(target)
        and not args.get("off_topic")
        and "?" not in text
        and len(text.split()) <= FALLBACK_MAX_WORDS[target]
        and not _SECOND_PERSON_RE.search(text)
        and not _IMPERATIVE_OPENER_RE.match(text)
    ):
        known[target] = text.strip()
        newly_filled.append(target)

    # See _TWO_NUMBERS_RE: extraction missed the pending item's price entirely, but the message
    # has exactly two numbers in it -- take them as buy price then sell price, in that order.
    if target == "pricing":
        pending_item = _pending_pricing_item_name({"known": known})
        if pending_item:
            item_entry = next((i for i in known.get("stock_items", []) if i["name"] == pending_item), None)
            if item_entry and item_entry.get("selling_price") is None:
                nums = _extract_two_numbers(text)
                if nums:
                    item_entry["buying_price"], item_entry["selling_price"] = nums

    # See _EMPLOYEES_DECLINE_RE: a plain "No" / "Not right now" to the employees question isn't
    # reliably turned into employees_count=0 by the model, so match it directly here instead.
    employees_declined_via_regex = (
        target == "employees" and "employees_count" not in known and bool(_EMPLOYEES_DECLINE_RE.match(text))
    )
    if employees_declined_via_regex:
        known["employees_count"] = 0

    # See _EMAIL_DECLINE_RE.
    email_declined_via_regex = (
        not email_declined_by_model and target == "email" and "email" not in declined
        and not known.get("email") and bool(_EMAIL_DECLINE_RE.match(text))
    )
    if email_declined_via_regex:
        declined.append("email")
    email_declined_this_turn = email_declined_by_model or email_declined_via_regex

    state = {"known": known, "declined": list(dict.fromkeys(declined)), "is_service_business": is_service}
    response = (args.get("response") or "").strip()

    # §3.5/§3.6/§3.13: when exactly one thing was learned this turn and it's one of the fields
    # with an exact scripted acknowledgment, use that verbatim rather than trust the model to
    # remember to say it (or say it right) every single time. A multi-fact message (several
    # things volunteered at once) still gets the model's own combined acknowledgment, there's no
    # single script for that combination.
    if len(newly_filled) == 1:
        field = newly_filled[0]
        if field in SCRIPTED_ACK:
            response = SCRIPTED_ACK[field](known[field])
        elif field == "stock_items":
            response = _stock_ack(known["stock_items"])

    # §3.12's exact decline wording -- was already defined as EMPLOYEES_NO_REPLY but never
    # actually wired in anywhere, so the model's own (inconsistent) phrasing was used instead.
    if employees_declined_via_regex:
        response = EMPLOYEES_NO_REPLY

    # §3.10's exact decline wording -- same situation as EMPLOYEES_NO_REPLY, was defined but
    # never wired in. Applied whenever email gets declined this turn, whether the model itself
    # caught it or the regex fallback did, so the Brain doc's exact wording always wins over
    # whatever the model would have improvised.
    if email_declined_this_turn:
        response = EMAIL_DECLINE_REPLY

    # See sale_or_expense_mentioned in TOOLS: overrides anything above, deliberately. Onboarding
    # has no path to actually record a transaction, so the reply must never sound like one was
    # saved -- a deterministic, honest line replaces whatever the model said rather than trusting
    # free text not to imply completion.
    if args.get("sale_or_expense_mentioned"):
        response = (
            "Thanks for telling me! I can't record that just yet while we're still setting up "
            "your business, but I'll make sure to save it properly for you as soon as we're done, "
            "just a little more to go."
        )

    if not response:
        # Should be rare given the prompt above, but never send a bare re-asked question with
        # zero acknowledgment that anything was said at all.
        response = "Got it."

    nxt = next_missing_field(state)
    if nxt is None:
        reply = f"{response}\n\n{completion_message(state)}"
        return {"state": state, "reply": reply, "done": True}

    q = question_for(nxt, state, user)
    reply = f"{response}\n\n{q['text']}"
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

    if field == "email":
        if value == "add":
            # Stay on this question until the actual address is captured as free text, same
            # pattern as phone_confirm's "different" branch.
            state = {**state, "known": known}
            return {"state": state, "reply": "What's your email?", "done": False, "next_field": "email", "kind": "text"}
        # "skip"
        declined.append("email")
        state = {**state, "known": known, "declined": declined}
        return _advance(state, user, prefix=f"{EMAIL_DECLINE_REPLY}\n\n")

    if field == "employees":
        if value == "yes":
            # Confirmed live (2026-09-22): a bare digit answer like "3" to this follow-up was
            # occasionally not recognized as answering "employees" by the model (target_label
            # just said "employees", not specifically "expect a number"), so this is captured
            # deterministically instead, see handle_awaiting_capture's "employees_count_text".
            state = {**state, "known": known, "awaiting": "employees_count_text"}
            return {"state": state, "reply": "Great! How many employees do you have?", "done": False, "next_field": "employees", "kind": "text"}
        # "no"
        known["employees_count"] = 0
        state = {**state, "known": known}
        return _advance(state, user, prefix=f"{EMPLOYEES_NO_REPLY}\n\n")

    if field == "stock_items":
        if value == "now":
            # Same pattern as employees "yes" -- stays on "stock_items" (still missing), the
            # actual free-text question follows, answered normally by interpret_onboarding_message.
            state = {**state, "known": known}
            return {"state": state, "reply": QUESTIONS["stock_items"], "done": False, "next_field": "stock_items", "kind": "text"}
        # "later"
        declined.append("stock_items")
        declined.append("pricing")
        state = {**state, "known": known, "declined": declined}
        return _advance(state, user, prefix="No problem, you can add products anytime by just telling me what you sold.\n\n")

    return _advance(state, user)


def handle_awaiting_capture(user: User, state: Dict[str, Any], text: str) -> Optional[Dict[str, Any]]:
    """If the previous turn left something specific pending (the actual phone number after
    choosing 'different', or a headcount after tapping 'Yes' to employees), the next plain
    message is captured directly rather than run through general extraction. Returns None if
    nothing was pending (falls through to the model turn)."""
    awaiting = state.get("awaiting")
    if awaiting == "contact_phone_text":
        known = dict(state.get("known", {}))
        known["contact_phone"] = text.strip()
        known["phone_confirm"] = "different"
        state = {**state, "known": known, "awaiting": None}
        return _advance(state, user)
    if awaiting == "employees_count_text":
        m = re.search(r"\d+", text)
        if not m:
            return None  # not a plain digit ("a few", "three") -- let the model take a shot
        known = dict(state.get("known", {}))
        known["employees_count"] = int(m.group())
        state = {**state, "known": known, "awaiting": None}
        return _advance(state, user)
    return None


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
    elif known.get("products_mentioned"):
        # See _is_known: a bare product list satisfies the onboarding question even when the
        # model never separately fills business_description, so synthesize one here rather than
        # leaving the profile field blank.
        user.business_description = "Sells " + ", ".join(known["products_mentioned"])
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
