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
        cur.execute("DELETE FROM users WHERE id = ?", (uid,))
    con.commit()
    con.close()


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
    if d["action"] == "reply" and (d.get("reply") or "").lower().startswith("i don't have"):
        r = await client.post("/api/v1/chat/process", json={"text": "yes"}, headers=headers)
        d = r.json()
        print("  reply (after confirming add-product):", d)
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
        await test_full_flow_scripted_acks(client)

        phone = "+256700000999"
        await cleanup(phone)
        token = await register(client, phone)
        headers = {"Authorization": f"Bearer {token}"}
        await client.patch("/api/v1/users/me", json={"business_name": "Test Co", "currency": "UGX"}, headers=headers)
        await test_chat_sales(client, headers)
        await cleanup(phone)

    print("\n=== SUMMARY ===")
    for label, status in results:
        print(f"[{status}] {label}")
    failed = [r for r in results if r[1] == FAIL]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
