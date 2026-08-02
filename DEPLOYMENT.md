# Ozzy for Business — Deployment Guide

This explains how Ozzy for Business goes live on the internet, using only free-tier services:

- **Render** — hosts the backend (the FastAPI server that does all the thinking)
- **Vercel** — hosts the frontend (the website/app screens people actually see and tap)
- **Neon** — hosts the database (where all business data — sales, expenses, invoices — is stored)
- **UptimeRobot** — pings the backend every 5 minutes so it doesn't fall asleep (Render's free tier "sleeps" a backend after 15 minutes of no visitors, which would make the app feel slow to the first person who opens it after a quiet period)

None of these cost anything at the scale this app needs right now.

## Environment variables (the settings the backend needs to run)

These are set inside Render's dashboard, not in a file that gets uploaded anywhere — never commit real secrets to GitHub.

| Variable | What it is | Where it comes from |
|---|---|---|
| `GROQ_API_KEY` | Lets the backend talk to Groq, the AI Ozzy uses to understand chat messages | Your Groq account, API Keys page |
| `DATABASE_URL` | The connection string for the production database | Copied from your Neon dashboard |
| `SECRET_KEY` | A random secret used to keep login sessions secure | Any long random string — Render can generate one, or you can paste any long password-like text |
| `ALGORITHM` | The technical method used to sign login sessions | Always `HS256` — leave as-is |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | How long someone stays logged in before needing to log in again | `10080` (that's 7 days) is a sensible default |
| `FRONTEND_URL` | The live Vercel web address, so the backend knows to trust it | Fill this in *after* Vercel gives you the frontend's URL (see checklist below) |

**No longer needed, removed from this guide:** `GEMINI_API_KEY` (the project uses Groq now, not Google Gemini) and the MTN/Airtel/Flutterwave payment keys (payments aren't built yet — these will come back once that feature exists).

## Keep-alive health check

The backend already has a `/health` endpoint built in — it needs no login and just replies `{"status": "healthy"}`. This is what UptimeRobot will ping every 5 minutes to keep the backend awake. Once deployed on Render, it will live at an address like:

```
https://your-app-name.onrender.com/health
```

## Deployment checklist (do these in order)

### 1. Set up the database (Neon)
1. Go to neon.tech and create a free account.
2. Create a new project/database (any name is fine, e.g. "ozzy-production").
3. On the project dashboard, find and copy the **connection string** (it starts with `postgresql://`). Keep this page open — you'll paste it into Render next.

### 2. Deploy the backend (Render)
1. Go to render.com and create a free account.
2. Create a new **Web Service** and connect your GitHub account, then select the `ozzyforbusiness` repository.
3. When asked for environment variables, add all of these:
   - `GROQ_API_KEY` — your real Groq key
   - `DATABASE_URL` — the connection string you copied from Neon
   - `SECRET_KEY` — any long random text
   - `ALGORITHM` — `HS256`
   - `ACCESS_TOKEN_EXPIRE_MINUTES` — `10080`
   - (leave `FRONTEND_URL` blank for now — you'll come back and add it in step 3)
4. Click deploy. Render will build and start the backend automatically — this can take a few minutes the first time.
5. Once it's live, copy the backend's web address (something like `https://ozzy-backend.onrender.com`) — you'll need it for the frontend in the next step.

### 3. Deploy the frontend (Vercel)
1. Go to vercel.com and create a free account.
2. Import the same GitHub repository, and set the project's root folder to `frontend`.
3. Add one environment variable: `VITE_API_URL` set to your Render backend address from step 2, followed by `/api/v1` (e.g. `https://ozzy-backend.onrender.com/api/v1`).
4. Click deploy. Once it's live, Vercel will give you a web address (something like `https://ozzy-for-business.vercel.app`) — this is the real link people will use to open the app.
5. Go back to Render, open the backend's environment variables, and add `FRONTEND_URL` set to that exact Vercel address. Save — Render will restart the backend automatically with this new setting.

### 4. Keep the backend awake (UptimeRobot)
1. Go to uptimerobot.com and create a free account.
2. Add a new monitor: choose "HTTP(s)", paste in your Render health-check address (`https://your-app-name.onrender.com/health`), and set it to check **every 5 minutes**.
3. Save. UptimeRobot will now ping the backend around the clock so it stays awake and responds quickly whenever someone opens the app.

That's it — Neon holds the data, Render runs the backend, Vercel serves the app, and UptimeRobot keeps everything responsive.

## Database migrations

After the first deploy (and any time the data structure changes), run migrations against the production database from Render's dashboard **Shell** tab:

```bash
alembic upgrade head
```

## Scheduled tasks (optional, for later)

Render's free tier doesn't include built-in cron jobs. If/when these become needed, Render offers a separate free "Cron Job" service type that can run these on a schedule:

```bash
# Reset monthly usage on the 1st of every month at midnight
python -m app.scripts.reset_usage

# Generate daily AI summaries every day at 6 AM
python -m app.scripts.generate_summaries daily

# Generate weekly AI summaries every Monday at 6:30 AM
python -m app.scripts.generate_summaries weekly

# Generate monthly AI summaries on the 1st of every month at 7 AM
python -m app.scripts.generate_summaries monthly
```

This isn't set up yet — flagging it here so it isn't forgotten, not because it's needed right now.
