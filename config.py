"""Central configuration. Everything secret comes from environment variables (or a local .env file)."""
import os
from collections import OrderedDict
from datetime import timedelta

BASE = os.path.dirname(os.path.abspath(__file__))


def _load_env():
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip()
                if v[:1] in ("'", '"') and v.count(v[0]) >= 2:
                    v = v[1:v.index(v[0], 1)]          # quoted value: keep everything inside the quotes
                else:
                    v = v.split(" #", 1)[0].strip()    # unquoted: drop trailing "  # comment"
                os.environ.setdefault(k.strip(), v)


_load_env()


def env(k, d=""):
    return os.environ.get(k, d)


def flag(k, d="0"):
    return env(k, d).lower() in ("1", "true", "yes", "on")


APP_ENV = env("APP_ENV", "development")
PROD = APP_ENV == "production"

APP_NAME = env("APP_NAME", "Debut")
COMPANY_NAME = env("COMPANY_NAME", "Your Company Pvt Ltd")
SUPPORT_EMAIL = env("SUPPORT_EMAIL", "support@example.com")
SUPPORT_PHONE = env("SUPPORT_PHONE")                       # shown on the Contact page (payment gateways ask for a contact number)
SUPPORT_HOURS = env("SUPPORT_HOURS", "Monday to Friday, 10:00 to 18:00 IST")
COMPANY_ADDRESS = env("COMPANY_ADDRESS")                   # registered/business address, shown on Contact and legal pages
COMPANY_GSTIN = env("COMPANY_GSTIN")
GRIEVANCE_OFFICER = env("GRIEVANCE_OFFICER")               # name of the person who handles privacy/grievance requests
GRIEVANCE_EMAIL = env("GRIEVANCE_EMAIL") or env("SUPPORT_EMAIL", "support@example.com")
REFUND_WINDOW_DAYS = int(env("REFUND_WINDOW_DAYS") or 7)   # how many days after the first payment a refund is offered (edit your policy accordingly)
AI_DAILY_CAP = int(env("AI_DAILY_CAP") or 0)                # platform-wide AI credits per day across ALL workspaces (0 = no cap). Protects your API budget during launch.
MAINTENANCE = flag("MAINTENANCE")                          # 1 = show a maintenance page to everyone except the platform admin (use during risky deploys)
GA_MEASUREMENT_ID = env("GA_MEASUREMENT_ID")

# --- live market data (Market Pulse). Everything here is optional; sources that need a key stay off until you add one.
NEWS_PROVIDER = env("NEWS_PROVIDER", "google_rss")         # google_rss (free, fine for a pilot) | gnews | newsdata (licensed APIs: use one of these for commercial scale)
GNEWS_API_KEY, NEWSDATA_API_KEY = env("GNEWS_API_KEY"), env("NEWSDATA_API_KEY")
YOUTUBE_API_KEY = env("YOUTUBE_API_KEY")                   # official YouTube Data API: trending videos per keyword
PULSE_HN = flag("PULSE_HN", "1")                           # Hacker News search (tech-related industries only)
PULSE_TRENDS = flag("PULSE_TRENDS", "1")                   # Google's daily trending-searches feed (India + global)
PULSE_REDDIT = flag("PULSE_REDDIT", "0")                   # Reddit public feeds for Subreddit watch items (off by default: often blocked from cloud servers, check Reddit's terms)
PULSE_CACHE_MINUTES = int(env("PULSE_CACHE_MINUTES") or 60)
PULSE_MIN_REFRESH_MINUTES = int(env("PULSE_MIN_REFRESH_MINUTES") or 10)
AI_WEB_SEARCH = flag("AI_WEB_SEARCH", "1")                 # allow AI Studio "live web research" (needs web search enabled in your Anthropic console)
AI_RESEARCH_EXTRA = int(env("AI_RESEARCH_EXTRA") or 2)     # extra credits a research answer costs (web searches cost you more than plain text)               # optional Google Analytics 4 id, loaded on public marketing pages only
VAPID_PUBLIC = env("VAPID_PUBLIC")      # web-push keys: run  python gen_vapid.py  and paste both into Render env vars
VAPID_PRIVATE = env("VAPID_PRIVATE")
VAPID_SUBJECT = env("VAPID_SUBJECT", "mailto:hello@example.com")
APP_URL = env("APP_URL", "http://127.0.0.1:8001").rstrip("/")
TRIAL_DAYS = int(env("TRIAL_DAYS") or 14)
PRICE_NOTE = env("PRICE_NOTE", "+ GST")  # shown next to prices; must match what your Razorpay plans actually charge
ADMIN_EMAILS = [e.strip().lower() for e in env("ADMIN_EMAILS").split(",") if e.strip()]


def _db_url():
    u = env("DATABASE_URL")
    if not u:
        return "sqlite:///" + os.path.join(BASE, "gtm.db")
    if u.startswith("postgres://"):
        return "postgresql+psycopg2://" + u[len("postgres://"):]
    if u.startswith("postgresql://"):
        return "postgresql+psycopg2://" + u[len("postgresql://"):]
    return u


DATABASE_URL = _db_url()
UPLOAD_DIR = env("UPLOAD_DIR", os.path.join(BASE, "uploads"))
SECRET_KEY = env("SECRET_KEY") or ("" if PROD else "dev-only-not-secret")

# --- email (SMTP: Amazon SES, Resend, Postmark, Gmail app password, etc.)
SMTP_HOST, SMTP_PORT = env("SMTP_HOST"), int(env("SMTP_PORT") or 587)
SMTP_USER, SMTP_PASSWORD = env("SMTP_USER"), env("SMTP_PASSWORD")
SMTP_FROM = env("SMTP_FROM", "Debut <no-reply@example.com>")

# --- AI (your key; usage is metered per plan)
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
GTM_MODEL = env("GTM_MODEL", "claude-sonnet-5")

# --- billing (Razorpay Subscriptions). BILLING_MODE is an explicit, independent choice from APP_ENV/PROD:
# PROD only controls proxy/security hardening (see app.py) and must be "production" behind a proxy like Render,
# regardless of whether real Razorpay keys are configured. Set BILLING_MODE=off yourself to hide billing entirely.
RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_ID"), env("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET")
BILLING_MODE = env("BILLING_MODE", "razorpay" if env("RAZORPAY_KEY_ID") else "demo")

# --- optional infrastructure
S3_BUCKET, S3_REGION, S3_ENDPOINT = env("S3_BUCKET"), env("S3_REGION", "ap-south-1"), env("S3_ENDPOINT")
REDIS_URL = env("REDIS_URL")  # rate-limit storage; falls back to per-process memory
SENTRY_DSN = env("SENTRY_DSN")
# Platform-admin access additionally requires two-factor login when this is on (default on in production)
REQUIRE_ADMIN_2FA = flag("REQUIRE_ADMIN_2FA", "1" if PROD else "0")

FLASK = dict(
    SECRET_KEY=SECRET_KEY, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=PROD,
    PERMANENT_SESSION_LIFETIME=timedelta(days=14), MAX_CONTENT_LENGTH=25 * 1024 * 1024, WTF_CSRF_TIME_LIMIT=8 * 3600,
    RATELIMIT_STORAGE_URI=REDIS_URL or "memory://", RATELIMIT_HEADERS_ENABLED=True,
)

ALL_FEATURES = {"content_ops", "promo_events", "influencers", "analytics", "ai", "import", "group", "api"}  # "group" = team hub, approvals, Lead role; "api" = REST API keys
# Prices are placeholders: set your own. price is INR per month, excl. GST. Create matching plans in Razorpay
# and put their IDs in RAZORPAY_PLAN_STARTER / _TEAM / _AGENCY.
PLANS = OrderedDict([
    # Free forever: the core planning tools with small limits. New workspaces first get a trial of everything.
    ("free", dict(name="Free", price=0, seats=1, clients=0, watch=3, ai_credits=5, records=100, boards=3, features={"ai"},
                  blurb="Plan and organise your marketing, free forever")),
    ("trial", dict(name="Free trial", price=0, seats=5, clients=5, watch=25, ai_credits=40, records=2000, boards=999, features=ALL_FEATURES,
                   blurb=f"{TRIAL_DAYS} days, all Team features")),
    ("starter", dict(name="Starter", price=999, seats=1, clients=0, watch=10, ai_credits=40, records=1500, boards=20, features={"influencers", "analytics", "ai", "import"},
                     blurb="Solo marketers & freelancers", rzp_env="RAZORPAY_PLAN_STARTER")),
    ("team", dict(name="Team", price=3999, seats=5, clients=5, watch=25, ai_credits=250, records=10000, boards=999, features=ALL_FEATURES,
                  blurb="Growing brands & small agencies", rzp_env="RAZORPAY_PLAN_TEAM")),
    ("agency", dict(name="Agency", price=9999, seats=15, clients=25, watch=50, ai_credits=1000, records=50000, boards=999, features=ALL_FEATURES,
                    blurb="Agencies & content businesses", rzp_env="RAZORPAY_PLAN_AGENCY")),
])
PAID_PLANS = [k for k in PLANS if k not in ("free", "trial")]


# ---- pricing cards: each plan shows what it ADDS over the one below, so the next step up is easy to see
FEATURE_LABELS = [("ai", "AI Studio drafts"), ("influencers", "Influencer discovery & outreach"), ("analytics", "KPI tracking & analytics"), ("import", "CSV import"),
                  ("group", "Team hub, Lead role & approvals"), ("content_ops", "Content Ops: creator network, orders, invoices"),
                  ("promo_events", "Promotions & events, online + offline"), ("api", "REST API & integrations")]
PLAN_PITCH = {"free": ("Try it, no card needed", "Need AI drafts, analytics or influencers? Starter switches them on."),
              "starter": ("For one marketer going solo", "Working with a team or clients? Team adds seats, approvals and a client portal."),
              "team": ("For brands and small agencies", "Running many clients? Agency triples the seats and gives 25 client logins."),
              "agency": ("For agencies and content businesses", "")}
PLAN_ORDER = ["free", "starter", "team", "agency"]


def _fmt(n, key=""):
    return "Unlimited" if (key == "boards" and n >= 999) else f"{n:,}"


def plan_cards(cur=""):
    """Cards for the pricing grid. `cur` (a plan key) turns on billing mode: plans above it list what you'd gain over it."""
    cards = []
    for i, k in enumerate(PLAN_ORDER):
        p = PLANS[k]
        base_k = PLAN_ORDER[i - 1] if i else None
        if cur in PLAN_ORDER and PLAN_ORDER.index(cur) < i:
            base_k = cur                                      # billing: compare against what the customer has now
        b = PLANS[base_k] if base_k else None
        adds = []
        for f, label in FEATURE_LABELS:
            if f in p["features"] and (b is None or f not in b["features"]):
                adds.append(label)
        if p["clients"] and (b is None or not b["clients"]):
            adds.append(f"Client portal ({p['clients']} client logins)")
        elif b and p["clients"] > b["clients"]:
            adds.append(f"Client logins: {b['clients']} → {p['clients']}")
        if b is None:
            adds.append(f"Market Pulse: live news & trends for {p['watch']} topics")
        elif p["watch"] > b["watch"]:
            adds.append(f"Market Pulse topics: {b['watch']} → {p['watch']}")
        nums = []
        for key, label in (("seats", "team seats"), ("ai_credits", "AI credits / mo"), ("records", "records"), ("boards", "mood boards")):
            v = p[key]
            if b is None:
                nums.append((_fmt(v, key), label, False))
            elif v > b[key]:
                nums.append((_fmt(v, key), label, f"{_fmt(b[key], key)} → {_fmt(v, key)}"))
        cards.append(dict(key=k, name=p["name"], blurb=p["blurb"], price=p["price"], base=PLANS[base_k]["name"] if base_k else "",
                          adds=adds, nums=nums, who=PLAN_PITCH[k][0], nudge=PLAN_PITCH[k][1], popular=(k == "team"), rank=i))
    return cards


def plan_matrix():
    """Rows for the full side-by-side comparison."""
    rows = [(label, [_fmt(PLANS[k][key], key) for k in PLAN_ORDER]) for key, label in (("seats", "Team seats"), ("clients", "Client logins"), ("ai_credits", "AI credits / month"),
            ("records", "Records"), ("boards", "Mood boards"), ("watch", "Market Pulse topics"))]
    rows = [(l, [("—" if v == "0" else v) for v in vals]) for l, vals in rows]
    rows += [(label, ["✓" if f in PLANS[k]["features"] else "—" for k in PLAN_ORDER]) for f, label in FEATURE_LABELS]
    return rows
AI_COST = {"calendar": 3, "gtm_plan": 2, "report": 2, "event_plan": 2, "blog": 2, "competitor": 2, "pulse_brief": 2, "research_market": 2, "research_competitor": 2, "research_trends": 2,
           "problem_assessment": 2, "ask_debut": 1}
ROLES = ["owner", "admin", "lead", "manager", "creator", "viewer", "client"]
# Who may assign / change / remove whom: an actor can only touch roles ranked strictly below their own (owner is never assignable).
RANK = {"owner": 5, "admin": 4, "lead": 3, "manager": 2, "creator": 1, "viewer": 0, "client": -1}
TEAM_MANAGERS = ("owner", "admin", "lead")


# ---- what each locked feature does, shown on the "unlock this" page
FEATURE_PITCH = {
    "ai": ("AI Studio", "Draft calendars, GTM plans, reports and posts in seconds."),
    "influencers": ("Influencer discovery & outreach", "Find creators, track every outreach and reply, and never lose a lead to a buried DM."),
    "analytics": ("KPI tracking & analytics", "See what is working with KPIs, experiments and trends in one place."),
    "import": ("CSV import", "Bring your spreadsheets in with one upload instead of retyping."),
    "content_ops": ("Content Ops", "Run a creator network: orders, deadlines, invoices and payouts."),
    "promo_events": ("Promotions & events", "Plan online promos and offline events with budgets and checklists."),
    "group": ("Team hub & approvals", "Add a Team Lead, see everyone's workload and approve work before it goes out."),
    "api": ("REST API & integrations", "Push data in and out of Debut from your other tools."),
}


def next_plan(plan_key):
    """The next paid plan up from plan_key, or None."""
    order = PLAN_ORDER
    i = order.index(plan_key) if plan_key in order else 0
    return next((k for k in order[i + 1:]), None)


def upsell(plan_key, what, key, label):
    """One friendly sentence naming the next step up, for limit messages."""
    nk = next_plan(plan_key)
    if not nk:
        return ""
    n = PLANS[nk]
    return f" {n['name']} (₹{n['price']:,}/mo) raises it to {_fmt(n[key], key)} {label}."
