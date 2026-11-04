# Hosting options (free or cheap)

> **Current budget is $0** — follow **`docs/DEPLOY.md`** (Render + Neon, step by step). See `docs/FUNDING.md`.
> Our production `Dockerfile` builds ONE container (API + app), so any Docker host works.

ChrystalClear needs three things online: the **app** (backend + frontend), a **Postgres
database**, and **file storage** for photos. Prices change often — check each provider's
current pricing page before signing up.

## Recommended: one small server (~$5/month, predictable)
- **Server:** a small VPS (e.g. Hetzner, DigitalOcean, Vultr) running our Docker Compose
  setup — backend, frontend, and Postgres all on one machine.
- **Photos:** Cloudflare R2 (free tier includes several GB and no download fees).
- **Domain + HTTPS + caching:** Cloudflare (free plan) in front of the server.
- **Why:** one bill, no "sleeping" app, no surprise limits. Easy to move later.
- **Owner does:** create the VPS account and a Cloudflare account, buy a domain (~$10–15/yr).

## Fully free (good for a demo, has limits)
- **Frontend:** Cloudflare Pages (free).
- **Backend:** Render free web service (falls asleep when idle, ~30–60s to wake up).
- **Database:** Neon or Supabase free Postgres (small storage cap; Supabase pauses idle projects).
- **Photos:** Cloudflare R2 free tier.
- **Trade-off:** slow first load after idle time; storage caps you'll outgrow.

## Also possible
- **Oracle Cloud "Always Free"** ARM VM — generous free server, but signup can be finicky.
- **Fly.io / Railway** — easy deploys, small monthly cost (no meaningful free tier for new accounts).

## Email (needed for account verification and password resets)
Any SMTP provider with a free tier, e.g. Resend, Brevo, or Amazon SES. In local dev,
emails are printed to the console instead of being sent.

A step-by-step deploy guide will be added when v0.1 is ready to go live.
