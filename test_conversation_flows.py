"""
Standalone test script for Ozzy's conversational interpretation, covering every flow that
sends a user message to the model for real understanding: onboarding (Volume 3, §3.1-§3.23),
and the main chat/sales flow.

Run with a real OPENAI_API_KEY configured in .env:

    venv\\Scripts\\activate
    python test_conversation_flows.py

It talks to the FastAPI app in-process (no server needs to be running) and prints what Ozzy
actually did for each case, plus a PASS/FAIL judgment against what should have happened. It
creates and then deletes its own throwaway test users, it does not touch real data.

The onboarding section below is the permanent regression suite for the 2026-09-21 tone and
comprehension bug: Ozzy silently re-asking the scripted question instead of genuinely engaging
with off-script input (a question back to Ozzy, a rude remark, a refusal to continue), and
missing the exact §3.5/§3.6/§3.13 acknowledgments. Every case from that bug report has its own
test here so a regression is caught automatically, not just by someone happening to try the
same three sentences again by hand.
"""
import asyncio
import re
import sys

import httpx

# Windows' console defaults to cp1252, which can't print the emoji in Ozzy's real replies --
# without this the test run crashes on the first printed reply instead of on an actual failure.
sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")
from app.main import app  # noqa: E402

PASS = "PASS"
FAIL = "FAIL"
results = []

# Exact generic AI-assistant filler the 2026-09-21 bug report caught Ozzy using. None of this is
# in the Brain doc anywhere and none of it may ever appear in an onboarding reply again.
BANNED_PHRASES = [
    "sorry to hear that you're feeling this way",
    "i'm here to help with any questions",
    "how can i assist",
    "i understand your concern",
    "i apologize for any inconvenience",
]


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((label, status))
    print(f"[{status}] {label}" + (f" -- {detail}" if detail else ""))


def has_banned_phrase(text):
    low = (text or "").lower()
    return any(p in low for p in BANNED_PHRASES)


async def register(client, phone):
    r = await client.post("/api/v1/auth/register", json={"phone_number": phone, "password": "testpass123"})
    return r.json()["access_token"]


async def cleanup(phone):
    import sqlite3
    con = sqlite3.connect("ozzy.db")
    cur = con.cursor()
    cur.execute("SELECT id FROM users WHERE phone_number = ?", (phone,))
    row = cur.fetchone()
    if row:
        uid = row[0]
        for table in ("chat_proposals", "transactions", "items"):
            cur.execute(f"DELETE FROM {table} WHERE user_id = ?", (uid,))
        for table in ("customers", "invoices", "invites"):
            cur.execute(f"DELETE FROM {table} WHERE business_id = ?", (uid,))
        cur.execute("DELETE FROM users WHERE id = ?", (uid,))
    con.commit()
    con.close()


def count_transactions(phone):
    import sqlite3
    con = sqlite3.connect("ozzy.db")
    cur = con.cursor()
    cur.execute("SELECT id FROM users WHERE phone_number = ?", (phone,))
    row = cur.fetchone()
    if not row:
        con.close()
        return 0
    cur.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (row[0],))
    n = cur.fetchone()[0]
    con.close()
    return n


async def new_onboarding_user(client, phone):
    """Fresh user, onboarding started, ready for the first free-text turn."""
    await cleanup(phone)
    token = await register(client, phone)
    headers = {"Authorization": f"Bearer {token}"}
    await client.get("/api/v1/chat/onboarding-start", headers=headers)
    return headers


async def send_msg(client, headers, text):
    r = await client.post("/api/v1/chat/onboarding-message", json={"text": text}, headers=headers)
    return r.json()


async def send_choice(client, headers, field, value):
    r = await client.post("/api/v1/chat/onboarding-choice", json={"field": field, "value": value}, headers=headers)
    return r.json()


async def test_single_word_name(client):
    print("\n=== ONBOARDING: name given alone, one word only ===")
    phone = "+256700000901"
    headers = await new_onboarding_user(client, phone)
    d = await send_msg(client, headers, "Angel")
    print("  reply:", d["reply"])
    reply = d["reply"]
    check("single-word name gets the exact §3.5 acknowledgment", "lovely to meet you" in reply.lower() and "angel" in reply.lower(), reply)
    check("single-word name still advances to the business-name question", "name of your business" in reply.lower(), reply)
    await cleanup(phone)


async def test_name_typo(client):
    print("\n=== ONBOARDING: name given with a typo ===")
    phone = "+256700000902"
    headers = await new_onboarding_user(client, phone)
    d = await send_msg(client, headers, "my nmae is Angeal")
    print("  reply:", d["reply"])
    reply = d["reply"]
    check(
        "typo'd name is understood and acknowledged warmly, with no comment on the mistake",
        "lovely to meet you" in reply.lower() and "typo" not in reply.lower() and "spelling" not in reply.lower() and "mean" not in reply.lower(),
        reply,
    )
    check("typo'd name still advances to the business-name question", "name of your business" in reply.lower(), reply)
    await cleanup(phone)


async def test_wrong_word_substitution(client):
    """Bug 3, 2026-09-22: a real live 'Connection error' reaching OpenAI got surfaced as Ozzy
    failing to understand "I sale ladies clothes" -- the message never reached the model at all.
    ai_client.chat now retries once on a connection error, so this should sail through under
    normal conditions. This is also §3.2's actual target case (a simple wrong-word substitution,
    not just a misspelling): confirm Ozzy reads intent, not just characters."""
    print("\n=== ONBOARDING: business description with a common wrong-word substitution ===")
    phone = "+256700000908"
    headers = await new_onboarding_user(client, phone)
    await send_msg(client, headers, "Angel")
    await send_msg(client, headers, "Rinah Fashions")
    d = await send_msg(client, headers, "I sale ladies clothes")
    print("  reply:", d["reply"])
    reply = d["reply"]
    check(
        "wrong-word substitution ('sale' for 'sell') is understood, not a generic non-answer",
        "didn't quite catch" not in reply.lower() and "having a little trouble" not in reply.lower() and "isn't configured" not in reply.lower(),
        reply,
    )
    check(
        "business description is recognized as answered, Ozzy moves forward instead of re-asking it",
        "what do you sell or what services do you offer" not in reply.lower(),
        reply,
    )
    await cleanup(phone)


async def test_direct_question_to_ozzy(client):
    print("\n=== ONBOARDING: a direct question aimed at Ozzy mid-onboarding ===")
    phone = "+256700000903"
    headers = await new_onboarding_user(client, phone)
    d1 = await send_msg(client, headers, "Angel")
    print("  reply 1:", d1["reply"])
    d2 = await send_msg(client, headers, "Wait, before that -- what's my name, if you remember it?")
    print("  reply 2:", d2["reply"])
    reply = d2["reply"]
    check("a real question aimed at Ozzy is answered correctly from known facts", "angel" in reply.lower(), reply)
    check("no generic AI-assistant filler in the answer", not has_banned_phrase(reply), reply)
    check("Ozzy still returns to the pending business-name question afterward", "name of your business" in reply.lower(), reply)
    await cleanup(phone)


async def test_rude_reply(client):
    print("\n=== ONBOARDING: a rude / dismissive reply ===")
    phone = "+256700000904"
    headers = await new_onboarding_user(client, phone)
    d1 = await send_msg(client, headers, "Angel")
    print("  reply 1:", d1["reply"])
    d2 = await send_msg(client, headers, "You are rude.")
    print("  reply 2:", d2["reply"])
    reply = d2["reply"]
    check("no generic AI-assistant filler (\"sorry to hear that you're feeling this way\" etc.)", not has_banned_phrase(reply), reply)
    check("response line before the question is non-empty (genuinely engaged, not silent)", bool(reply.split("\n\n")[0].strip()), reply)
    check("still returns to the pending business-name question", "name of your business" in reply.lower(), reply)
    await cleanup(phone)


async def test_refuses_to_continue(client):
    print("\n=== ONBOARDING: refuses to continue until Ozzy answers something first ===")
    phone = "+256700000905"
    headers = await new_onboarding_user(client, phone)
    d1 = await send_msg(client, headers, "Angel")
    print("  reply 1:", d1["reply"])
    d2 = await send_msg(client, headers, "Answer my question first.")
    print("  reply 2:", d2["reply"])
    reply = d2["reply"]
    check("no generic AI-assistant filler (\"I'm here to help with any questions you have\" etc.)", not has_banned_phrase(reply), reply)
    check("response line before the question is non-empty (genuinely engaged, not silent)", bool(reply.split("\n\n")[0].strip()), reply)
    check("still returns to the pending business-name question", "name of your business" in reply.lower(), reply)
    await cleanup(phone)


async def test_all_info_at_once(client):
    print("\n=== ONBOARDING: all info given at once (the Sarah case, §3.20) ===")
    phone = "+256700000906"
    headers = await new_onboarding_user(client, phone)
    d = await send_msg(client, headers, "Hi, I'm Sarah. I run Sarah's Fashion in Kampala. I sell dresses and shoes. I have three employees.")
    print("  reply:", d, "\n  field/kind:", d.get("field"), d.get("kind"))
    reply = d["reply"].lower()
    check("does not re-ask for the owner's name", "what should i call you" not in reply, reply)
    check("does not re-ask for the business name", "name of your business" not in reply, reply)
    check("does not re-ask for the location", "where is your business located" not in reply, reply)
    check("does not re-ask about employees", "any employees" not in reply, reply)
    await cleanup(phone)


async def test_employees_decline_loop(client):
    """Bug report 2026-09-22, Issue 2: 'Not right now' / 'No' to the employees question got
    re-asked the identical question forever, permanently blocking onboarding completion for
    anyone who didn't want to add employees immediately."""
    print("\n=== ONBOARDING: employees decline must not loop (§3.12) ===")
    phone = "+256700000909"
    headers = await new_onboarding_user(client, phone)
    for text in ["Angel", "Rinah Fashions", "I run a small boutique", "Kampala"]:
        await send_msg(client, headers, text)
    await send_choice(client, headers, "phone_confirm", "same")
    await send_msg(client, headers, "I don't have one yet, that's fine")
    await send_choice(client, headers, "logo", "none")

    d = await send_msg(client, headers, "Not right now")
    print("  reply 1:", d["reply"])
    check(
        "§3.12 decline gets the exact scripted text, not a repeated question",
        "that's perfectly fine" in d["reply"].lower() and "always add employees later" in d["reply"].lower(),
        d["reply"],
    )
    check("employees question is not asked again", "do you have any employees" not in d["reply"].lower(), d["reply"])
    check("onboarding actually advanced past employees", d.get("field") != "employees", d)
    await cleanup(phone)


async def test_email_decline_variants(client):
    """Issue 3 follow-up found during Issue 2's live retest: 'just my phone is fine' -- a
    natural, common way to decline -- intermittently failed to register as declined the same
    way 'No' did for employees. Confirms §3.10's exact text fires and onboarding advances."""
    print("\n=== ONBOARDING: email decline with natural phrasing (§3.10) ===")
    phone = "+256700000910"
    headers = await new_onboarding_user(client, phone)
    for text in ["Angel", "Rinah Fashions", "I run a small boutique", "Kampala"]:
        await send_msg(client, headers, text)
    await send_choice(client, headers, "phone_confirm", "same")

    d = await send_msg(client, headers, "just my phone is fine")
    print("  reply:", d["reply"])
    check(
        "§3.10 decline gets the exact scripted text",
        "we can leave that for now" in d["reply"].lower(),
        d["reply"],
    )
    check("email question is not asked again", "what email address" not in d["reply"].lower(), d["reply"])
    await cleanup(phone)


async def test_business_description_natural_phrasing(client):
    """Issue 4, 2026-09-22: 'I sell ladies clothes and shoes' got no acknowledgment before the
    next question. Confirmed already fixed by the 2026-09-21 strict-mode/response-first change
    (8/8 reliable in isolated retesting) -- this is the permanent regression case for exactly
    the phrasing from the bug report."""
    print("\n=== ONBOARDING: business description acknowledgment (§3.7 exact phrasing) ===")
    phone = "+256700000911"
    headers = await new_onboarding_user(client, phone)
    await send_msg(client, headers, "Angel")
    await send_msg(client, headers, "Rinah Fashions")
    d = await send_msg(client, headers, "I sell ladies clothes and shoes")
    print("  reply:", d["reply"])
    response_line = d["reply"].split("\n\n")[0].strip()
    check(
        "business description gets a real acknowledgment, not a bare re-ask",
        bool(response_line) and response_line.lower() != "got it.",
        d["reply"],
    )
    check("moves on to the next question instead of repeating itself", "where is your business located" in d["reply"].lower(), d["reply"])
    await cleanup(phone)


async def test_sale_mentioned_mid_onboarding(client):
    """Issue 5, 2026-09-22: a sale mentioned mid-onboarding ('Sold shoes at 50,000 ugx, one
    pair') got a conversational reply that sounded exactly like a real confirmation ('Got it,
    ...sold for 50,000 UGX') while nothing was written to the transactions table -- a false
    confirmation. Onboarding has no PROPOSE/COMMIT integration, so the fix is honesty: the reply
    must not imply anything was recorded, and nothing should actually land in the database."""
    print("\n=== ONBOARDING: a sale mentioned mid-onboarding must not be falsely confirmed ===")
    phone = "+256700000912"
    headers = await new_onboarding_user(client, phone)
    await send_msg(client, headers, "Angel")
    await send_msg(client, headers, "Rinah Fashions")

    before = count_transactions(phone)
    d = await send_msg(client, headers, "Sold shoes at 50,000 ugx, one pair")
    print("  reply:", d["reply"])
    after = count_transactions(phone)
    reply = d["reply"].lower()
    check("does not falsely claim the sale was recorded/saved", "got it, a pair of shoes sold" not in reply and "recorded" not in reply, d["reply"])
    check("is honest that this hasn't been saved yet", "can't record" in reply or "not yet" in reply or "once we" in reply or "once we're done" in reply, d["reply"])
    check("nothing was actually written to the transactions table", after == before, f"before={before} after={after}")
    await cleanup(phone)


async def test_pricing_bare_pronoun_answer(client):
    """Found live while retesting Issue 2 (not in the original report): 'I buy them at 10000
    and sell at 20000' -- a completely normal answer once a product's already been named --
    failed to extract a price at all about 1 in 6 tries, since the pending item's name is never
    restated in a 'them' answer. This would silently block onboarding completion on the very
    last question. Confirms the deterministic two-number fallback catches it every time."""
    print("\n=== ONBOARDING: pricing answered with a bare pronoun ('them') ===")
    phone = "+256700000913"
    headers = await new_onboarding_user(client, phone)
    for text in ["Angel", "Rinah Fashions", "Shoes", "Kampala"]:
        await send_msg(client, headers, text)
    await send_choice(client, headers, "phone_confirm", "same")
    await send_msg(client, headers, "just my phone is fine")
    await send_choice(client, headers, "logo", "none")
    d = await send_msg(client, headers, "Not right now")
    print("  reply before pricing:", d["reply"], " field=", d.get("field"))

    d = await send_msg(client, headers, "I buy them at 10000 and sell at 20000")
    print("  pricing reply:", d["reply"], " done=", d["done"])
    check("a bare-pronoun price answer is accepted, onboarding reaches completion", d.get("done") is True, d)
    await cleanup(phone)


async def test_full_flow_scripted_acks(client):
    """Walks a full onboarding conversation end to end, confirming every exact §3.5/§3.6/§3.13
    scripted acknowledgment fires on its own single-fact turn, and that the whole state machine
    actually reaches completion."""
    print("\n=== ONBOARDING: full flow, each scripted acknowledgment individually ===")
    phone = "+256700000907"
    headers = await new_onboarding_user(client, phone)

    d = await send_msg(client, headers, "Angel")
    print("  owner_name reply:", d["reply"])
    check("§3.5 owner_name acknowledgment fires exactly", "it's lovely to meet you, angel" in d["reply"].lower(), d["reply"])

    d = await send_msg(client, headers, "Rinah Fashions")
    print("  business_name reply:", d["reply"])
    check("§3.6 business_name acknowledgment fires exactly", "i like that name" in d["reply"].lower(), d["reply"])

    # Deliberately no product names here (vs. "I sell shoes and bags") -- naming products this
    # early also seeds the stock list (a product-list answer legitimately satisfies both "what do
    # you sell" and "what's in stock", see onboarding_engine._is_known), which would make the
    # dedicated stock_items question below get skipped as already-answered. Keeping it vague here
    # is what lets that question fire fresh, so its own single-item scripted ack can be tested in
    # isolation.
    d = await send_msg(client, headers, "I run a small boutique")
    print("  business_description reply:", d["reply"])
    check("business_description turn produces a genuine, non-empty response", bool(d["reply"].split("\n\n")[0].strip()), d["reply"])

    d = await send_msg(client, headers, "Kampala")
    print("  business_location reply:", d["reply"])
    check("moves on after location is given", "where is your business located" not in d["reply"].lower(), d["reply"])

    # phone_confirm is a deterministic choice step, no model call.
    d = await send_choice(client, headers, "phone_confirm", "same")
    print("  phone_confirm reply:", d["reply"])

    d = await send_msg(client, headers, "I don't have one yet, that's fine")
    print("  email reply:", d["reply"])

    # logo is also a deterministic choice step.
    d = await send_choice(client, headers, "logo", "none")
    print("  logo reply:", d["reply"])
    check("logo decline gets the exact §3.11 text", "you don't need one to get started" in d["reply"].lower(), d["reply"])

    d = await send_msg(client, headers, "No employees yet, just me")
    print("  employees reply:", d["reply"])

    d = await send_msg(client, headers, "Shoes")
    print("  stock_items reply:", d["reply"])
    check("§3.13 stock acknowledgment fires exactly for a single item", "got it. shoes." in d["reply"].lower(), d["reply"])

    d = await send_msg(client, headers, "I buy them at 20000 and sell at 30000")
    print("  pricing / completion reply:", d["reply"])
    check("full onboarding conversation reaches completion", d.get("done") is True, d)

    await cleanup(phone)


async def test_chat_sales(client, headers):
    print("\n=== CHAT: sales flow ===")

    # 1. Plain direct answer. A brand-new test business has an empty product catalog, so the
    # first mention of "dresses" correctly triggers the add-to-catalog step before a sale can be
    # proposed (Volume 5) -- confirm that first, same as a real first-time user would.
    r = await client.post("/api/v1/chat/process", json={"text": "sold 2 dresses at 30000 each"}, headers=headers)
    d = r.json()
    print("  reply:", d)
    # 2026-09-22 platform-wide button rule: this "want me to add it?" question now returns
    # action="confirm" (button-backed) instead of a plain "reply" -- typed "yes" must still work
    # too, confirmed here.
    if d["action"] == "confirm" and (d.get("reply") or "").lower().startswith("i don't have"):
        r = await client.post("/api/v1/chat/process", json={"text": "yes"}, headers=headers)
        d = r.json()
        print("  reply (after confirming add-product):", d)
    # 2026-09-23 bug 8 fix: adding a brand-new product now asks for its buying price before the
    # sale finalizes, so this step may need answering before a total is available at all.
    if "how much did you buy" in (d.get("reply") or "").lower():
        r = await client.post("/api/v1/chat/process", json={"text": "20000"}, headers=headers)
        d = r.json()
        print("  reply (after giving buying price):", d)
    # Either a confirm_sale card, or the deterministic add-product-then-resume reply text, both
    # are correct outcomes here -- what matters is the total is right either way.
    amount_ok = (d.get("draft") or {}).get("amount") == 60000 or "60,000" in (d.get("reply") or "")
    check("chat: plain unambiguous sale proposes a confirm card with the right total", amount_ok, d)

    # 2. Correction before confirming
    r = await client.post("/api/v1/chat/process", json={"text": "actually make it 3"}, headers=headers)
    d = r.json()
    print("  reply:", d)
    check("chat: a correction before confirming produces a fresh, updated proposal", d["action"] == "confirm_sale" and d.get("draft", {}).get("amount") == 90000, d)

    # confirm it so state is clean for the next cases
    if d.get("proposal_id"):
        await client.post("/api/v1/chat/confirm", json={"proposal_id": d["proposal_id"]}, headers=headers)

    # 3. Off-topic / unclear, sent as a normal message (no pending proposal at this point)
    r = await client.post("/api/v1/chat/process", json={"text": "are you okay"}, headers=headers)
    d = r.json()
    print("  reply:", d)
    check("chat: off-topic remark gets a real conversational reply, not silently ignored or misfiled", d["action"] == "reply" and bool(d.get("reply")), d)

    # 4. Ambiguous pricing
    r = await client.post("/api/v1/chat/process", json={"text": "sold 2 sodas for 6000"}, headers=headers)
    d = r.json()
    print("  reply:", d)
    check(
        "chat: ambiguous total-vs-each pricing gets a clarifying question, not a guess",
        d["action"] == "reply" and d.get("proposal_id") is None and "each" in (d.get("reply") or "").lower(),
        d,
    )


async def test_offtopic_detour_preserves_pending_sale(client):
    """Bug 10, CRITICAL, 2026-09-23: a pending sale/product proposal got completely forgotten
    the moment the conversation went off-topic even briefly, including Ozzy flatly denying one
    was pending when asked directly. A pending proposal must survive an off-topic detour and
    never be denied when it's real."""
    print("\n=== CHAT: pending proposal survives an off-topic detour ===")
    phone = "+256700000970"
    await cleanup(phone)
    token = await register(client, phone)
    headers = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/users/me", json={"business_name": "Test Co", "currency": "UGX"}, headers=headers)

    r = await client.post("/api/v1/chat/process", json={"text": "sold 1 pair of shoes at 50000"}, headers=headers)
    d = r.json()
    print("  proposal reply:", d)
    check("a new-product sale gets a pending proposal", bool(d.get("proposal_id")), d)

    r = await client.post("/api/v1/chat/process", json={"text": "this app is annoying me today"}, headers=headers)
    d = r.json()
    print("  off-topic detour reply:", d)

    r = await client.post("/api/v1/chat/process", json={"text": "do you have a pending transaction?"}, headers=headers)
    d = r.json()
    reply = (d.get("reply") or "").lower()
    print("  asked directly:", reply)
    check("does not falsely deny a real pending proposal", "no pending" not in reply and "don't have any pending" not in reply and "nothing pending" not in reply, reply)
    check("correctly confirms the pending proposal is still there", "yes" in reply or "shoes" in reply or "pending" in reply, reply)
    await cleanup(phone)


async def test_yes_please_confirms_add_product_sale(client):
    """Bug 9, 2026-09-23: typed "Yes please" confirming a pending add-product-and-record-sale
    proposal wasn't recognized, Ozzy asked for "more detail" instead. Also verifies the bug 9
    redundant-proposal fix: this must resolve in one clean step, not spawn a second, separate
    "Add X to your products?" confirmation that loses track of the sale."""
    print("\n=== CHAT: 'Yes please' cleanly confirms an add-product-then-sale proposal ===")
    phone = "+256700000971"
    await cleanup(phone)
    token = await register(client, phone)
    headers = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/users/me", json={"business_name": "Test Co", "currency": "UGX"}, headers=headers)

    r = await client.post("/api/v1/chat/process", json={"text": "sold 1 pair of shoes at 50000"}, headers=headers)
    d = r.json()
    print("  proposal reply:", d)

    r = await client.post("/api/v1/chat/process", json={"text": "Yes please"}, headers=headers)
    d = r.json()
    print("  'Yes please' reply:", d)
    reply = (d.get("reply") or "").lower()
    check(
        "'Yes please' is recognized as confirmation, not treated as unclear",
        "more detail" not in reply and "could you let me know what you want" not in reply,
        reply,
    )
    check(
        "does not spawn a second, separate 'add to products?' confirmation for the same item",
        "add \"shoes\" to your products?" not in reply and "want me to add it?" not in reply,
        reply,
    )
    await cleanup(phone)


async def test_new_product_prompts_for_buying_price(client):
    """Bug 8, CRITICAL, 2026-09-23: a brand-new product added mid-sale never had its buying
    price asked, so profit could never be calculated for anything added this way."""
    print("\n=== CHAT: a new product added mid-sale prompts for buying price ===")
    phone = "+256700000972"
    await cleanup(phone)
    token = await register(client, phone)
    headers = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/users/me", json={"business_name": "Test Co", "currency": "UGX"}, headers=headers)

    r = await client.post("/api/v1/chat/process", json={"text": "sold 1 pair of shoes at 50000"}, headers=headers)
    r2 = await client.post("/api/v1/chat/process", json={"text": "yes"}, headers=headers)
    d = r2.json()
    print("  reply after confirming add-product:", d)
    reply = (d.get("reply") or "").lower()
    check(
        "asks for the buying price in plain, friendly language, not a bare form field",
        "how much did you buy" in reply and "shoes" in reply,
        reply,
    )
    check("still explains the reason (working out profit), not just a bare request for a number", "profit" in reply, reply)

    r = await client.post("/api/v1/chat/process", json={"text": "15000"}, headers=headers)
    d = r.json()
    print("  reply after giving buying price:", d)
    check("resumes into the sale confirmation once the buying price is given", d.get("action") == "confirm" and d.get("proposal_id"), d)
    if d.get("proposal_id"):
        await client.post("/api/v1/chat/confirm", json={"proposal_id": d["proposal_id"]}, headers=headers)

    import sqlite3
    con = sqlite3.connect("ozzy.db")
    row = con.execute(
        "SELECT buying_price, unit_price FROM items WHERE user_id = (SELECT id FROM users WHERE phone_number = ?) AND name LIKE '%shoes%'",
        (phone,),
    ).fetchone()
    con.close()
    print("  item buying_price/unit_price:", row)
    check("the buying price actually got saved onto the product", row is not None and float(row[0]) == 15000, row)
    await cleanup(phone)


async def test_business_name_change_requires_confirmation(client):
    """Bug 3, CRITICAL, 2026-09-23: business name got silently overwritten mid-chat, twice in
    one conversation, with zero confirmation step. Deliberately overrides Volume 4's original
    L1/instant-apply design for business name/type -- see chat_engine.py's PROPOSAL_FUNCTIONS."""
    print("\n=== CHAT: business name change requires explicit confirmation ===")
    phone = "+256700000973"
    await cleanup(phone)
    token = await register(client, phone)
    headers = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/users/me", json={"business_name": "Old Name Co", "currency": "UGX"}, headers=headers)

    r = await client.post("/api/v1/chat/process", json={"text": "change my business name to Rinah Fashions"}, headers=headers)
    d = r.json()
    print("  reply:", d)
    check("business name change is proposed with a confirm button, not applied instantly", d.get("action") == "confirm" and bool(d.get("proposal_id")), d)

    r = await client.get("/api/v1/users/me", headers=headers)
    check("business name is NOT changed before confirmation", r.json().get("business_name") == "Old Name Co", r.json())

    if d.get("proposal_id"):
        await client.post("/api/v1/chat/confirm", json={"proposal_id": d["proposal_id"]}, headers=headers)
    r = await client.get("/api/v1/users/me", headers=headers)
    check("business name changes only after explicit confirmation", r.json().get("business_name") == "Rinah Fashions", r.json())
    await cleanup(phone)


async def test_single_service_not_treated_as_ambiguous(client):
    """Bug 5, 2026-09-23: a fully complete answer (service name, price, and a clear instruction
    to record it, all in one message) got treated as incomplete and the user was asked to
    repeat everything -- a singular, unnumbered mention was wrongly flagged as ambiguous
    total-vs-each pricing when there was only ever one possible reading."""
    print("\n=== CHAT: a single implied-quantity service is never treated as ambiguous ===")
    phone = "+256700000974"
    await cleanup(phone)
    token = await register(client, phone)
    headers = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/users/me", json={"business_name": "Test Co", "currency": "UGX"}, headers=headers)

    r = await client.post("/api/v1/chat/process", json={"text": "Haircut for 20000, please record it"}, headers=headers)
    d = r.json()
    print("  reply:", d)
    reply = (d.get("reply") or "").lower()
    check(
        "a single service with a clear price is never asked total-vs-each",
        "each" not in reply and "per haircut" not in reply,
        reply,
    )
    await cleanup(phone)


async def check_proposal_type(client, name, phone, extra_setup, trigger_text, expected_actions):
    """2026-09-24: added after being explicitly called out for verifying the platform-wide
    button rule against only 2-3 proposal types and generalizing from there. Every distinct
    proposal type in chat_engine.py now gets its own test, individually, checking all three
    things that were claimed "fixed everywhere": a real button on the proposal itself, survival
    of an off-topic detour, and a plain typed "yes" reliably confirming it -- each in its own
    fresh conversation so one check can't mask a failure in another."""
    # Check 1: shows a real button.
    await cleanup(phone)
    headers = {"Authorization": f"Bearer {await register(client, phone)}"}
    if extra_setup:
        await extra_setup(client, headers)
    r = await client.post("/api/v1/chat/process", json={"text": trigger_text}, headers=headers)
    d = r.json()
    print(f"  [{name}] proposal reply:", d)
    has_button = d.get("action") in expected_actions and bool(d.get("proposal_id"))
    check(f"{name}: shows a real button pair, not plain text", has_button, d)
    await cleanup(phone)
    if not has_button:
        return

    # Check 2: survives an off-topic detour without being denied.
    await cleanup(phone)
    headers = {"Authorization": f"Bearer {await register(client, phone)}"}
    if extra_setup:
        await extra_setup(client, headers)
    await client.post("/api/v1/chat/process", json={"text": trigger_text}, headers=headers)
    await client.post("/api/v1/chat/process", json={"text": "this app is annoying me today"}, headers=headers)
    r = await client.post("/api/v1/chat/process", json={"text": "do you have anything pending?"}, headers=headers)
    reply = (r.json().get("reply") or "").lower()
    print(f"  [{name}] after off-topic detour, asked directly:", reply)
    survives = "nothing" not in reply and "don't have any" not in reply and "no pending" not in reply and not reply.strip().startswith("no ")
    check(f"{name}: survives an off-topic detour without being denied", survives, reply)
    await cleanup(phone)

    # Check 3: plain "yes" reliably confirms it.
    await cleanup(phone)
    headers = {"Authorization": f"Bearer {await register(client, phone)}"}
    if extra_setup:
        await extra_setup(client, headers)
    await client.post("/api/v1/chat/process", json={"text": trigger_text}, headers=headers)
    r = await client.post("/api/v1/chat/process", json={"text": "yes"}, headers=headers)
    d = r.json()
    print(f"  [{name}] after plain 'yes':", d)
    confirmed = bool(d.get("reply")) and d.get("proposal_id") is None
    check(f"{name}: plain 'yes' reliably confirms it", confirmed, d)
    await cleanup(phone)


async def test_every_proposal_type_individually(client):
    """One test per distinct proposal/action type that exists in chat_engine.py, per the
    explicit 2026-09-24 requirement not to generalize from a handful of examples."""
    print("\n=== CHAT: every proposal type individually (button, off-topic survival, plain yes) ===")

    async def add_shoes(client, headers):
        await client.post("/api/v1/inventory/", json={"name": "shoes", "unit_price": 30000, "buying_price": 15000, "stock_level": 10, "is_service": False}, headers=headers)

    await check_proposal_type(client, "propose_sale", "+256700001030", add_shoes, "sold 1 pair of shoes at 30000", {"confirm_sale"})
    await check_proposal_type(client, "propose_expense", "+256700001031", None, "paid 5000 for transport", {"confirm_expense"})
    await check_proposal_type(client, "add_product", "+256700001032", None, "add a new product called bags, I buy them at 10000 and sell at 20000", {"confirm"})

    async def credit_sale_setup(client, headers):
        await client.post("/api/v1/inventory/", json={"name": "shoes", "unit_price": 30000, "buying_price": 15000, "stock_level": 10, "is_service": False}, headers=headers)
        r = await client.post("/api/v1/chat/process", json={"text": "sold 1 pair of shoes at 30000 on credit to John"}, headers=headers)
        d = r.json()
        if d.get("proposal_id"):
            await client.post("/api/v1/chat/confirm", json={"proposal_id": d["proposal_id"]}, headers=headers)

    # "mark John as paid" is genuinely ambiguous with mark_document_paid (an invoice), confirmed
    # live 2026-09-24 -- unambiguous phrasing for testing THIS specific tool.
    await check_proposal_type(client, "mark_customer_paid", "+256700001033", credit_sale_setup, "clear John's outstanding balance", {"confirm"})
    await check_proposal_type(client, "generate_document_preview", "+256700001034", None, "invoice John for 2 dresses at 30000 each", {"confirm"})

    async def unpaid_invoice_setup(client, headers):
        r = await client.post("/api/v1/chat/process", json={"text": "invoice John for 2 dresses at 30000 each"}, headers=headers)
        d = r.json()
        if d.get("proposal_id"):
            await client.post("/api/v1/chat/confirm", json={"proposal_id": d["proposal_id"]}, headers=headers)

    await check_proposal_type(client, "mark_document_paid", "+256700001035", unpaid_invoice_setup, "mark John's invoice as paid", {"confirm"})
    await check_proposal_type(client, "update_profile_field", "+256700001036", None, "change my business name to Rinah Fashions", {"confirm"})
    await check_proposal_type(client, "propose_currency_change", "+256700001037", None, "change my currency to KES", {"confirm"})
    await check_proposal_type(client, "generate_worker_invite", "+256700001038", None, "add a worker with phone number +256700009996", {"confirm"})

    async def worker_setup(client, headers):
        # redeem_invite CREATES the worker account itself and rejects an already-registered
        # phone -- confirmed live 2026-09-24, without cleaning up the worker's own account too
        # (not just the owner's), the SECOND time this test runs the redeem silently fails
        # (phone already exists from the prior run) and no worker ever gets created, so "remove
        # worker" correctly reports not found -- a test bug, not an app bug.
        await cleanup("+256700009995")
        r = await client.post("/api/v1/chat/process", json={"text": "add a worker with phone number +256700009995"}, headers=headers)
        d = r.json()
        if d.get("proposal_id"):
            r = await client.post("/api/v1/chat/confirm", json={"proposal_id": d["proposal_id"]}, headers=headers)
            reply = r.json().get("reply") or ""
            m = re.search(r"\b(\d{6})\b", reply)
            if m:
                await client.post("/api/v1/invites/redeem", json={"code": m.group(1), "password": "testpass123"})

    await check_proposal_type(client, "propose_remove_worker", "+256700001039", worker_setup, "remove worker +256700009995", {"confirm"})
    await cleanup("+256700009995")

    async def low_stock_shoes(client, headers):
        await client.post("/api/v1/inventory/", json={"name": "shoes", "unit_price": 30000, "buying_price": 15000, "stock_level": 5, "is_service": False}, headers=headers)

    await check_proposal_type(client, "propose_restock", "+256700001040", low_stock_shoes, "restocked 10 more shoes, bought at 15000 each", {"confirm"})


async def test_cogs_profit_calculation(client):
    """2026-09-23, CRITICAL: net_profit was sales minus expenses everywhere in the app, cost of
    goods sold never subtracted despite buying_price being collected. Recreates Angel's exact
    live numbers: shoes bought at 15,000, sold at 30,000, one other expense of 4,918.04. Real
    profit is 30,000 - 15,000 - 4,918.04 = 10,081.96, not 25,081.96 (sales minus expenses alone).
    Uses the REST endpoints directly for the expense (not chat) to isolate the COGS calculation
    itself from the model's occasional expense-category back-and-forth, a separate concern."""
    print("\n=== CHAT: cost of goods sold in profit calculation ===")
    phone = "+256700000950"
    await cleanup(phone)
    token = await register(client, phone)
    headers = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/users/me", json={"business_name": "Test Co", "currency": "UGX", "onboarding_completed": True}, headers=headers)

    r = await client.post("/api/v1/inventory/", json={"name": "shoes", "unit_price": 30000, "buying_price": 15000, "stock_level": 10, "is_service": False}, headers=headers)
    check("inventory endpoint accepts and stores a buying_price", r.status_code == 200 and r.json().get("buying_price") == "15000.00", r.json())

    r = await client.post("/api/v1/chat/process", json={"text": "sold 1 pair of shoes at 30000"}, headers=headers)
    d = r.json()
    if d.get("proposal_id"):
        await client.post("/api/v1/chat/confirm", json={"proposal_id": d["proposal_id"]}, headers=headers)

    await client.post("/api/v1/transactions/", json={"type": "expense", "amount": 4918.04, "description": "transport", "category": "Transport", "quantity": 1}, headers=headers)

    r = await client.get("/api/v1/reports/summary", headers=headers)
    d = r.json()
    print("  /reports/summary:", d)
    check("sales are correct", float(d["total_sales"]) == 30000, d)
    check("cost of goods sold is correctly captured (15,000, not 0)", float(d["cost_of_goods_sold"]) == 15000, d)
    check("net profit subtracts COGS, not just expenses (10,081.96, not 25,081.96)", abs(float(d["net_profit"]) - 10081.96) < 0.01, d)
    check("cogs_known_complete is true when every sold item has a buying price on file", d["cogs_known_complete"] is True, d)

    r = await client.post("/api/v1/chat/process", json={"text": "what are my profits today"}, headers=headers)
    reply = (r.json().get("reply") or "").lower()
    print("  chat reply:", reply)
    check("chat answer reflects the real (COGS-aware) profit, not sales minus expenses alone", "10,081" in reply or "10081" in reply, reply)

    r = await client.post("/api/v1/chat/process", json={"text": "what's my margin on shoes"}, headers=headers)
    reply = (r.json().get("reply") or "").lower()
    print("  margin reply:", reply)
    check("per-item margin question is answered correctly (15,000 / 50%)", ("15,000" in reply or "15000" in reply) and "50" in reply, reply)

    await cleanup(phone)


async def test_cogs_unknown_buying_price_is_honest(client):
    """Explicit requirement: an item with no buying price on file must never be silently treated
    as zero cost (which would overstate profit) -- the app must flag it as incomplete instead."""
    print("\n=== CHAT: profit is honest when a buying price is unknown ===")
    phone = "+256700000951"
    await cleanup(phone)
    token = await register(client, phone)
    headers = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/users/me", json={"business_name": "Test Co", "currency": "UGX", "onboarding_completed": True}, headers=headers)

    await client.post("/api/v1/inventory/", json={"name": "bags", "unit_price": 20000, "stock_level": 5, "is_service": False}, headers=headers)
    r = await client.post("/api/v1/chat/process", json={"text": "sold 1 bag at 20000"}, headers=headers)
    d = r.json()
    if d.get("proposal_id"):
        await client.post("/api/v1/chat/confirm", json={"proposal_id": d["proposal_id"]}, headers=headers)

    r = await client.get("/api/v1/reports/summary", headers=headers)
    d = r.json()
    print("  /reports/summary:", d)
    check("cogs_known_complete is false when a sold item has no buying price on file", d["cogs_known_complete"] is False, d)
    check("cost of goods sold is not silently guessed as a real positive number", float(d["cost_of_goods_sold"]) == 0, d)

    r = await client.post("/api/v1/chat/process", json={"text": "what are my profits today"}, headers=headers)
    reply = (r.json().get("reply") or "").lower()
    print("  chat reply:", reply)
    check(
        "reply honestly caveats that real profit may be lower, doesn't state the number as certain",
        any(w in reply for w in ("lower", "not fully known", "n't know", "don't have", "unknown", "not on file", "may be")),
        reply,
    )

    await cleanup(phone)


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await test_single_word_name(client)
        await test_name_typo(client)
        await test_wrong_word_substitution(client)
        await test_direct_question_to_ozzy(client)
        await test_rude_reply(client)
        await test_refuses_to_continue(client)
        await test_all_info_at_once(client)
        await test_employees_decline_loop(client)
        await test_email_decline_variants(client)
        await test_business_description_natural_phrasing(client)
        await test_sale_mentioned_mid_onboarding(client)
        await test_pricing_bare_pronoun_answer(client)
        await test_full_flow_scripted_acks(client)

        phone = "+256700000999"
        await cleanup(phone)
        token = await register(client, phone)
        headers = {"Authorization": f"Bearer {token}"}
        await client.patch("/api/v1/users/me", json={"business_name": "Test Co", "currency": "UGX"}, headers=headers)
        await test_chat_sales(client, headers)
        await cleanup(phone)

        await test_offtopic_detour_preserves_pending_sale(client)
        await test_yes_please_confirms_add_product_sale(client)
        await test_new_product_prompts_for_buying_price(client)
        await test_business_name_change_requires_confirmation(client)
        await test_single_service_not_treated_as_ambiguous(client)

        await test_cogs_profit_calculation(client)
        await test_cogs_unknown_buying_price_is_honest(client)

        await test_every_proposal_type_individually(client)

    print("\n=== SUMMARY ===")
    for label, status in results:
        print(f"[{status}] {label}")
    failed = [r for r in results if r[1] == FAIL]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
