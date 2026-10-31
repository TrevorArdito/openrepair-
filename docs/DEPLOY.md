# Put ChrystalClear online for free (step by step)

Total cost: **$0**. Time: about 30–45 minutes. No credit card should be needed for the
services below at the time of writing — if a sign-up page asks for one, stop and tell
Claude; we'll pick another option. Plans and limits change, so glance at each pricing page.

What you'll set up:
1. **Neon** — the free database (where accounts, guides and specs are stored).
2. **Render** — the free web host that runs the app.
3. (Optional, for real emails) **Brevo** — free email sending for "confirm your email" and
   "reset password" messages.
4. (Optional) A **GitHub secret** so recalls/TSBs refresh automatically every week.

> **Before you start:** Render deploys from a branch of your GitHub repo. Our work lives on the
> branch `claude/openrepair-project-setup-06acm5`. Either pick that branch in Render, or ask
> Claude to open a pull request so you can merge it into `main` (recommended — the weekly data
> refresh only runs from `main`).

---

## 1. Create the database (Neon)

1. Go to **neon.com** → **Sign up** (you can sign in with your GitHub account).
2. Create a project. Name: `chrystalclear`. Region: the US region closest to you.
3. On the project dashboard click **Connect**. Copy the **connection string**. It looks like
   `postgresql://user:password@ep-something.us-east-2.aws.neon.tech/neondb?sslmode=require`
4. Keep it somewhere private (it's a password). You'll paste it in step 2.

Free plan (per Neon's site, Oct 2026): 0.5 GB storage per project, 100 compute-hours a month,
and the database sleeps after 5 minutes idle (it wakes up automatically).

## 2. Create the website (Render)

1. Go to **render.com** → **Get Started** → sign up **with GitHub** and allow access to the
   `openrepair-` repository.
2. In the Render dashboard: **New +** → **Blueprint**. Pick the `openrepair-` repo (and the branch,
   see the note above). Render reads our `render.yaml` and shows one service: `chrystalclear`.
3. It asks for three values:
   - `DATABASE_URL` → paste the Neon connection string.
   - `PUBLIC_BASE_URL` → `https://chrystalclear.onrender.com` (if Render shows a different
     address for your service, use that one — no slash at the end).
   - `ADMIN_EMAILS` → the email you'll sign up with. That account becomes the admin.
4. Click **Apply**. The first build takes ~5–10 minutes. When it says **Live**, open the address.
5. **Sign up** on your site with the `ADMIN_EMAILS` email. You're the admin — you'll see
   **Moderation** on the Account page.

If the address Render gave you differs from what you typed for `PUBLIC_BASE_URL`, fix it in
Render → your service → **Environment**, then **Manual Deploy → Deploy latest commit**.

**What "free" means on Render:** the site goes to sleep after ~15 minutes without visitors, and
the first visit after that takes up to a minute to wake it. Upgrading later removes this.

## 3. Real emails (optional but recommended)

Until this is set up, emails (confirm-email and password-reset links) are only written to
Render's log (Render → your service → **Logs**), so password resets need your help.

1. Go to **brevo.com** → sign up for the free plan.
2. Add and confirm a **sender** — your new project Gmail address works.
3. Open **SMTP & API** settings and create an SMTP key. Note the server, port, login and key
   (at the time of writing: server `smtp-relay.brevo.com`, port `587`).
4. In Render → your service → **Environment**, add:
   - `EMAIL_BACKEND` = `smtp`
   - `SMTP_HOST` = the SMTP server
   - `SMTP_PORT` = `587`
   - `SMTP_USER` = your SMTP login
   - `SMTP_PASSWORD` = the SMTP key
   - `EMAIL_FROM` = the sender address you confirmed
   - `REQUIRE_VERIFIED_EMAIL` = `true` (new members must confirm their email before posting — cuts spam)
5. Save — Render redeploys automatically. Test with "Forgot password?" on your site.

## 4. Load every vehicle + keep data fresh automatically (recommended)

1. GitHub → the `openrepair-` repo → **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret**: name `PROD_DATABASE_URL`, value = the Neon connection string.
3. Run it once now: **Actions** → **Data refresh** → **Run workflow**. In about a minute your site
   has every car and light truck since 1984 with its engines (~21,000 vehicles from EPA data,
   plus the heavy-duty diesel trucks from our engine catalog).
4. After that it runs by itself every Monday: updates the vehicle catalog, refreshes recalls and
   complaints for vehicles people have looked up, and imports the newest TSB index.

## 5. Tell Google about the site (free)

1. Go to **search.google.com/search-console** → add your site address.
2. Verify ownership with the **HTML tag** method. Google shows a tag like
   `<meta name="google-site-verification" content="AbC123..." />`. Copy only the part inside
   `content="..."`. In Render → your service → **Environment**, add
   `GOOGLE_SITE_VERIFICATION` = that value. After the redeploy, click **Verify** in Google.
3. Submit the sitemap: `https://<your-address>/sitemap.xml`.

---

## Limits to watch (and what to do)
| Limit | When it matters | What to do |
|---|---|---|
| Site sleeps when idle (Render free) | First visit after 15 min is slow | Upgrade the Render plan when there's money, or move to a ~$5/month server (docs/HOSTING.md) |
| 0.5 GB database (Neon free) | Roughly a few thousand photos, or a very large TSB import | Move photos to Cloudflare R2 (free 10 GB) — planned in TODO.md — or upgrade Neon |
| 300 emails/day (Brevo free, at time of writing) | Only with lots of sign-ups | Upgrade or add a second provider |

## Updating the site
Every push to the deployed branch redeploys automatically. Database changes are applied on
startup (`alembic upgrade head`), and built-in content is added without overwriting edits.
