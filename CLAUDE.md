# Ozzy for Business — Project Brief for Claude Code

## Who you're working with
The owner, Angel, has no coding background. Explain any technical term in plain language the first time you use it. Always give full file replacements, never partial diffs she has to merge by hand. One task at a time — do not jump between unrelated concerns in a single instruction.

## Product
Ozzy for Business is an AI-powered, chat-first financial management platform for African small businesses (Uganda first). The core promise: manage your business as easily as chatting on WhatsApp. Owners record sales/expenses by typing plain language ("Sold shoes 40,000") and the AI handles the rest.

## Tech stack
- Backend: FastAPI (Python 3.12), SQLAlchemy + Alembic, SQLite locally (Postgres planned for production)
- Frontend: React + TypeScript + Vite, Tailwind CSS
- AI: OpenAI, model gpt-4o-mini, centralized in `app/services/ai_client.py` (moved off Groq on 2026-08-30 — see Rule 1/2)
- Auth: phone number + password (JWT) — not OTP, to avoid per-message SMS costs
- Repo: github.com/AngelWanyama/ozzyforbusiness (public)
- Local path: `C:\Users\user\ozzyforbusiness`

## Rules that must never be broken
1. **Paid OpenAI billing is approved, deliberately.** Confirmed by Angel on 2026-08-30, reversing the earlier free-tier-only constraint specifically to allow moving the AI layer from Groq to OpenAI, per Appendix A of the Ozzy Behaviour Intelligence Brain (`brain-spec/Ozzy_Behaviour_Intelligence_Brain_v1.md`). This approval covers the AI provider only — do not treat it as blanket permission for other paid services; any other paid service still needs the same explicit, separate confirmation.
2. **AI provider is OpenAI, model gpt-4o-mini.** Never use gpt-4o or any larger/costlier model without a specific, tested reason. Never suggest or revert to Google Gemini — it was abandoned after billing/quota failures. Live as of 2026-08-30 — `app/services/ai_client.py` runs OpenAI, not Groq. `OPENAI_API_KEY` must be set in `.env` for AI features to work at all.
3. **Branding:** primary purple `#3F0071` (hover `#2E0054`), teal `#1EBFA3` used only inside Chat for sent bubbles and Ozzy's avatar. **Never use an owl anywhere** — it carries a negative cultural meaning in Uganda. (The current favicon and chat avatar still use a 🦉 emoji — flag this for removal as an easy independent task.)
4. **Every session starts with these commands, unprompted:**
   - Terminal 1: `cd C:\Users\user\ozzyforbusiness` → `venv\Scripts\activate` → `uvicorn app.main:app --reload`
   - Terminal 2: `cd C:\Users\user\ozzyforbusiness\frontend` → `npm run dev`
5. **Only ever work on the main branch.** Never check out, merge, or pull from any other branch — including any branch created by CTO.new — without Angel's explicit permission first, regardless of its name.
6. **Never run CTO.new and Claude Code on this repo at the same time.** Always `git pull` before starting manual work.
7. **Commit and push at the start and end of every session.**

## Verified current state (checked directly against the local repo, 2026-08-30 — trust this over any older summary, including older parts of this same file that hadn't been re-checked in a while)

This section had drifted a long way from reality before this pass — several features listed below as "not built" in older versions of this file were, in fact, already fully built (most likely by CTO.new working directly on `main`). Treat every line below as freshly verified, not carried forward.

### Activities tab — DONE
Real transactions, search, date filters (Today/Week/Month/All), plain-language breakdowns ("You sold 3 dresses..."). Fully wired, frontend and backend both real.

### Settings tab — MOSTLY DONE
Backend: `GET /users/me`, `PATCH /users/me`, `POST /users/me/logo` in `app/api/api_v1/endpoints/users.py`. `UserProfileUpdate` supports business name/type, owner name, description, years in business, location, email, contact phone, notifications, receipt template, currency.
- **Working:** Business Name, Business Type, Currency, owner name, description, years in business, location, email, logo upload, receipt template choice, onboarding-completed flag — all save and load for real.
- **Still not built:** Add Another Account, Switch Business (multiple businesses per login — out of scope per the Brain doc's Open Decisions Log), Add Worker/Manage Access buttons (backend exists, not wired — see Workers Stage E), Change PIN, Biometric Login toggle, Help Center/Contact Support/About Ozzy content.

### Reports tab — DONE
Backend: `GET /reports/summary` and `GET /reports/dashboard` (period today/week/month — totals, % change vs. previous period, 7-day daily chart, expense category breakdown, best-sellers) plus `GET /reports/dashboard/pdf` for export, all in `app/api/api_v1/endpoints/reports.py`, all `business_id`-scoped and owner-only.
Frontend: `frontend/src/pages/Reports.tsx` calls `/reports/dashboard` for real, with loading/error states and a working PDF download. No hardcoded data.

### Chat tab — DONE (AI layer rebuilt 2026-08-30)
- **Working:** real OpenAI (gpt-4o-mini) tool-calling per Appendix A of the Brain doc, with a genuine server-side PROPOSE/COMMIT flow (see `app/models/chat_proposal.py` and `app/services/chat_engine.py`) instead of a fixed classifier; first-time onboarding conversation (client-orchestrated in `frontend/src/pages/Chat.tsx`, saves each answer immediately); dynamic time-of-day greeting (`app/services/greeting_engine.py`, `GET /chat/greeting`) covering morning/midday/evening/no-activity/great-day/slow-day/outstanding-invoices/low-stock/weekly-milestone; invoicing and receipts from a chat request; receipt photo scanning (`app/services/receipt_scanner.py`, vision call); voice input (record → transcribe → same pipeline as typed text).
- **Still not built:** worker-add-via-chat is implemented as a proposal (`generate_worker_invite`) but untested end-to-end pending Angel providing a real `OPENAI_API_KEY` locally; text-to-speech (Ozzy speaking replies aloud) — not planned yet per the Brain doc.

### Workers & Permissions system
Locked spec: two roles, Owner and Worker. Worker can record sales/expenses via chat and see the past week's activity only. Worker cannot see reports/profit/totals, activity older than a week, export/download, settings, add workers, or edit/delete transactions. Onboarding: Owner generates a 6-digit invite code (valid 7 days, one-time use); Worker enters it via a "Have an invite code?" link on login, sets their own password, joins the Owner's business.
- **Stage A — DONE:** `role` and `business_id` added to every business-data table (users, transactions, items, payments, summaries, invoices, invites, customers), migrated and backfilled, non-nullable throughout. New registrations auto-assigned as owner of their own business.
- **Stage B — DONE:** invite backend built and verified — `POST /invites/generate`, `/invites/check`, `/invites/redeem`, `GET /invites/workers` in `app/api/api_v1/endpoints/invites.py`.
- **Stage C — PARTIAL:** most Owner-only endpoints already gate on `require_owner` (reports, invoices, settings). The chat layer's function catalog now also enforces Owner-only per function in code (`OWNER_ONLY_FUNCTIONS` in `chat_engine.py`), independent of the model. Not yet audited: whether every REST endpoint (not just chat) correctly blocks a Worker.
- **Stage D — NOT DONE:** Worker's limited app view (hide Reports, old activity, Settings tabs in the frontend nav for a Worker).
- **Stage E — NOT DONE:** wire the "Have an invite code?" login link and the "Add Worker"/"Manage Access" Settings buttons to the already-built invite backend.

## Locked product specs — build to these exactly, do not redesign

### First-time onboarding conversation (in Chat)
On a brand-new user's first message, Ozzy greets them and asks, one at a time, conversationally (never a form): owner's name → business name → business location → what the business does → how long it's been running → logo upload → phone confirmation ("use the number you logged in with, or a different one?") → optional email ("do you have an email to share, or shall we continue with just your phone?"). Every answer saves to the backend immediately as it's given. Settings only ever *displays* this data — it never asks for it separately.

### Dynamic greeting (every login after onboarding)
Formula for every case: **Greeting → Summary → Insight → Next Step**, with tappable suggestion chips. Never generic ("How can I help?") — Ozzy always opens with the most useful thing it already knows about the business.

- **First login ever:** "👋 Hi [name], welcome to Ozzy! I'm here to help you understand your business by simply chatting. Let's get your business ready. What's your business called?" (starts onboarding)
- **Morning:** "☀️ Good morning, [name]. Yesterday you made [X] from [N] sales. Your profit was [Y]. You're running low on [item]. What would you like to do today?" Chips: Record a sale / Check stock / View yesterday / Create an invoice
- **Midday:** "👋 Good afternoon, [name]. So far today you've made [X] from [N] sales. Your biggest expense today is [category]. How can I help?" Chips: Record a sale / Record an expense / Create an invoice
- **Evening:** "🌙 Good evening, [name]. Here's how today went. Sales: [X]. Expenses: [Y]. Profit: [Z]. Nice work today. What would you like to do before you close?" Chips: View today's activity / Create a report / Check stock
- **No activity today:** "👋 Good afternoon, [name]. I haven't seen any business activity today yet. When you're ready, tell me about your first sale or expense."
- **Great day:** "🎉 Good afternoon, [name]. Congratulations! Today is your best sales day this month. You've already made [X]. Keep it going!"
- **Slow day:** "👋 Good afternoon, [name]. Today has been quieter than usual. Sales are lower than yesterday at this time. Would you like to see what's changed?"
- **Outstanding invoices:** "👋 Good morning, [name]. You have [N] unpaid invoices worth [X]. Following up with those customers could improve your cash flow today."
- **Low stock:** "👋 Good morning, [name]. [Items] are running low. You may want to restock before they run out."
- **Weekly milestone:** "🎉 Congratulations! You've reached [X] in sales this week. That's [N%] higher than last week."

Backend needed to power this: name, current time, today+yesterday totals, low-stock check, unpaid-invoice check, best-day/week detection.

### Invoicing & receipts — one feature, two outputs, built together
Never build one without the other. Same data produces an **Invoice** (before payment) and a **Receipt** (after payment, or from a scanned photo). At onboarding (or later in Settings), the user picks one of three visual templates; that choice is remembered and auto-applied to every invoice/receipt they generate afterward:
1. **Clean Minimal** — quiet, professional. Best for formal/corporate billing.
2. **Bold Branded** — full Ozzy purple/teal, confident. Best for retail, fashion, beauty.
3. **Classic Ledger** — cream paper, boxed like a familiar receipt book. Best for market vendors and traditional trade.

All three auto-fill the user's logo and business name from their profile. Flow: user says "invoice [client] for [items/amount]" in Chat → Ozzy asks clarifying questions only where genuinely needed → shows a preview → offers Download PDF / Share on WhatsApp / Send by Email.

### Receipt photo scanning (expense capture)
User uploads a photo of a paper receipt in Chat. The AI reads it (item, amount, date, vendor) using a vision-capable model call, then confirms back in plain language ("I see UGX 15,000 spent on transport on Tuesday, is that right?") before recording it as an expense transaction. Requires a second function in `app/services/ai_client.py` alongside the existing text parser. Groq's free tier includes vision models — no new cost, no rebuild of the existing parser.

### No canned responses
Except the fixed first-login welcome line, every Chat reply must reflect genuine understanding of what was typed. Ask for clarification when something is unclear — never fall back to generic text.

## Build order — sequential within each chain, the two chains can run in parallel

**Chain 1 — DONE:** profile fields, onboarding conversation, Reports wired to real data, invoicing + receipts, receipt photo scanning, dynamic time-of-day greeting. All verified live as of 2026-08-30 (see Verified current state above).

**Chain 2 (each step depends on the last):**
7. Workers Stage C — audit every non-chat REST endpoint for correct Owner/Worker enforcement (chat layer's functions already enforce this in code)
8. Workers Stage D — Worker's limited app view (hide Reports, old activity, Settings tabs)
9. Workers Stage E — wire invite-code login link + Add Worker/Manage Access buttons

**Fully independent — can run anytime, in parallel with either chain:**
- Remaining Settings polish (Add Another Account/Switch Business are out of scope per the Brain doc; Change PIN, Biometric Login, Help Center/Contact Support/About Ozzy content still need backend or content)
- Remove the owl from favicon and chat avatar
