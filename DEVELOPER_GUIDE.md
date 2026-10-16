# Debut: Developer Deployment Guide

**Audience:** the developer / DevOps person deploying Debut to production.
**Goal:** a secure, monitored, paid-subscription SaaS running on a real domain, with backups.
**Time:** about 1 day for a test deployment; 2–4 more days if Razorpay KYC and DNS/email verification are still pending.

Everything below was checked against the code in this repo. Where something was **not** tested against a live third-party service, it is marked ⚠️.

---

## 1. What you are deploying

| Item | Detail |
|---|---|
| App | Python 3.12, Flask 3, server-rendered HTML (no separate frontend build, no Node needed) |
| Web server | gunicorn (3 workers × 2 threads by default), behind one HTTPS reverse proxy |
| Database | **PostgreSQL 14+** in production (tested on 16). SQLite only for local dev. |
| Services | ONE web service + ONE Postgres + one small daily cron job (digest emails). Optional: S3-compatible bucket, Redis, Sentry. |
| Auth | Own email + password auth, sessions in signed cookies (no session store needed) |
| Billing | Razorpay Subscriptions (INR). Free plan + 3 paid plans. |
| AI | Anthropic API (metered per plan) |
| Multi-tenant | Every row has `workspace_id`; tenant isolation is covered by tests |
| Product modes | 14 industry modes + general (personal brand, B2B, D2C, FMCG, startup, SaaS, hospitality, retail, real estate, education, healthcare, fashion, fintech, agency): tailored kits, AI tasks and modules |
| Collaboration | Comments with @mentions, in-app notifications, approvals, Team hub, daily email digest (cron) |
| Integrations | Lead-capture form + website webhook (all plans); REST API with keys (Team/Agency); calendar feed; shareable client report |
| Security | Roles incl. Team Lead, CSRF, rate limits, **two-factor login (TOTP)**, SSRF guard, upload sniffing, audit log |
| Branding | App name comes from `APP_NAME` (default **Debut**); logo is `static/icons/`; theme colours are CSS variables at the top of `static/style.css` |
| Mobile | Installable PWA (Android/iOS home screen), mobile menu; no native app |

**Architecture in one line:** Browser → HTTPS proxy (Render / Caddy / Cloudflare) → gunicorn (`wsgi:app`) → PostgreSQL.
Outbound calls: SMTP, Razorpay API, Anthropic API, RSS feeds (users' feed URLs), optional S3.

### Repo map

```
app.py         app factory, request guard (auth → role → seats → feature gating), security headers
config.py      ALL configuration and the PLANS table (prices, seats, AI credits, limits, features)
db.py          SQLAlchemy layer: same SQL on SQLite/PostgreSQL, auto schema creation + additive migrations
modules.py     marketing modules (tables/forms), AI prompts, seed data
industries.py  14 industry kits + which niche modules each industry sees (plain data)
services.py    plan checks, audit log, email, SSRF guard, file storage, workspace seeding
auth.py        signup / login (+ two-factor step) / reset / verify / invites
totp.py        TOTP two-factor codes (RFC 6238, no external library)
api.py         REST API v1 (bearer API keys, CSRF-exempt blueprint)
billing.py     Razorpay subscribe / verify / cancel / webhook (+ demo mode for non-production)
workspace.py   team & roles, activity, account, 2FA, integrations/API keys, export, delete workspace
admin.py       platform-owner console at /admin (+ read-only support view)
views.py       all product screens
templates/     ~45 HTML pages       static/  CSS, vendored Chart.js, PWA icons
tests/         pytest suite (131 tests)
docs/          customer guides (PDF) and this developer guide
Launch Debut.bat  Windows one-click local launcher
deploy/        Caddyfile, backup.sh
```

---

## 2. Before you start: what the owner must give you

| From the owner | Used for |
|---|---|
| Domain name + DNS access | e.g. `app.theirbrand.in` |
| The email address to make platform admin | `ADMIN_EMAILS` |
| Company legal name, support email | `COMPANY_NAME`, `SUPPORT_EMAIL` (shown in Terms, Privacy, footer) |
| Razorpay account (KYC complete for live) | payments |
| Final prices, and whether they include GST | `config.py` → `PLANS`, `PRICE_NOTE` |
| Anthropic API key | AI Studio |
| Transactional email account (SES / Resend / Postmark / Brevo) | verification, reset, invites |
| Lawyer-reviewed Terms & Privacy text | replace `templates/terms.html`, `templates/privacy.html` (currently marked TEMPLATE) |

You (developer) create: hosting account, Postgres, storage bucket (if used), Sentry (optional), uptime monitor.

---

## 3. Verify locally first (30 min)

```bash
python3.12 -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt pytest
python -m pytest -q tests                                # expect: 131 passed (SQLite)
python app.py                                            # http://127.0.0.1:8001 (dev mode, demo billing)
```

Note: `requirements.txt` deliberately does **not** include the PostgreSQL driver (`psycopg2-binary`), so a plain local/SQLite setup — including the Windows `Launch Debut.bat` path — never needs a C compiler or Postgres client libraries. It lives in its own `requirements-postgres.txt`, installed automatically by the Dockerfile and required any time you actually connect to Postgres (production, or the test run below).

Run the suite against Postgres too (recommended):

```bash
pip install -r requirements-postgres.txt
docker run -d --name pgtest -e POSTGRES_USER=gtm -e POSTGRES_PASSWORD=gtm -e POSTGRES_DB=gtm_test -p 5432:5432 postgres:16
TEST_DATABASE_URL=postgresql+psycopg2://gtm:gtm@localhost:5432/gtm_test python -m pytest -q tests   # expect: 131 passed
```

> ⚠️ **NEVER set `TEST_DATABASE_URL` to a real database.** The test fixture runs `TRUNCATE ... CASCADE` on every table.

---

## 4. Configuration (environment variables)

The app reads env vars (and a local `.env` file, which is git-ignored). Full annotated template: `.env.example`.

### Required in production

| Variable | Value / notes |
|---|---|
| `APP_ENV` | `production` → secure cookies, HSTS, ProxyFix, demo billing disabled |
| `SECRET_KEY` | 64 hex chars: `python -c "import secrets;print(secrets.token_hex(32))"`. **The app refuses to start without it in production.** |
| `DATABASE_URL` | `postgresql+psycopg2://user:pass@host:5432/db` (`postgres://` and `postgresql://` are auto-converted). If the provider requires TLS, append `?sslmode=require`. |
| `APP_URL` | Public **https** URL, no trailing slash. Used in emails and calendar links. |
| `ADMIN_EMAILS` | Comma-separated. A user with one of these emails gets `/admin` **once their email is verified** (so nobody can take admin by registering the owner's address first). |
| `COMPANY_NAME`, `SUPPORT_EMAIL` | Legal pages and footer |

### Strongly recommended

| Variable | Notes |
|---|---|
| `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Uses STARTTLS on the given port. Without SMTP **no email is sent** in production (verification, password reset, invites all break). |
| `ANTHROPIC_API_KEY`, `GTM_MODEL` | Default model string is in `config.py`; confirm it is available on your key, else set `GTM_MODEL`. |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | See §7 |
| `RAZORPAY_PLAN_STARTER`, `RAZORPAY_PLAN_TEAM`, `RAZORPAY_PLAN_AGENCY` | Razorpay plan IDs (`plan_XXXX`) |
| `REQUIRE_ADMIN_2FA` | Default **on in production**: the platform admin must have two-factor login enabled to reach `/admin` (§9d). Set `0` only temporarily. |
| `PRICE_NOTE` | `+ GST` or `incl. GST`. Text next to prices; **must match what your Razorpay plans actually charge.** |

### Optional

| Variable | Notes |
|---|---|
| `S3_BUCKET`, `S3_REGION` (ap-south-1), `S3_ENDPOINT` | Image storage. Credentials via the standard AWS env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) or an instance role. Use `S3_ENDPOINT` for Cloudflare R2 / other S3-compatible. |
| `UPLOAD_DIR` | Local upload path when S3 is not used (Docker default `/data/uploads`). Must be a **persistent volume**. |
| `REDIS_URL` | Shared rate-limit counters. Needed when running more than one process/instance for accurate limits. |
| `SENTRY_DSN` | Error monitoring (`sentry-sdk` is in `requirements-extras.txt`, installed in the Docker image). |
| `SUPPORT_PHONE`, `SUPPORT_HOURS`, `COMPANY_ADDRESS`, `COMPANY_GSTIN`, `GRIEVANCE_OFFICER`, `GRIEVANCE_EMAIL` | Business identity shown on the **Contact**, **Refund** and **Privacy** pages and the footer. Payment gateways (Razorpay) review these pages, so fill them **before** applying for live payments. |
| `REFUND_WINDOW_DAYS` | Days (default 7) quoted in the Refund policy page. Must match your written policy. |
| `GA_MEASUREMENT_ID` | Optional Google Analytics 4 id, loaded on **public marketing pages only** (never inside the signed-in app). Mention it in the privacy policy (the page does this automatically when set). |
| `AI_DAILY_CAP` | **Launch budget guard.** Platform-wide AI credits per day across all customers (0 = off). When reached, AI Studio politely refuses until the next day. Set it during launch week. |
| `MAINTENANCE` | `1` shows a "being updated" page (HTTP 503) to everyone except the verified platform admin; `/health` and the Razorpay webhook keep working. Use for risky deploys/migrations. |
| `NEWS_PROVIDER`, `GNEWS_API_KEY`, `NEWSDATA_API_KEY` | Where Market Pulse gets news. Default `google_rss` (free; fine for the pilot). **Move to `gnews` or `newsdata` (licensed APIs) before you scale or charge customers.** |
| `YOUTUBE_API_KEY` | Optional. Google Cloud > enable *YouTube Data API v3* > create a key. Adds trending videos per keyword (official API, free daily quota). |
| `PULSE_HN`, `PULSE_TRENDS`, `PULSE_REDDIT` | Toggles for Hacker News (tech industries only), Google's daily trending-searches feed, and Reddit feeds (**off by default**). |
| `PULSE_CACHE_MINUTES`, `PULSE_MIN_REFRESH_MINUTES` | Freshness window (60) and the minimum gap between manual refreshes (10). |
| `AI_WEB_SEARCH`, `AI_RESEARCH_EXTRA` | Enables AI Studio live web research (needs **web search enabled in the Anthropic console**) and the extra credits a research answer costs (2). |
| `WEB_CONCURRENCY` | gunicorn workers (default 3). Read by `start.sh`. |
| `TRIAL_DAYS` | Default 14 |
| `APP_NAME` | Default "Debut" |
| `BILLING_MODE` | Leave unset. Auto: `razorpay` if a key is set; otherwise `demo`. `demo` and `PROD` (needed behind any reverse proxy, Render included) are deliberately independent — `demo` works the same in production as in dev, so a proxied deployment with no Razorpay keys yet still has a working Billing page. Set `BILLING_MODE=off` yourself if you want it hidden instead. |

> `SECRET_KEY` also signs password-reset, email-verification and calendar-feed links. **Changing it logs everyone out and invalidates those links.** It must be identical on every instance.

---

## 5. Choose a deployment path

All paths run the same command: `sh start.sh` = `python manage.py init-db` (create/upgrade schema) then gunicorn.

### Option A: Render (managed, least effort)

1. Push the repo to a private GitHub repository.
2. Render → **New → Blueprint** → select the repo. `render.yaml` defines the web service (Docker) and a Postgres database.
   ⚠️ **The `render.yaml` shipped in this repo defaults to Render's free plan on purpose**, so anyone can spin up a working test deployment with no card and no cost (see `Debut-Deploy-Online-Free.md`). Before real production use, change `plan: free` to a paid plan (e.g. `starter`) for **both** the web service and the `gtm-db` database in Render's dashboard: the free database expires after 30 days, the free web service sleeps after 15 minutes idle, and neither supports a persistent disk. For uploads to survive restarts in real production, either add a paid disk (`disk: {name: uploads, mountPath: /data/uploads, sizeGB: 1}` under the web service, plus `UPLOAD_DIR=/data/uploads` as an env var) or configure S3 (§4, `S3_BUCKET`) instead — Render's own plan names and prices change over time, so check current values before applying regardless.
3. Fill in the environment variables it prompts for (§4). `SECRET_KEY` is generated.
4. Health check path is `/health` (already set).
5. After deploy, add the custom domain in Render, set `APP_URL` to it, redeploy.
6. **Limitation:** a Render persistent disk attaches to one instance, so with the disk you cannot scale horizontally. For multiple instances, use S3 (`S3_BUCKET`) and Redis (`REDIS_URL`) and remove the disk.

### Option B: One VPS with Docker Compose

```bash
git clone <repo> && cd <repo>
cp .env.example .env         # set: APP_ENV=production, SECRET_KEY, DB_PASSWORD, APP_URL, DOMAIN, ADMIN_EMAILS, etc.
docker compose --profile https up -d --build
docker compose logs -f web
```

- Services: `db` (Postgres 16, volume `pgdata`), `web` (port bound to 127.0.0.1:8000), `caddy` (automatic HTTPS for `$DOMAIN`, needs DNS pointing at the server and ports 80/443 open).
- `docker-compose.yml` builds `DATABASE_URL` from `DB_PASSWORD`, so you do not set `DATABASE_URL` in `.env` for this path.
- Uploads live in the `uploads` volume: back it up too, or use S3.

### Option C: Railway / Heroku-style

`Procfile` = `web: sh start.sh`. Add a Postgres add-on (it provides `DATABASE_URL`), set the other variables. Same S3/Redis advice for multi-instance.

### Scheduled job: daily digest email (all paths)

`python manage.py send-digests` emails each verified user who has not opted out, **only if** something needs them (overdue/upcoming tasks assigned to them, content publishing in 3 days, approvals waiting). Schedule it once a day, e.g. **02:30 UTC = 08:00 IST**, with the *same environment variables* as the web service:

- **Render:** create a *Cron Job* from the same repo, command `python manage.py send-digests`, schedule `30 2 * * *`.
- **Docker Compose / VPS:** host crontab `30 2 * * *  cd /path/to/app && docker compose exec -T web python manage.py send-digests`.
- **Railway / Heroku-style:** a scheduler add-on running the same command.
Without SMTP (§8) it sends nothing. Every digest carries a one-click unsubscribe link; users can also toggle it under Account.

### Reverse proxy requirements (all paths)

- The app applies `ProxyFix(x_for=1, x_proto=1, x_host=1)` in production: it trusts **exactly one** proxy hop for the client IP, scheme and host. If you put Cloudflare **and** another proxy in front, change `x_for` in `app.py` to the real hop count, otherwise rate limits will key on the wrong IP.
- The proxy must forward `X-Forwarded-For`, `X-Forwarded-Proto` and `Host`, and pass the **raw request body** unchanged on `/webhooks/razorpay` (the signature covers the raw body).
- Terminate TLS at the proxy. Cookies are `Secure`, so plain HTTP will not keep users logged in.
- `start.sh` runs gunicorn with `--forwarded-allow-ips="*"`. This is safe **only** when the container port is not publicly exposed (Compose binds it to 127.0.0.1; on Render the platform proxy is in front).

---

## 6. First-boot verification (10 min)

Replace `$URL` with your site:

```bash
curl -s  $URL/health                       # {"status":"ok"}
curl -sI $URL/ | egrep -i "HTTP/|strict-transport|x-frame|x-content-type|content-security"
curl -s -o /dev/null -w "%{http_code}\n" $URL/app          # 302 (redirect to login)
curl -s $URL/manifest.webmanifest | head -c 200            # installable-app manifest (JSON)
curl -sI $URL/sw.js | egrep -i "HTTP/|content-type|service-worker"   # service worker, JavaScript, Service-Worker-Allowed: /
curl -s -o /dev/null -w "%{http_code}\n" $URL/api/v1/leads   # 401 (API needs a key)
curl -s -o /dev/null -w "%{http_code}\n" -X POST -d "email=a@b.c&password=x" $URL/login   # 400 (CSRF blocks tokenless POST)
```

Then in a browser (register the owner's admin email **first**, before announcing the URL):

1. Sign up with the email in `ADMIN_EMAILS`. Confirm the **verification email arrives** (§8) and click it. Admin access only works after the email is verified. If SMTP isn't ready yet, run `python manage.py verify-user owner@theirbrand.in` on the server to unlock admin.
2. Sidebar shows **Admin**. Open it: workspace list, MRR tiles.
3. **Turn on two-factor login** for this account (Account → Two-factor login) and save the recovery codes. In production `/admin` stays hidden until you do (§9d). The sidebar shows "Turn on 2FA to unlock Admin" until then.
4. Confirm the session cookie is `Secure; HttpOnly; SameSite=Lax` (DevTools → Application → Cookies).
5. Check logs for errors: there should be none at startup.

---

## 7. Razorpay subscriptions (do in Test Mode first)

### 7.1 Setup

1. Razorpay Dashboard → Test Mode. Copy **Key ID** and **Key Secret** → `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`.
2. Create **3 Plans** (Subscriptions → Plans): period *monthly*, interval *1*, one each for Starter, Team, Agency. Amount must equal the price in `config.py` `PLANS` (defaults ₹999 / ₹3,999 / ₹9,999 — **owner must confirm the final prices**). In the dashboard you enter rupees; via API it would be paise.
   - **GST:** Razorpay charges exactly the plan amount. Either prices are GST-inclusive (`PRICE_NOTE=incl. GST`) or plan amount = price × 1.18 (`PRICE_NOTE=+ GST`). Get the owner's accountant to decide.
3. Put plan IDs in `RAZORPAY_PLAN_STARTER|TEAM|AGENCY`.
4. Create a **Webhook**: URL `https://YOUR-DOMAIN/webhooks/razorpay`, a random secret → `RAZORPAY_WEBHOOK_SECRET`, events: `subscription.authenticated`, `.activated`, `.charged`, `.pending`, `.halted`, `.cancelled`, `.completed`, `.paused`, `.resumed`.
5. Redeploy so env vars load. On `/billing` the plan buttons should now open Razorpay Checkout.

### 7.2 How the code works (so you can debug it)

| Step | Endpoint | What happens |
|---|---|---|
| Choose plan | `POST /billing/subscribe/<plan>` (owner only) | Creates a Razorpay subscription (`total_count=120`, `customer_notify=1`, notes with workspace id), stores `rzp_subscription_id` + `pending_plan`, returns checkout params |
| After payment | `POST /billing/verify` | Verifies `HMAC_SHA256(key_secret, payment_id + "|" + subscription_id)` against `razorpay_signature`, then marks the plan active |
| Lifecycle | `POST /webhooks/razorpay` (CSRF-exempt) | Verifies `X-Razorpay-Signature` = `HMAC_SHA256(webhook_secret, raw_body)`; de-duplicates using `X-Razorpay-Event-Id` (table `webhook_events`); maps `subscription.*` events to `plan_status` and `period_end` |
| Cancel | `POST /billing/cancel` | Calls Razorpay cancel with `cancel_at_cycle_end=1`; plan stays active until `period_end` |

**Access rules** (`services.plan_key`): trial running → all features; paid and status `active`/`authenticated`/`pending` (or `cancelled`/`completed` but still inside the paid period) → that plan; anything else (trial over, `halted`, `paused`, subscription ended) → **Free plan**. Nothing is deleted on downgrade.

### 7.3 Test matrix (Test Mode)

| Test | Expected |
|---|---|
| Subscribe with a test card | Plan flips to the chosen plan; features unlock |
| Razorpay dashboard → Webhooks → recent deliveries | All `200` |
| Cancel in app | Banner shows "cancels at period end"; access continues |
| Simulate failed payment / `halted` | Workspace drops to Free next request |
| Replay same webhook | Second delivery answers `duplicate`, no double effect |
| Wrong webhook secret | `400 bad signature` |

### 7.4 Go live

Complete KYC → swap to **Live** key/secret, **live** plan IDs and a **live** webhook + secret → redeploy → make one real ₹ payment on a real card, then refund it.

⚠️ **The Razorpay integration was written from the API docs and verified with simulated signatures/webhooks; it has not been run against Razorpay's servers.** Expect to spend time here.

**Known limitation:** switching between paid plans while subscribed is not implemented (the app tells the user to cancel first, or the owner changes it in `/admin` and in Razorpay). Proration via the update-subscription API is not built.

---

## 8. Email (SMTP)

1. Choose a provider (SES, Resend, Postmark, Brevo). Verify the sending domain.
2. **DNS:** add SPF, DKIM (provider gives records) and a DMARC record, or mail lands in spam.
3. Set `SMTP_*`. `SMTP_FROM` should be an address on the verified domain, e.g. `Debut <no-reply@theirbrand.in>`.
4. Test all four flows: signup verification, password reset, team invite, and that invite links open the app.
5. Behaviour to know: emails are sent **inside the web request** (no queue). A slow SMTP server makes signup slow. If failures occur they are logged and the user just doesn't get the mail.
6. In non-production the app prints links on screen when SMTP is missing; **in production it does not**.

⚠️ The SMTP code path is not exercised by the automated tests (a mock is used); verify it on staging.

---

## 9. File storage (mood-board images)

- **Default:** files are written to `UPLOAD_DIR` and served through the app at `/media/<workspace>/<file>`, only to members of that workspace. On containers this directory **must be a persistent volume**, or images vanish on every deploy.
- **S3 mode** (set `S3_BUCKET`): objects are stored under `<workspace_id>/<uuid>.<ext>` and served through **1-hour presigned URLs**. Keep the bucket **private** (no public access). Minimal IAM policy: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` on `arn:aws:s3:::BUCKET/*`.
- Uploads accept PNG/JPG/GIF/WebP only (content is sniffed; SVG rejected), max 10 MB each; request limit 25 MB.

⚠️ The S3 path is not covered by the automated tests; test upload, display and delete on staging.

---

## 9b. Product modes (industries)

Each workspace has an **industry** (chosen at signup, changeable by owner/admin in Account). It drives the whole product:

| Effect | Where it lives |
|---|---|
| Extra launch-checklist items, key dates, Google-News feeds, persona templates | `industries.py` → applied by `services.apply_industry` (idempotent; "Save & load starter kit") |
| Idea Bank: content ideas, campaign ideas, KPI scorecard (one-click "+ Add") | `industries.py` → `/ideas` |
| Industry-specific AI tasks (e.g. personal-brand profile rewrite, B2B ABM plan, D2C ad concepts, FMCG trade scheme, hospitality review replies) and industry context in every AI prompt | `modules.py` (`AI_TASKS`, `AI_TASK_FOR`) + `industries.py` (`ai_context`) |
| Niche modules shown in the sidebar only for relevant industries: **Opportunities** (speaking/podcasts/media: personal brand, B2B, SaaS, agency, startup), **Target Accounts** (ABM: B2B, SaaS, agency, fintech, startup), **Retail Audits** (FMCG, retail) | `industries.MODULE_INDUSTRIES` (hidden from the menu only: URLs and data remain, so switching industry never loses anything) |
| "Get started" checklist adapts (opportunity / target account / retail audit) | `views.dashboard` |

Modes: general, personal brand, D2C, FMCG, B2B services & manufacturing, B2B SaaS, startup, hospitality, retail & QSR, real estate, education, healthcare, fashion, fintech, agency.

**To add or edit an industry:** edit `industries.py` only (plain data), then run `pytest -k industry_data`: it validates every checklist phase, date, feed category, channel, format, campaign objective and persona field against the app's real dropdown values, so a typo cannot ship. Dates marked "approx." are moving/regional: the owner should review them for their market.
**To add a module:** add an entry to `MODULES` in `modules.py` (tables/columns are created automatically on next start). Optionally add it to `MODULE_INDUSTRIES` and `MODULE_FEATURE` (plan gating).

---

## 9c. Integrations & REST API

All under **Integrations** in the app (owner/admin/lead/manager).

**Lead capture (all plans)**
- Hosted form `https://DOMAIN/lead/<workspace-slug>`: name, email/phone, company, message, **consent checkbox** (required), honeypot field, 10 posts/hour/IP. Creates a lead (`stage=New`, `source=Website form`) and records the consent line in the lead's notes.
- Webhook `POST https://DOMAIN/hooks/lead/<secret-key>` (JSON or form fields: `name`, `email`, `phone`, `company`, `message`, `source`; needs email or phone). It answers CORS (`Access-Control-Allow-Origin: *`, preflight `OPTIONS` supported) so any website form or Zapier/Make can post to it. **CSRF-exempt by design**; protected by the secret key in the URL (96 bits) and a 300/hour/IP rate limit. "Reset webhook URL" rotates the key. The customer is responsible for collecting consent on their own forms.

**REST API v1 (Team & Agency plans: feature `api`)**
- Owner/admin creates a key (Read or Read & write). The key is shown **once**; only its SHA-256 hash is stored. Max 10 keys per workspace; usage date shown.
- `Authorization: Bearer gtm_…`. Endpoints: `GET /api/v1/` (modules + fields), `GET|POST /api/v1/<module>`, `GET|PATCH|DELETE /api/v1/<module>/<id>`. List supports `limit` (max 200), `offset`, `q` (search) and exact filters like `?stage=Won`.
- Same validation as the UI (select values, URLs, lengths); unknown fields ignored; record limits and module plan-gating (e.g. Content Ops) enforced; every write is audit-logged (`api_create/update/delete`).
- Rate limit **300 requests/minute per key**. The blueprint is CSRF-exempt because it never uses cookies.
- Example: push a KPI from a script or Zapier: `curl -X POST https://DOMAIN/api/v1/kpis -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{"metric":"Sessions","period":"2026-09-01","value":"12840","target":"15000"}'`.
- API writes do **not** trigger notifications or the creator "cannot approve" rule (keys are trusted server-to-server credentials).

**Native connectors (Meta Ads, Google Analytics, Instagram publishing, email campaigns) are not built.** The API + Zapier/Make cover reporting inflow today; build first-party connectors on top of `api.py`/`services.py` as customers ask for them.

**Client report** (`/report`, print-to-PDF) and its **read-only share link** `/r/<token>` (Starter+; no login): shows KPIs, campaigns and budget/spend, content, leads, promotions/events and retail audits for a month. The token is signed and tied to the workspace's `ics_key`; **Calendar → Reset link** rotates it (and the calendar feed) instantly. Treat the link as confidential: anyone with it sees budgets.

---

## 9d. Two-factor login and admin security

- Any user can enable TOTP two-factor under **Account → Two-factor login** (works with Google/Microsoft Authenticator, Authy, 1Password): QR code + manual key, confirmation code, then **8 one-time recovery codes** (shown once; stored hashed).
- At login, after a correct password, the user is taken to `/login/2fa` (10-minute window, 10 attempts/15 min). A code cannot be **replayed** (last used time-step is stored). Recovery codes work once each.
- Turning 2FA off needs the password **and** a fresh code.
- **`REQUIRE_ADMIN_2FA`** (default on in production): `/admin` and the support view require the admin email to be verified **and** have 2FA on. First-time flow for the owner: sign up → verify email (or `python manage.py verify-user …`) → enable 2FA → Admin appears.
- **Lost device:** `python manage.py reset-2fa user@email.com` (server shell) clears their 2FA so they can log in with the password and set it up again.
- The TOTP code is implemented in `totp.py` and checked against the RFC 6238 test vector in development. QR codes use the pure-Python `segno` package.

---

## 9e. Installable mobile app (PWA) and mobile layout

- The app is an installable Progressive Web App: `/manifest.webmanifest`, icons in `static/icons/`, service worker at `/sw.js`. Users on Android/Chrome tap **Install app**; on iPhone Safari use **Share → Add to Home Screen**. **HTTPS is required** for install prompts and the service worker (localhost works for testing).
- The service worker caches **only** `/static/*` assets and an offline page; signed-in pages and data are never stored on the device. To force clients to refresh cached assets after a CSS change, bump `V='gtm-v1'` in `SW_JS` (`views.py`).
- On screens ≤800px the sidebar becomes a slide-in menu with a notification bell; tables scroll sideways inside their own container.
- To change the icon/colours: replace the PNGs in `static/icons/` (192, 512, maskable 512, apple-touch 180) and `theme_color`/`background_color` in the `manifest` view.

---

## 9f. Comments, notifications and the digest

- **Comments** appear on every record's edit page. Viewers (internal stakeholders) can comment; creators only within their modules; authors and leads/admins/owners can delete. `@Full Name` or a unique `@FirstName` notifies that teammate; the record's assignee/owner is notified too.
- **Notifications** (bell + `/notifications`) are created when: work is assigned to you (assignee/owner field matches your name/email), someone comments/@mentions you, something is **sent for approval** (owner/admin/lead/manager are told) and when it is **approved** (the item's owner is told). In-app only (no web-push).
- **Approvals rule:** creators can move content to *Review* but not to Approved/Scheduled/Published (or orders to Approved/Delivered/Invoiced): the app sends it to review instead and tells them. Leads/managers approve from the **Team hub**.
- **Daily digest:** see the scheduled job in §5 and `services.digest_text` / `send_digests`.
- Matching people to tasks is by **name/email typed in the assignee/owner field** (the forms suggest team names). It is text matching, not an ID relation.

## 9g. Roles, data visibility and agencies (read before promising anything to customers)

- **Creator (freelancer) role** sees only: content items, Content Library, tasks, references, **content orders**, mood boards, calendar, Idea Bank. On content orders the **client price and creator cost fields are hidden** everywhere for creators (list, form, board, search) and are ignored if forged in a form post (`HIDDEN_FOR_CREATOR` in `modules.py`, enforced in `views.py`; covered by `test_freelancers_never_see_agency_money`). Extend that dict if other fields become sensitive.
- **Viewer role is read-only access to every module on the plan**, including the Clients list, invoices and payouts and creator costs. It is designed for **internal** stakeholders. For **external clients** tell customers to use the read-only **Client report share link** (Starter+) or a separate workspace per client. The in-app roles table and the customer guides say this explicitly.
- For **external clients** the app now has a dedicated **Client** role and a **client portal** (§9i). Do not give clients the Viewer role.
- **Ownership transfer** is built (Account > Transfer ownership, owner only, needs password + 2FA code + typing TRANSFER; the old owner becomes Admin; the new owner is emailed). The subscription stays with the workspace; the new owner should review billing details.
- **2FA is per user**; there is no workspace-wide enforcement. Platform-admin access does require 2FA (`REQUIRE_ADMIN_2FA`).

## 9h. Customer guides (hand these to customers)

Two designed PDFs live in `docs/` and are written for end users, not developers:
- `Debut-Guide-Personal-Branding.pdf`: how one person uses Debut to build a personal brand (setup, first week, AI Studio, opportunities, leads, KPIs, weekly rhythm).
- `Debut-Guide-Agencies-and-Teams.pdf`: how a leader runs a team: roles, Team hub, approvals, delegation, Content Ops, reporting, security, playbooks.
They are also served to signed-in users from the in-app **Help & guides** page (`/help`, files in `static/guides/`). A fourth PDF, `Debut-Visual-Tour.pdf`, is a screenshot walkthrough of every screen and role (owner, lead, creator, viewer, client) across three industries — useful for sales, onboarding, or showing a client what they're buying before they sign up. Replace the PDFs in **both** `docs/` and `static/guides/` when you update them. They describe the plan limits and features **as shipped** (Free/Starter/Team/Agency limits in `config.py`). **If you change plan limits, features, role permissions or screen names, update the guides.** They intentionally avoid quoting prices (they point to the Pricing page).

## 9i. Client portal (Client role)

Agencies invite their clients as **Client** members (Team & roles > Invite, role *client*, plus the **client name**). A client sees a single page, `/portal`, and nothing else.

- **Scoping rule:** Content Items and Campaigns have a **Client** field. A client only ever sees rows whose `client` equals (case-insensitive) the `client_name` stored on their membership. Every portal query filters by workspace **and** client name; item pages return 404 for anything else. Covered by `test_client_portal_shows_only_that_clients_work` (other client's items, budgets, internal notes, owners, money, every staff URL and every write endpoint).
- **What a client can do:** view their items (copy, CTA, hashtags, design link, friendly status), see their campaigns (goal, channel, dates, status, KPI target; **never** budget, spend, owner or learnings), **approve** or **request changes** on items in *Review* (the app moves the item to *Approved* or back to *In progress*), and message the team. Staff get notifications for each action.
- **Comments are private by default.** A staff comment is visible to the client only if the author ticks **Share with client** (managers and above, only on items that have a client). Client comments are always visible to staff.
- **Allow-list, default deny:** `CLIENT_OK` in `app.py` lists the only endpoints a client can reach (portal, notifications, feedback, help, their account). Everything else returns 403.
- **Seats:** clients do **not** use staff seats. Plans have a separate `clients` allowance in `config.py` (`free 0, starter 0, trial 5, team 5, agency 25`); pending invites count. On a plan with `clients=0` (e.g. after a downgrade) a client sees a "not included in the current plan" page and no data.
- **Staff preview:** owners, admins, leads and managers can open `/portal?client=<name>` (or use **Preview portal** on the Team page) to see exactly what a client sees; only the client can approve.
- Clients never appear in the Team hub workload, `@mention` matching, assignee suggestions, task assignment notifications or the daily digest. Client roles cannot be created or changed by editing a role: remove and re-invite.
- New columns (added automatically): `memberships.client_name`, `invites.client_name`, `comments.client_visible`, `content_items.client`, `campaigns.client`.
- **Not in the portal yet:** KPI/report views, invoices, file uploads by the client, e-signatures. Add them by extending `portal()` with equally strict client-name filters and tests.

## 9j. Launch controls, business pages and pilot tools

- **Business pages:** `/contact` and `/refunds` (plus Terms and Privacy) are driven by the business-identity env vars (§4) so payment-gateway reviewers see real details. The Terms, Privacy and Refund pages remain **templates** that a lawyer must approve. `/sitemap.xml` and `/robots.txt` are generated; signed-in pages are `noindex`. Public pages carry description, canonical and Open Graph tags.
- **Cost and abuse controls:** AI Studio requires a **verified email** (fake sign-ups cost you nothing), and `AI_DAILY_CAP` optionally caps platform-wide AI use per day. Per-workspace monthly credits, per-IP rate limits and signup limits already exist.
- **Maintenance mode:** `MAINTENANCE=1` (see §4).
- **Feedback:** every signed-in role (including creators and clients) has **Send feedback** in the menu. Messages are stored, emailed to `SUPPORT_EMAIL` with user, workspace, plan and page, and listed in **Admin > Feedback inbox** (`/admin/feedback`) with a Resolve button. Feedback is deleted with the workspace.
- **Launch metrics (Admin):** new users (7/30 days), new workspaces, workspaces active in 7 days, AI credits today/30 days, new subscriptions, open feedback, signups by day (14 days) and **trials ending in the next 3 days** with the owner's email (for personal outreach).
- **Help centre:** `/help` (signed-in) lists the customer guides and quick answers.

## 9k. Live data: Market Pulse and AI live research

**Market Pulse** (`/pulse`, menu > Intelligence) pulls live signals for each workspace's *watchlist* (starter terms per industry, plus anything the user adds, plus their Competitors automatically). Code: `pulse.py` (fetchers and analysis), `services.run_pulse` (storage), routes at the bottom of `views.py`.

| Source | How | Needs | Notes |
|---|---|---|---|
| News, India and Global | Google News RSS (default), or GNews / NewsData APIs | nothing / an API key | Last 7 days, per term and region. Publisher and date shown; click-through to the original. |
| Hacker News | Algolia public API | nothing | Only for tech-related industries (SaaS, startup, B2B, fintech, agency, personal brand) |
| YouTube | Official Data API v3 | `YOUTUBE_API_KEY` | Most-viewed videos of the last 30 days per keyword, with view counts |
| Trending searches | Google's public trending-now RSS (India and US) | nothing | Broad "what people search today" signal |
| Reddit | Public `.rss` for Subreddit watch items | `PULSE_REDDIT=1` | Off by default |
| Public holidays | Nager.Date public API | nothing | "Add public holidays" button; adds to Key Dates without duplicates |

- **Rising terms:** a transparent word/phrase frequency count across the fetched headlines (no AI), with a *new* badge for terms absent from the previous refresh. The last 8 snapshots per workspace are kept (`pulse_runs`).
- **AI brief:** one click sends the stored live items (numbered, with sources) to Claude and returns a brief that cites `[n]`. Costs 2 credits, requires a verified email, respects `AI_DAILY_CAP`. It does **not** perform extra web searches.
- **Limits:** watchlist size per plan (`watch` in `config.py`: Free 3, Starter 10, Team 25, Agency 50, trial 25). Refresh is limited to owner/admin/lead/manager, once per `PULSE_MIN_REFRESH_MINUTES`, 20/hour. Fetching runs in the request (8 parallel calls, 8 s timeout each): typically a few seconds.
- **Safety:** all outbound requests go through `services.safe_get` (public hosts only, size and time limits, redirects re-checked). User terms are URL-encoded; subreddit names are validated; links from feeds are kept only if they are `http(s)`; text is HTML-stripped and escaped on display. A failing source never breaks the page: errors are listed under *Notes on sources*.
- **Scheduled refresh (optional):** `python manage.py refresh-pulse` refreshes every workspace with a watchlist whose data is older than the cache window. Run it once or twice a day from the same scheduler as the digest so users open fresh data.

**AI live research:** in AI Studio, three tasks (*market & category scan*, *competitor intelligence*, *trends & content opportunities*) always use Anthropic's **web search tool** (`web_search_20250305`, up to 4 searches, India location hint), and any other task can opt in with a checkbox (+`AI_RESEARCH_EXTRA` credits). The answer lists the pages Claude used (from citations and search results, de-duplicated, http(s) only). Long searches that pause are continued up to twice. If web search is not enabled on your Anthropic account the user gets a plain message and **is not charged**.

**Compliance and cost notes (read these):**
1. **Data terms.** Google News RSS and Google's trending feed are public feeds without a commercial licence for a paid product; Reddit and YouTube have their own API terms. That is acceptable for a small pilot with links back to publishers, but **before you scale or charge, switch `NEWS_PROVIDER` to a licensed API (GNews or NewsData) and have your lawyer review the sources you keep**. We show headlines and links only, never full articles.
2. **Web search costs money.** Anthropic charges per web search on top of tokens; research answers cost you more, which is why they cost users extra credits. Watch your Anthropic usage page in launch week and use `AI_DAILY_CAP`.
3. **What was and was not tested.** Parsing, storage, throttling, limits, safety and every failure path are covered by automated tests using recorded sample responses for each source and for Claude's web-search reply shape. **None of it has run against the live services from our build environment** (no internet access to those hosts, no API key). Expect to verify on staging: run *Refresh now*, check *Notes on sources*, and run one live research task.
4. Trending words and searches are signals, not forecasts. The UI says so.

---

## 9l. Brand theming, the mood board canvas, and first-time onboarding

- **Brand theming:** business workspaces (any industry except `personal_brand`) can set a hex colour in Account > Brand colours (`ws.account_theme` / `ws.account_theme_reset`, owner/admin only). It's stored in `workspaces.brand_color` and expanded server-side into a small palette (`services.hex_shades`: a darker shade, two light tints) that overrides the CSS variables `--pri/--pri-d/--pri2/--pri3/--accent` via an inline `<style>` block in `base.html`. Applies everywhere that template is used, including the client portal and printed report. `personal_brand` workspaces always render the default lavender theme and the route 403s if they try to set one.
- **Mood board canvas:** `board_items` now has `x, y, w, h, z` columns. New items are placed automatically in a cascading grid (`views._next_slot`); dragging (pointer events, no library) and resizing save instantly via `POST /moodboards/item/<id>/place` (JSON, bounds-clamped, workspace-scoped). `POST /moodboards/<id>/arrange` snaps everything back to a tidy grid. Boards created before this existed get their items placed once, the first time the board is opened (`x=-1` sentinel). Creators can use boards fully; viewers remain read-only.
- **First-time tour:** a client-side spotlight tour (no new dependency) runs once per user on first dashboard load, driven by `data-tour` attributes in the sidebar; finishing or skipping it POSTs to `/account/onboarded` (`users.onboarded`). Replayable any time from Help & guides ("Take the tour again"). The Help page also has a static "Where is everything?" quick-reference table.

## 10. Database operations

- **Schema:** created and upgraded by `python manage.py init-db` on every start (`start.sh`). It is **additive only** (new tables/columns are added; nothing is dropped or renamed). This makes rollbacks safe: old code ignores new columns. Renaming/removing columns needs a manual migration (consider Alembic if you start doing that).
- **Also new** (auto-created): table `feedback`; `memberships.client_name`, `invites.client_name`, `comments.client_visible`; fields `content_items.client`, `campaigns.client`.
- **New tables/columns in an earlier release** (created/added automatically by `init-db`; safe on existing databases): `comments`, `notifications`, `api_keys`, modules `pitches`, `accounts`, `retail_audits`; `users.totp_secret/totp_on/totp_last/recovery/digest`; `workspaces.industry/ics_key/hook_key`. Older databases upgrade in place (verified against a database created by the previous release).
- **Concurrent boot:** `init-db` takes a Postgres advisory lock so several instances can start together safely.
- **Connections:** each gunicorn worker holds a pool of up to 10 connections (5 + 5 overflow). With 3 workers that is up to 30. Make sure the database plan allows it, or reduce `WEB_CONCURRENCY`/add a pooler (PgBouncer).
- **Backups:** enable the provider's automated backups **and** schedule `deploy/backup.sh` (needs `pg_dump`; set `DATABASE_URL_PLAIN=postgresql://user:pass@host/db`, optional `S3_BACKUP_URI`; keeps 14 days locally). Example cron: `0 2 * * * /path/deploy/backup.sh`.
- **Restore test (mandatory before launch):** restore a backup into a scratch database, point a staging copy at it, log in, confirm data.
  ```bash
  gunzip -c debut-YYYYMMDD-HHMM.sql.gz | psql "$SCRATCH_DATABASE_URL"
  ```
- Also back up the uploads volume if not using S3.

---

## 11. Operations cheat sheet

```bash
python manage.py init-db                       # create/upgrade schema (runs automatically on start)
python manage.py list                          # list workspaces with plan/status
python manage.py verify-user <email>           # mark an email verified (e.g. to unlock /admin before SMTP works)
python manage.py reset-2fa <email>             # clear someone's two-factor setup (lost phone)
python manage.py send-digests                  # send the daily digest emails (run from cron, §5)
python manage.py set-plan <slug> <plan>        # comp a plan (starter|team|agency)
python manage.py extend-trial <slug> <days>    # extend a trial
docker compose logs -f web                     # Compose logs (Render/Railway: platform log viewer)
```

Platform owner tasks are in the web UI at `/admin`: revenue tiles, search workspaces/users, +14-day trial, set plan (including back to Free), mark email verified, and **Open (read-only)** support view of any workspace (recorded in that workspace's activity log; disclosed in the Privacy Policy).

**Deploy procedure:** merge → CI (GitHub Actions in `.github/workflows/ci.yml` runs tests on SQLite and Postgres) → deploy → check `/health` → smoke test (§13).
**Rollback:** redeploy the previous image/commit. Safe because schema changes are additive.

**Logs:** plain-text logs to stdout/stderr (gunicorn access log + app log). Ship them with your platform's log drain. Rate-limit hits are logged at INFO.

---

## 12. Security checklist

- [ ] `APP_ENV=production` and a unique 64-char `SECRET_KEY` (never reuse, never commit)
- [ ] HTTPS only; HSTS is sent by the app in production
- [ ] Database not publicly reachable (private network or IP allow-list)
- [ ] `ADMIN_EMAILS` contains only the owner's real, MFA-protected mailbox. Admin access requires the account's email to be **verified**; the owner should register that address immediately after deploy so nobody else can
- [ ] Razorpay webhook secret set (webhook returns 400 without a valid signature)
- [ ] S3 bucket private, least-privilege credentials
- [ ] Container runs as non-root (Dockerfile already does)
- [ ] `.env` never in git or Docker image (`.gitignore`/`.dockerignore` already exclude it)
- [ ] Owner has turned on 2FA and stored the recovery codes offline; `REQUIRE_ADMIN_2FA` left on
- [ ] The lead webhook is intentionally callable from any website (CORS `*`); confirm the owner is comfortable, and that their own forms collect consent
- [ ] Optional but recommended: Cloudflare/WAF in front; automated dependency updates (Dependabot); uptime monitor on `/health`; Sentry via `SENTRY_DSN`

Already implemented in code: CSRF protection on all forms and API calls, login/signup/reset/AI/apply rate limits, scrypt password hashing, SSRF guard on user-supplied feed URLs, upload content sniffing, security headers, workspace-scoped queries with isolation tests, audit log, input hardening (bad ids/JSON/null bytes return 4xx).

Rate limits in place: signup 10/h, login 15 per 15 min, forgot 5/h, reset 10/h, public creator-apply 6/h, AI 5/min and 60/h (per IP), global 600/h and 2000/day per IP. Users behind one corporate NAT share an IP; raise limits in `extensions.py`/decorators if that bites.

Additional controls in this release: **two-factor login** (§9d, required for platform admin in production), hashed API keys, secret-URL webhook with rate limit, calendar/report links that can be rotated, consent capture on the hosted lead form, comments/notifications scoped to workspace and user.

Not implemented (be aware): SSO/SAML, workspace-wide enforced 2FA for all members (2FA is per user), strict CSP (pages use inline scripts, so only `frame-ancestors/base-uri/object-src` are set), email verification is encouraged but not enforced, DNS-rebinding race in the feed SSRF guard is theoretically possible (keep the web service off internal admin networks).

---

## 13. Smoke test before go-live (with Razorpay in Test Mode)

Run on the real staging URL, in this order:

1. Sign up (owner) → verification email arrives → click link.
2. Create a content item, a mood board with an image upload; reload; confirm image still loads.
3. Calendar page → copy the subscribe link → open it in a private window (must return `.ics` text) → click **Reset link** → old link must 404.
4. Team → invite a **lead** (second email). Accept the invite. As lead: Team hub opens; Billing returns 403; can invite a manager but not an admin.
5. Invite a **creator**. As creator: set a content item to *Published* → it must be saved as *Review*. As lead: Approve it from Team hub.
6. Billing → subscribe to Team (test card) → features unlock → webhook shows 200 in Razorpay.
7. Cancel subscription → banner shows cancellation → (optionally set `period_end` in the past in DB) → workspace drops to Free, paid modules show the upgrade page, data remains.
8. Password reset flow end to end.
9. Account → Export data (ZIP of CSVs) → Delete workspace (type slug) → confirm data gone.
10. Sign in as admin → `/admin` → open another workspace in support view → confirm it is read-only and the exit button works.
11. AI Studio → generate once → credit counter increases. (If it errors, check `ANTHROPIC_API_KEY`/`GTM_MODEL`.)
12. Sign up two unrelated workspaces and confirm neither can see the other's data.
13. **Industry modes:** sign up with *Personal brand*, *B2B* and *FMCG* ("load starter kit" on): each sees its own checklist/Idea Bank; only the right niche module shows in the sidebar (Opportunities / Target Accounts / Retail Audits).
14. **Collaboration:** assign a task to a teammate's exact name, add a comment with `@TheirName`; they see the bell badge and the notification opens the record. Creator sets an item to *Review* → lead is notified → lead approves from Team hub → creator is notified.
15. **Digest:** with SMTP on and a task overdue for a verified user, run `python manage.py send-digests`; the email arrives with a working unsubscribe link.
16. **Lead capture:** open `/lead/<slug>` in a private window and submit (consent ticked) → lead appears. From another domain/`curl`, POST to the webhook URL → lead appears; reset the URL → old one returns 404.
17. **API:** create a *write* key (Team plan), `POST /api/v1/kpis` with curl → row appears in KPIs; a *read* key can't write; a Starter/Free workspace gets 403.
18. **Two-factor:** enable 2FA on the owner account, log out, log in → code prompt; wrong code refused; a recovery code works once. Confirm `/admin` is visible only after 2FA is on.
19. **Report:** `/report` → Print/save PDF looks clean; open the share link in a private window (no login); **Calendar → Reset link** kills it.
20. **Mobile/PWA:** open the site over HTTPS on a phone; slide-in menu works; "Install app"/Add to Home Screen; DevTools → Application shows the manifest and an active service worker.
21. **Client portal:** tag a content item with a client name and set it to *Review*; invite a *client* with that exact name; as the client confirm you see only that item and campaign (no budget, no other client, no internal notes, no menu beyond the portal); *Request changes* with a note, then *Approve*; confirm the team gets notifications; try a couple of staff URLs as the client (must be 403).
22. **Launch pages and pilot tools:** open `/contact`, `/refunds`, `/terms`, `/privacy` and confirm your real business details show; check `/sitemap.xml`; press **Send feedback** as a customer and confirm the message arrives in the admin **Feedback inbox** and in `SUPPORT_EMAIL`; check **Admin > Launch metrics**; set `AI_DAILY_CAP=1` briefly and confirm AI refuses, then reset; try `MAINTENANCE=1` and confirm `/health` still answers.
23. **Live data:** open **Market Pulse**, press *Refresh now* and confirm headlines, *Searching for today* and (if a YouTube key is set) videos appear; read *Notes on sources* for any failing source; click **AI brief** (needs a verified email and credits); add a competitor under Competitors and refresh to see it tracked; press **Add holidays**; then in **AI Studio** run *Live research: market & category scan* and confirm sources are listed (if it says web research isn't enabled, enable web search in the Anthropic console).

---

## 14. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| App won't start: `SECRET_KEY must be set` | Set `SECRET_KEY` (production requires it) |
| Every form returns 400 | CSRF cookie not sent: not on HTTPS, wrong domain, or cookies blocked. Also happens if workers/instances have **different** `SECRET_KEY`s |
| Users keep getting logged out | Different `SECRET_KEY` per instance, or `SECRET_KEY` changed on deploy |
| Login works locally but not in prod | Site served over HTTP (cookies are `Secure`) |
| "Too many requests" for everyone | Proxy chain wrong so all users share one IP: adjust `ProxyFix(x_for=…)` in `app.py`; set `REDIS_URL` when running several workers/instances |
| No verification / reset / invite emails | SMTP not configured or blocked; check logs (`email failed`); check SPF/DKIM; some hosts block port 587 |
| Payment succeeds but plan doesn't change | Webhook not reaching the app or wrong `RAZORPAY_WEBHOOK_SECRET` (400 in Razorpay delivery log); proxy altering the request body; `/billing/verify` failing (check key secret) |
| "Razorpay plan ID … not set" on subscribe | Missing `RAZORPAY_PLAN_*` env var |
| Prices differ between app and checkout | `PLANS` in `config.py` ≠ Razorpay plan amounts |
| Images disappear after redeploy | Container filesystem is ephemeral: mount a volume at `UPLOAD_DIR` or use S3 |
| `too many connections` / pool timeouts | Reduce `WEB_CONCURRENCY` or raise DB connection limit / add PgBouncer |
| Calendar (.ics) links stopped working | `SECRET_KEY` changed, or someone used **Reset link** |
| `postgres://` URL errors | Already auto-converted; if you still see driver errors, use `postgresql+psycopg2://…` and ensure `psycopg2-binary` installed |
| AI returns "not configured" / 402 | No `ANTHROPIC_API_KEY`, or the workspace used its monthly AI credits (by design) |
| Owner can't reach `/admin` in production | Admin needs a **verified email** and **2FA on** (`REQUIRE_ADMIN_2FA`). Enable 2FA under Account; if the phone is lost: `python manage.py reset-2fa <email>` |
| Digest emails never arrive | The cron job (§5) isn't scheduled, SMTP isn't configured, the user's email isn't verified, they opted out, or there was nothing due (it only sends when something needs them) |
| Website form can't post to the lead webhook | Wrong/reset key (404), missing email/phone (400), blocked by an ad-blocker, or a proxy stripping CORS headers; test with `curl -i -X OPTIONS <hook-url>` (expect 204 + `Access-Control-Allow-Origin: *`) |
| API returns 403 | Plan lacks the `api` feature (Team/Agency), a read-only key used for writes, or a module gated by plan (e.g. Content Ops) |
| "Install app" never appears | Site not on HTTPS, service worker failed to register (check `/sw.js` returns JavaScript), or the user already installed it |
| 2FA codes are always wrong | The server or phone clock is off by more than ~30 s; sync time (NTP) |
| Health check fails at boot | `init-db` couldn't reach the database: check `DATABASE_URL`, network, TLS (`?sslmode=require`) |

---

## 15. Things the owner may ask you to change

| Change | Where |
|---|---|
| Prices, seats, AI credits, record limits, Free-plan limits, which plan has which feature | `config.py` → `PLANS` (and update Razorpay plan amounts) |
| Role permissions | `config.py` (`RANK`, `TEAM_MANAGERS`), `app.py` (`CREATOR_OK`, `VIEWER_WRITE_OK`), `views.py` (`RESTRICTED` approvals) |
| Industries (add/edit kits) | `industries.py`; run `pytest tests -k industry` (validates against dropdown values) |
| Branding / colours | `static/style.css` (CSS variables at the top), `APP_NAME` |
| Industry kits, AI tasks per industry, which niche modules show for which industry | `industries.py`, `modules.py` (`AI_TASKS`, `AI_TASK_FOR`), `industries.MODULE_INDUSTRIES` |
| API rate limit / which plans get the API | `api.py` (`limiter.limit`), `config.py` (`api` in each plan's `features`) |
| Digest content / timing | `services.digest_text`, cron schedule (§5) |
| Legal pages | `templates/terms.html`, `templates/privacy.html` |
| New marketing modules/fields | `modules.py` (tables and columns are created automatically on next start) |

Third-party code bundled: Chart.js 4.5.1 (MIT) in `static/vendor/`, licence file included.

---

## 16. Go-live checklist

- [ ] All items in §2 received from the owner
- [ ] Staging fully passes the smoke test (§13) with Razorpay **Test Mode**
- [ ] Live Razorpay keys, live plan IDs, live webhook + secret installed; one real payment made and refunded
- [ ] SMTP verified (SPF/DKIM/DMARC pass; mail not in spam)
- [ ] Custom domain + HTTPS + `APP_URL` correct
- [ ] Prices and `PRICE_NOTE` final and consistent with Razorpay plans
- [ ] Lawyer-approved Terms and Privacy installed
- [ ] Daily digest cron job created (§5) and one digest received
- [ ] Owner's admin account has 2FA enabled (production requires it for `/admin`)
- [ ] Lead form + webhook, API key, report share link and PWA install each tried once on the live domain
- [ ] Backups enabled **and a restore tested**
- [ ] Uptime monitor on `/health`, Sentry (or equivalent) receiving a test error
- [ ] `ADMIN_EMAILS` correct and the owner can open `/admin`
- [ ] Support mailbox monitored
- [ ] Owner has the credentials/handover list (hosting, DNS, Razorpay, SMTP, Anthropic, database) stored securely

---

## 17. Known limitations (share with the owner)

- Razorpay, SMTP and S3 integrations are untested against live services (⚠️ §7, §8, §9). The new digest email, lead form CORS and PWA install were tested in automated tests and a headless browser, but not on real phones/mail providers.
- No plan-change proration; no 2FA/SSO; email verification not enforced.
- Team-hub workload and notifications match people to tasks by the name/email typed in the assignee/owner field (free text, not an ID link).
- Market Pulse data comes from public feeds and free APIs: coverage of Indian regional-language media and niche trade press is limited; no Instagram, LinkedIn or Meta/Google Ads account data (those need each customer's own authorised connection and platform approval).
- The client portal covers content and campaigns only (no reports, invoices or uploads for clients); a client is tied to one client name.
- No suspend/ban control for an abusive workspace in the admin yet (workaround: `python manage.py set-plan <slug> free` and remove members, or a manual DB change).
- No native connectors to Meta Ads, Google Analytics, Instagram/LinkedIn publishing or email-campaign sending. Data can be pushed in through the REST API / lead webhook (Zapier/Make) or CSV import; build first-party connectors as customers ask.
- Notifications are in-app and by daily email digest only (no push notifications); comments cannot be edited (only deleted).
- 2FA is per user (not enforceable for a whole workspace); no SSO/SAML.
- API writes bypass approvals/notifications. Report share links expose budgets to anyone holding the link until it is reset.
- The PWA is a web app, not a native store app; it works online, with only static assets and an offline notice cached.
- News feeds are fetched on demand with a 15-minute per-workspace cache (no background worker); emails are sent synchronously.
- Schema upgrades are additive only.
- Free-plan workspaces cost real money (AI credits, storage): keep the Free limits modest and watch the "Free workspaces" tile in `/admin`.

*End of guide.*
