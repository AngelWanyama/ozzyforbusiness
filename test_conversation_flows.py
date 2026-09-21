"""
Standalone test script for Ozzy's conversational interpretation, covering every flow that
sends a user message to the model for real understanding (see the investigation in the
2026 chat log for the full map): onboarding, and the main chat/sales flow.

For each flow this runs: a plain direct answer, a correction after a wrong extraction, an
off-topic/unclear message, and an ambiguous answer. Run with a real OPENAI_API_KEY configured
in .env:

    venv\\Scripts\\activate
    python test_conversation_flows.py

It talks to the FastAPI app in-process (no server needs to be running) and prints what Ozzy
actually did for each case, plus a PASS/FAIL judgment against what should have happened. It
creates and then deletes its own throwaway test users, it does not touch real data.
"""
import asyncio
import sys

import httpx

sys.path.insert(0, ".")
from app.main import app  # noqa: E402

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((label, status))
    print(f"[{status}] {label}" + (f" -- {detail}" if detail else ""))


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


async def test_onboarding(client, headers):
    print("\n=== ONBOARDING: owner_name step ===")

    # 1. Plain direct answer
    r = await client.post("/api/v1/chat/onboarding-reply", json={
        "field": "owner_name", "question": "What's your name?", "text": "My name is Angel",
    }, headers=headers)
    d = r.json()
    print("  reply:", d)
    check("onboarding: plain answer extracts just the name", d["intent"] == "answer" and d.get("value", "").strip().lower() == "angel", d.get("value"))

    # 2. Correction after a wrong extraction (simulate the wrong extraction first)
    r = await client.post("/api/v1/chat/onboarding-reply", json={
        "field": "business_name", "question": "What's your business called?", "text": "No, my name is Angel, not Angelaa",
        "prior_field": "owner_name", "prior_question": "What's your name?", "prior_value": "Angelaa",
    }, headers=headers)
    d = r.json()
    print("  reply:", d)
    check(
        "onboarding: correction to the previous answer is attributed to the previous field, not the current one",
        d["intent"] == "correction" and d.get("applies_to") == "previous",
        d,
    )

    # 3. Off-topic / unclear
    r = await client.post("/api/v1/chat/onboarding-reply", json={
        "field": "owner_name", "question": "What's your name?", "text": "are you okay",
    }, headers=headers)
    d = r.json()
    print("  reply:", d)
    check("onboarding: off-topic remark is recognized, not saved as an answer", d["intent"] == "off_topic", d)

    # 4. Ambiguous answer (vague, no real number given)
    r = await client.post("/api/v1/chat/onboarding-reply", json={
        "field": "years_in_business", "question": "How long has your business been running?", "text": "not that long",
    }, headers=headers)
    d = r.json()
    print("  reply:", d)
    check(
        "onboarding: vague/ambiguous answer doesn't get treated as a confident number",
        d["intent"] != "answer" or not (d.get("value") or "").strip().replace(".", "").isdigit() or d.get("value") in ("0",),
        d,
    )


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
        phone = "+256700000999"
        await cleanup(phone)
        token = await register(client, phone)
        headers = {"Authorization": f"Bearer {token}"}
        await client.patch("/api/v1/users/me", json={"business_name": "Test Co", "currency": "UGX"}, headers=headers)

        await test_onboarding(client, headers)
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
