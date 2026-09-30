# Deploying Debut (SaaS edition)

This is the step-by-step to go from "folder on my laptop" to "customers can sign up and pay".
Do the steps in order. Budget roughly a weekend for steps 1–6, plus a few days waiting on Razorpay KYC.

## 0. What you have

| Layer | Choice |
|---|---|
| App | Flask, server-rendered pages, gunicorn |
| Database | PostgreSQL in production, SQLite for local dev (same code, tested on both) |
| Multi-tenancy | Every row carries `workspace_id`; every query is filtered by it (tests prove isolation) |
| Auth | Email + password (hashed), email verification, password reset, invites, roles |
| Roles | owner, admin, **lead** (team lead), manager, creator (limited), viewer (read-only, for clients) |
| Industries | 14 tailored modes (personal brand, D2C, FMCG, B2B, SaaS, startup, hospitality, retail, real estate, education, healthcare, fashion, fintech, agency) + general: kits, AI tasks, Idea Bank and niche modules |
| Collaboration | Comments + @mentions, notifications, approvals, Team hub, daily digest email (needs a daily cron: `python manage.py send-digests`) |
| Integrations | Lead form + webhook (all plans), REST API keys (Team/Agency), calendar feed, shareable client report, installable mobile app (PWA) |
| Security | Two-factor login (required for platform admin in production), roles, CSRF, rate limits, audit log |
| Group mode | Team lead role, team hub (workload, approvals), creators cannot self-approve. A paid feature (Team/Agency) |
| You (platform owner) | `/admin`: all workspaces and users, MRR, plan control, read-only support view of any customer workspace |
| Billing | **Free forever plan** + Razorpay Subscriptions for 3 paid plans. New workspaces get a 14-day trial of everything, then fall back to Free |
| Limits | Per plan: seats, AI credits per month, record count, feature access |
| Security | CSRF, rate limits, SSRF-safe feed fetching, upload validation, security headers, audit log |

## 1. Run it locally first

Windows: double-click **Launch Debut.bat** (first run installs everything). Open http://127.0.0.1:8001.
Local mode uses SQLite and **demo billing** (plan switches are instant, no payment). Verification / reset / invite
links are shown as a message on screen because no email server is configured.

Run the tests any time: `pip install pytest` then `python -m pytest tests`.
To test against Postgres: `TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost/dbname python -m pytest tests`.

## 2. Accounts you need to create

1. **Hosting** – Render (easiest), Railway, Fly.io, or any VPS with Docker.
2. **Domain** – e.g. `app.yourbrand.in`.
3. **Email sending** – Amazon SES, Resend, Postmark, Brevo etc. (any SMTP). Add SPF + DKIM DNS records or your emails land in spam.
4. **Razorpay** – create the account, complete KYC (takes days; start now).
5. **Anthropic API key** – for AI Studio. You pay per use; the credit limits per plan protect your margin.
6. *(Optional)* Sentry (errors), Cloudflare R2 or AWS S3 (images), Redis (rate limits across instances).

## 3. Deploy

### Option A: Render (managed, least work)
1. Put this folder in a private GitHub repo (`.env` is git-ignored; never commit secrets).
2. Render → **New → Blueprint** → pick the repo. `render.yaml` creates the web service and Postgres. **It defaults to Render's free plan** so anyone can test-deploy at no cost (see `docs/Debut-Deploy-Online-Free.md`) — for a real paying-customer launch, change `plan: free` to a paid plan for both, and add a persistent disk (or S3 — see §2 above) for uploads, since the free plan supports neither. Check Render's current plan names/prices before applying either way.
3. Fill in the environment variables it asks for (see section 4). `SECRET_KEY` is generated for you.
4. After the first deploy, open the URL, sign up with the email you put in `ADMIN_EMAILS`. You now see **Admin** in the sidebar.
5. Add your custom domain in Render and set `APP_URL` to it (https).

### Option B: Any VPS with Docker
```
cp .env.example .env        # edit: APP_ENV=production, SECRET_KEY, DB_PASSWORD, APP_URL, DOMAIN ...
docker compose --profile https up -d --build
```
Caddy fetches HTTPS certificates automatically once `DOMAIN` points at the server.

### Option C: Railway / Heroku-style
`Procfile` is included (`web: sh start.sh`). Add a Postgres plugin and set the same environment variables.

Every deploy runs `python manage.py init-db` (creates tables, adds new columns) and then starts gunicorn.

## 4. Environment variables (see `.env.example` for the full annotated list)

| Variable | Notes |
|---|---|
| `APP_ENV=production` | Turns on secure cookies, HSTS, and trusts your proxy's HTTPS headers (needed behind Render or any load balancer). Demo billing is a separate, independent setting — it stays on automatically until you set real `RAZORPAY_*` keys, in production or not. |
| `SECRET_KEY` | **Required.** The app refuses to start without it in production. |
| `DATABASE_URL` | Postgres URL. `postgres://` and `postgresql://` are both accepted. |
| `APP_URL` | Public https URL, used in emails. |
| `ADMIN_EMAILS` | Your email(s): unlock the `/admin` console once the email is verified (`python manage.py verify-user you@x.com` if email isn't set up yet). |
| `SMTP_*` | Without these, no email is sent (users cannot verify/reset/get invites). |
| `ANTHROPIC_API_KEY` | AI Studio. |
| `RAZORPAY_*` | See section 5. |
| `COMPANY_NAME`, `SUPPORT_EMAIL` | Shown in Terms/Privacy/footer. |
| `S3_*` | Recommended for images if your host has no persistent disk. |
| `REDIS_URL` | Recommended when running >1 instance so rate limits are shared. |

## 5. Razorpay subscriptions

1. Use **Test Mode** first. Copy the test Key ID and Key Secret into `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`.
2. In the Razorpay dashboard create three **Plans** (Subscriptions → Plans): billing period *monthly*, interval 1, one each for Starter, Team, Agency.
   The amounts must match `PLANS` in `config.py` (currently ₹999 / ₹3,999 / ₹9,999 – **change these to your real prices**).
   **GST:** Razorpay charges exactly the plan amount. Decide with your CA whether prices are GST-inclusive (then set `PRICE_NOTE=incl. GST`)
   or you add 18% into the plan amount (then leave `PRICE_NOTE=+ GST` and create plans at price × 1.18).
3. Put each plan's ID (`plan_XXXX`) in `RAZORPAY_PLAN_STARTER`, `RAZORPAY_PLAN_TEAM`, `RAZORPAY_PLAN_AGENCY`.
4. Create a **Webhook** pointing to `https://YOUR-DOMAIN/webhooks/razorpay`, choose a secret (put it in `RAZORPAY_WEBHOOK_SECRET`) and enable the `subscription.*` events
   (authenticated, activated, charged, pending, halted, cancelled, completed, paused, resumed).
5. Test end to end with Razorpay's test cards/UPI: sign up → Billing → choose a plan → pay → the plan should flip to active. Try cancelling. Check the webhook log in the Razorpay dashboard shows 200.
6. When KYC is approved, swap in **Live** keys, live plan IDs and a live webhook secret.

How access is decided (`services.plan_key`): trial running → all features; paid and status active/authenticated/pending (or cancelled but still inside the paid period) → that plan;
anything else (trial over, payment halted/paused, subscription ended) → the **Free** plan. Nothing is ever deleted on downgrade:
paid-only modules lock (data kept, comes back on upgrade), existing records stay editable/deletable/exportable but new ones stop at the Free limit,
and members beyond the Free seat count are paused until the owner upgrades or removes them.

**The Free plan** (edit in `config.py` → `PLANS["free"]`): 1 seat, 100 records, 3 mood boards, 5 AI credits/month, all core planning tools
(calendar, GTM plans, personas, competitors, brand kit, launch checklist, tasks, campaigns, leads, references, news feed, UTM builder).
Locked on Free: influencer discovery & outreach, KPIs/analytics, CSV import, Content Ops, Promotions & events.
Tune these limits to steer people to paid plans: too generous and nobody upgrades, too tight and nobody adopts. Watch the **Free workspaces** tile in `/admin`.

## 6. Before you take real customers

- [ ] Lawyer reviews **Terms** and **Privacy** (`templates/terms.html`, `privacy.html` are templates, clearly marked). Cover DPDP Act 2023 duties, refund policy, jurisdiction.
- [ ] GST registration and invoicing process decided with your CA.
- [ ] SMTP working: sign up with a fresh email and confirm the verification mail arrives (not in spam).
- [ ] Razorpay live mode payment tested with a real ₹ amount, then refunded.
- [ ] Sign up two accounts and confirm they cannot see each other's data (the test-suite checks this, but look yourself).
- [ ] Backups: enable your database provider's automatic backups, and/or schedule `deploy/backup.sh`. **Do a test restore.**
- [ ] Uptime monitor (UptimeRobot etc.) on `https://YOUR-DOMAIN/health`. Set `SENTRY_DSN` for error alerts.
- [ ] A support email address that someone actually reads.
- [ ] Rotate any secret that was ever pasted in chat or committed to git.

## 6b. Roles, group mode and your own access

**Who can do what** (also shown in-app under Team & roles):

| | owner | admin | **lead** | manager | creator | viewer |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| View all marketing data | ✓ | ✓ | ✓ | ✓ | limited | ✓ |
| Edit marketing data | ✓ | ✓ | ✓ | ✓ | limited | – |
| Approve / publish content | ✓ | ✓ | ✓ | ✓ | – | – |
| Team hub (workload, approvals), activity log | ✓ | ✓ | ✓ | – | – | – |
| Invite / change / remove people | all below owner | below admin | managers, creators, viewers | – | – | – |
| Export data | ✓ | ✓ | ✓ | ✓ | – | – |
| Billing, plan, industry, rename | ✓ (admin can view billing) | – | – | – | – | – |
| Delete workspace | ✓ | – | – | – | – | – |

Rule: nobody can create, change or remove a role equal to or above their own, and nobody can promote themselves.
**You** (platform owner): put your email in `ADMIN_EMAILS`, sign up with it, and use **Admin** in the sidebar. From there you can open any customer workspace in a strictly
read-only *support view* (each use is written to that customer's activity log, and the Privacy Policy discloses it), change plans, extend trials and mark emails verified.
Group mode (Lead role, Team hub) belongs to the `group` feature in `config.py`: Team and Agency plans have it; Free and Starter do not.

## 6c. Industry starter kits

Each workspace has an industry (chosen at signup, changeable in Account). It drives: extra launch-checklist items, key dates, news feeds (Google News searches per industry),
a KPI scorecard, persona templates, the Idea Bank (content and campaign ideas with one-click add), and extra context for the AI. Everything lives in `industries.py` as plain data:
edit or add industries there. `test_industry_data_is_valid` checks every value against the app's dropdowns so a typo can't ship. Dates marked "approx." are moving or regional; review them for your market.

## 7. Running the business

- **/admin** shows MRR, paying/trial counts and every workspace; extend a trial by 14 days or comp a plan.
- `python manage.py list | set-plan <slug> <plan> | extend-trial <slug> <days>` from a shell on the server.
- **Activity** page (per workspace) is the audit log; **Export data** downloads everything as CSVs; owners can delete their workspace.
- Suggested go-to-market from earlier: sign 3–5 paying agencies/brands by hand first (comp plans via admin), learn what they actually use, then open signup publicly.

## 8. Known limitations (be aware, then fix as you grow)

- **Team hub matching**: tasks and content are matched to people by the name/email typed in the assignee/owner field (forms suggest team names). Free-text matching is simple, not an ID link.
- **Free plan cost**: every free workspace can spend up to 5 AI credits/month on your Anthropic key and uses database/disk space; keep the limits modest and watch usage.
- **Plan changes while subscribed**: to switch between paid plans a customer cancels and re-subscribes (or you change it in `/admin` and in Razorpay). Proration via the Razorpay update-subscription API is not built.
- **Razorpay flow was written from the API docs and unit-tested with simulated signatures/webhooks; it has not been run against Razorpay's live servers.** Test in Test Mode (step 5) before launch.
- ~~S3 storage and SMTP email code paths are written but were not exercised in the test suite~~ — fixed and now covered by dedicated tests: `send_email` no longer assumes every SMTP server offers STARTTLS on every port (it used to crash against servers that don't advertise it, and never supported port 465's implicit TLS at all); S3 upload/fetch/delete is tested end-to-end against a mocked client. Both still deserve one real test against your actual SMTP/S3 provider before launch, same as anything running for the first time against a live third party.
- Email verification is encouraged (banner) but **not required** to use the app.
- No 2FA/SSO yet. Passwords are hashed (scrypt via Werkzeug); login is rate-limited.
- Content-Security-Policy only sets `frame-ancestors/base-uri/object-src` because pages use inline scripts; moving scripts to files would allow a strict CSP.
- Feed URLs are fetched server-side with private-network blocking (SSRF guard) but a DNS-rebinding race remains theoretically possible; keep the web service on a network without access to internal admin endpoints.
- Schema upgrades are **additive** (new fields become new columns automatically). Renaming/removing columns needs a manual migration; move to Alembic when you start doing that.
- Rate limiting uses per-process memory unless `REDIS_URL` is set.
- News feeds are fetched on demand (15-minute cache per workspace), not by a background worker.
- Sending email happens inside the request; if your SMTP is slow, signups feel slow. Move to a queue if it matters.

## 9. Repo map

```
app.py         app factory, request guard (auth, roles, plan, feature gating), security headers
config.py      env config and PLANS (edit prices, seats, credits, limits here)
db.py          SQLAlchemy layer that runs on SQLite and PostgreSQL, additive schema upgrades
modules.py     the marketing modules (tables/forms), AI prompts, seed data
services.py    plan checks, audit log, email, SSRF guard, file storage, workspace seeding
auth.py        signup/login/reset/verify/invites      billing.py  Razorpay + demo billing
workspace.py   team, activity, account, export, delete   admin.py  platform console
views.py       all product screens, scoped by workspace
tests/         pytest suite (isolation, roles, billing, security, workflows)
```
