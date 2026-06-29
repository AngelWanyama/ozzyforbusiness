# Ozzy for Business - Deployment Guide

This document outlines the steps to deploy the Ozzy for Business backend.

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./ozzy.db

# Security
SECRET_KEY=your_super_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Services
GEMINI_API_KEY=your_gemini_api_key_here
EXCHANGERATE_API_KEY=your_exchangerate_api_key_here

# Payment Integrations
MTN_UG_API_KEY=your_mtn_key
MTN_UG_USER_ID=your_mtn_user_id
MTN_UG_SUBSCRIPTION_KEY=your_mtn_sub_key

AIRTEL_UG_CLIENT_ID=your_airtel_id
AIRTEL_UG_CLIENT_SECRET=your_airtel_secret

FLUTTERWAVE_SECRET_KEY=your_flutterwave_secret
FLUTTERWAVE_PUBLIC_KEY=your_flutterwave_public
```

## Docker Deployment (Recommended)

1. **Build the image:**
   ```bash
   docker build -t ozzy-backend .
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

## Cloud Hosting Options

### Railway / Render
1. Connect your GitHub repository.
2. Add the environment variables in the dashboard.
3. The `Dockerfile` will be automatically detected and used for deployment.

### DigitalOcean App Platform
1. Create a new "App".
2. Link your repository.
3. Select "Docker" as the build method.
4. Set up your environment variables.

## Database Migrations

Run migrations on the production server:
```bash
docker-compose exec backend alembic upgrade head
```

## Scheduled Tasks (Cron Jobs)

To automate usage resets and AI summaries, set up cron jobs on your server:

```cron
# Reset monthly usage on the 1st of every month at midnight
0 0 1 * * docker-compose exec -T backend python -m app.scripts.reset_usage

# Generate daily AI summaries every day at 6 AM
0 6 * * * docker-compose exec -T backend python -m app.scripts.generate_summaries daily

# Generate weekly AI summaries every Monday at 6:30 AM
30 6 * * 1 docker-compose exec -T backend python -m app.scripts.generate_summaries weekly

# Generate monthly AI summaries on the 1st of every month at 7 AM
0 7 1 * * docker-compose exec -T backend python -m app.scripts.generate_summaries monthly
```

## SSL & Domain

Use a reverse proxy like Nginx with Certbot (Let's Encrypt) to handle SSL and map your domain (e.g., `api.ozzyforbusiness.com`) to port 8000.
