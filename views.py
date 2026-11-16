"""Product views. Every query is scoped by workspace_id; see tests/test_app.py for tenant-isolation checks."""
import os, re, io, csv, json, base64, hashlib, calendar as pycal, datetime as dt
from collections import OrderedDict, Counter
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from urllib.parse import quote, quote_plus
from xml.etree import ElementTree as ET
import requests
from flask import g, render_template, request, redirect, url_for, flash, jsonify, abort, Response, send_from_directory, make_response, session
import secrets
from itsdangerous import URLSafeSerializer, BadSignature
import config as C
import services as S
import industries as IND
from db import q, ex, ins, qi, MANUAL_ORDER
from extensions import csrf, limiter
from modules import *  # noqa: F401,F403

ROUTES = []


def route(rule, **opts):
    def deco(f):
        ROUTES.append((rule, f, opts))
        return f
    return deco


def register(app):
    for rule, f, opts in ROUTES:
        app.add_url_rule(rule, endpoint=f.__name__, view_func=f, **opts)
    csrf.exempt(app.view_functions["lead_hook"])      # called cross-site by visitors' browsers / Zapier; protected by its secret URL key instead


def W():
    return g.ws["id"]


def num(s):
    try:
        return float(re.sub(r"[^\d.\-]", "", str(s or "")) or 0)
    except ValueError:
        return 0.0


def safe_next(default):
    n = request.values.get("next", "")
    return n if n.startswith("/") and not n.startswith("//") else default


def mod(key):
    if key not in MODULES:
        abort(404)
    return MODULES[key]


CREATOR_OWN = {"tasks": "assignee", "content_items": "owner", "content_orders": "creator"}


def cscope(key):
    """A freelancer (creator role) only works with what is assigned to them: tasks where they are the assignee, content where
    they are the owner, orders where they are the creator. Returns (sql condition, args); ("1=1", []) for everyone else."""
    col = CREATOR_OWN.get(key)
    if g.role != "creator" or not col:
        return "1=1", []
    keys = [k for k in {(g.user["name"] or "").strip().lower(), (g.user["email"] or "").strip().lower()} if k]
    return f"LOWER(TRIM({col})) IN ({','.join('?' * len(keys))})", keys


def row_or_404(key, rid):
    c, ca = cscope(key)
    return q(f"SELECT * FROM {key} WHERE id=? AND workspace_id=? AND {c}", [rid, W()] + ca, one=True) or abort(404)


def locked(key):
    f = MODULE_FEATURE.get(key)
    return bool(f and f not in g.plan["features"])


# ----------------------------------------------------------------- public pages
@route("/")
def landing():
    if g.user:
        return redirect(url_for("dashboard"))
    return render_template("landing.html", plans=C.PLANS, mods=MODULES, inds=[IND.INDUSTRIES[k] for k in IND.ORDER if k != "general"], demo_inds=[(k, IND.INDUSTRIES[k]) for k in IND.ORDER if k != "general"])


@route("/demo")
@limiter.limit("30 per hour")
def demo():
    import demo as _demo
    from auth import start_session
    uid, wid = _demo.ensure_demo(request.args.get("v", "chai"))
    start_session(uid, wid)
    to = request.args.get("to", "")
    if to.startswith("/") and not to.startswith("//") and "\\" not in to and len(to) < 80:      # land on the matching page of the demo, never off-site
        return redirect(to)
    return redirect(url_for("dashboard"))


@route("/features")
def features():
    return render_template("features.html", inds=[IND.INDUSTRIES[k] for k in IND.ORDER if k != "general"])


@route("/pricing")
def pricing():
    return render_template("pricing.html", plans=C.PLANS)


CHANGELOG = [
    ("This week", [
        "Post straight to Instagram, Facebook and LinkedIn — schedule it, and Debut sends it",
        "Your Instagram numbers come back on their own: followers, reach, and how each post did",
        "“How did it do?” — three taps after a post, and Debut learns what works for your business",
        "Templates build the whole plan: pick the date and the posts and tasks land on your calendar",
        "Reels get a shoot sheet: every shot, its seconds, what to film and what to say",
        "“Before you post” checks the caption hook, the hashtags, the ask and the file",
        "Use a post again elsewhere: carousel, story, LinkedIn or newsletter in one tap",
        "Ask for reviews: a short link, a QR code for the counter and a count of who you asked",
        "Print the month: one page for the wall, with tick boxes",
        "हिन्दी: the menu, the bottom bar and the main buttons",
        "Drafts survive a bad connection, and are offered back rather than lost",
    ]),
    ("Earlier this month", [
        "Plan my month in one tap, from the Idea Bank",
        "Do this again: repeat any post next week, next month or next year",
        "A suggested time to post, by industry, then by what you actually do",
        "A menu you can cut down to only what you use",
        "Link page for your Instagram bio, with visits and taps counted into Leads",
        "Instagram grid planner, and a full activity log of every change",
    ]),
    ("Earlier", ["Idea Bank, Team hub and Content ops dashboards", "Bold headline bands and big-number tiles",
                 "Undo and duplicate on every list"]),
]


@route("/templates")
def templates_gallery():
    """Signed in, these are real: one tap puts the whole campaign on the calendar. Signed out, it is
    still the shop window, but what it promises now exists."""
    import playbooks as P
    return render_template("templates_gallery.html", books=P.PLAYBOOKS,
                           summary=P.summary, today=S.today().isoformat())


@route("/templates/use/<key>", methods=["POST"])
def templates_use(key):
    """Build a template's campaign, posts and tasks around the date the person picked."""
    import playbooks as P
    p = P.BY_KEY.get(key)
    if not p:
        abort(404)
    if g.role not in ("owner", "admin", "lead", "manager"):
        abort(403)
    try:
        day = dt.date.fromisoformat((request.form.get("date") or "")[:10])
    except ValueError:
        flash("Pick the date first, then press Use this.")
        return redirect(url_for("templates_gallery"))
    m = mod("content_items")
    opts = {x[0]: x[3] for x in m["fields"] if x[2] == "select" and len(x) > 3}
    camp_name = f"{p['title']} · {day.strftime('%b %Y')}"
    made_posts = made_tasks = 0
    room = g.plan["records"] - S.record_count(W())
    if room <= 0:
        flash("You're at your plan's record limit, so I can't add this template.")
        return redirect(url_for("templates_gallery"))
    try:
        ins("campaigns", dict(workspace_id=W(), name=camp_name, status="Planning",
                              start_date=(day + dt.timedelta(days=min(i[0] for i in p["items"]))).isoformat(),
                              end_date=(day + dt.timedelta(days=max(i[0] for i in p["items"]))).isoformat(),
                              brief=p["desc"]))
    except Exception:
        camp_name = ""
    for offset, kind, title, channel, fmt in p["items"]:
        if made_posts + made_tasks >= room - 1:
            flash("You hit your plan's record limit part-way, so only some of the template was added.")
            break
        when = (day + dt.timedelta(days=offset)).isoformat()
        if kind == "task":
            ins("tasks", dict(workspace_id=W(), title=title[:200], status="To do", due_date=when,
                              assignee=g.user["name"] or "", priority="Medium",
                              description=f"From the {p['title']} template"[:200]))
            made_tasks += 1
        else:
            ins("content_items", dict(workspace_id=W(), title=title[:200], status="Planned", publish_date=when,
                                      channel=channel if channel in (opts.get("channel") or []) else "Other",
                                      format=fmt if fmt in (opts.get("format") or []) else "Post",
                                      campaign=camp_name, notes=f"From the {p['title']} template"[:200]))
            made_posts += 1
    S.audit("template_use", f"{p['title']} around {day.isoformat()}: {made_posts} posts, {made_tasks} tasks")
    flash(f"{p['title']} is on your calendar: {made_posts} posts and {made_tasks} tasks, "
          f"from {(day + dt.timedelta(days=min(i[0] for i in p['items']))).strftime('%d %b')}. \U0001f4c5")
    return redirect(url_for("calendar_view", d=day.isoformat()))


@route("/cron/morning")
def cron_morning():
    """Daily job for a free external scheduler: /cron/morning?key=<CRON_KEY>. Sends the email digests and the morning push."""
    import hmac
    key = request.args.get("key", "")
    if not C.CRON_KEY or not hmac.compare_digest(key, C.CRON_KEY):
        abort(404)
    return jsonify(digests=S.send_digests(), pushes=S.morning_push(), nudges=S.client_approval_nudges(), reminders=S.fire_due_reminders())


@route("/cron/reminders")
def cron_reminders():
    """Run every 5 to 15 minutes: /cron/reminders?key=<CRON_KEY>. Sends reminders that have come due."""
    import hmac
    key = request.args.get("key", "")
    if not C.CRON_KEY or not hmac.compare_digest(key, C.CRON_KEY):
        abort(404)
    return jsonify(sent=S.fire_due_reminders())


@route("/reminders/add", methods=["POST"])
def reminder_add():
    text = (request.form.get("text") or "").strip()[:200]
    when = request.form.get("when", "")
    now = S.now_ist()
    if when == "1h":
        at = now + dt.timedelta(hours=1)
    elif when == "tonight":
        at = now.replace(hour=20, minute=0) if now.hour < 20 else now + dt.timedelta(hours=1)
    elif when == "tomorrow":
        at = (now + dt.timedelta(days=1)).replace(hour=9, minute=0)
    else:
        try:
            at = dt.datetime.strptime((request.form.get("date") or "") + " " + (request.form.get("time") or "09:00"), "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Pick a date and time for the reminder.")
            return redirect(request.referrer or url_for("dashboard"))
    if not text:
        flash("Write what to remind you about.")
        return redirect(request.referrer or url_for("dashboard"))
    link = (request.form.get("link") or "")[:300]
    if not link.startswith("/") or link.startswith("//"):
        link = ""
    rep = request.form.get("repeat", "")
    target, tname = g.user["id"], ""
    if request.form.get("for", "").isdigit() and int(request.form["for"]) != g.user["id"] and g.role != "client":
        m = q("SELECT u.id, u.name FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=? AND m.user_id=? AND m.role!='client'", (W(), int(request.form["for"])), one=True)
        if m:
            target, tname = m["id"], (m["name"] or "your teammate").split()[0]
    ins("reminders", dict(workspace_id=W(), user_id=target, by_user=g.user["id"], text=text, remind_at=at.strftime("%Y-%m-%d %H:%M"), link=link, repeat=rep if rep in ("daily", "weekly") else ""))
    flash("⏰ Reminder set for " + (tname + " on " if tname else "") + at.strftime("%d %b, %I:%M %p") + (". They will get a notification." if tname else ". Only you see it."))
    return redirect(request.referrer or url_for("dashboard"))


@route("/reminders")
def reminders_page():
    S.fire_due_reminders(g.user["id"])
    rows = q("SELECT * FROM reminders WHERE workspace_id=? AND user_id=? AND done=0 ORDER BY remind_at", (W(), g.user["id"]))
    past = q("SELECT * FROM reminders WHERE workspace_id=? AND user_id=? AND done=1 ORDER BY remind_at DESC LIMIT 10", (W(), g.user["id"]))
    team = q("SELECT u.id, u.name FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=? AND m.role!='client' AND u.id!=? ORDER BY u.name", (W(), g.user["id"])) if g.role != "client" else []
    return render_template("reminders.html", team=team, rows=rows, past=past, tomorrow=(S.today() + dt.timedelta(days=1)).isoformat())


@route("/reminders/<int:rid>/snooze", methods=["POST"])
def reminder_snooze(rid):
    now = S.now_ist()
    at = now + dt.timedelta(hours=1) if request.form.get("by") == "1h" else (now + dt.timedelta(days=1)).replace(hour=9, minute=0)
    ex("UPDATE reminders SET remind_at=?, fired=0, done=0 WHERE id=? AND user_id=? AND workspace_id=?", (at.strftime("%Y-%m-%d %H:%M"), rid, g.user["id"], W()))
    flash("Snoozed until " + at.strftime("%d %b, %I:%M %p") + ".")
    return redirect(request.referrer or url_for("reminders_page"))


@route("/reminders/<int:rid>/delete", methods=["POST"])
def reminder_delete(rid):
    S.audit("reminder_delete", f"reminder#{rid}")
    ex("DELETE FROM reminders WHERE id=? AND user_id=? AND workspace_id=?", (rid, g.user["id"], W()))
    return redirect(request.referrer or url_for("reminders_page"))


@route("/reminders/<int:rid>/done", methods=["POST"])
def reminder_done(rid):
    S.audit("reminder_done", f"reminder#{rid}")
    ex("UPDATE reminders SET done=1 WHERE id=? AND user_id=? AND workspace_id=?", (rid, g.user["id"], W()))
    return redirect(request.referrer or url_for("dashboard"))


@route("/cron/evening")
def cron_evening():
    """Second daily job: /cron/evening?key=<CRON_KEY> (about 8pm IST). Streak-saver push."""
    import hmac
    key = request.args.get("key", "")
    if not C.CRON_KEY or not hmac.compare_digest(key, C.CRON_KEY):
        abort(404)
    return jsonify(pushes=S.evening_push())


CAMP_KINDS = [("campaigns", "📣 Campaign", "start_date", "end_date"), ("promotions", "🎪 Promotion", "start_date", "end_date"),
              ("events", "🎟️ Event", "date", "date"), ("gtm_plans", "🚀 Launch plan", "launch_date", "launch_date")]


@route("/campaigns")
def campaigns_all():
    """One list for campaigns, promotions, events and launch plans (they overlap), with the kind as a filter. Each row opens its own full form."""
    want = request.args.get("type", "")
    rows = []
    for key, label, a, b in CAMP_KINDS:
        if want and want != key:
            continue
        cols = {r[0] for r in mod(key)["fields"]}
        for r in q(f"SELECT * FROM {key} WHERE workspace_id=? ORDER BY id DESC LIMIT 300", (W(),)):
            r = dict(r)
            rows.append(dict(key=key, kind=label, id=r["id"], name=r.get("name") or r.get("product") or "Untitled", channel=r.get("channel") or r.get("channels") or "",
                             start=r.get(a) or "", end=r.get(b) or "", status=r.get("status") or r.get("stage") or "", budget=r.get("budget") or ""))
    rows.sort(key=lambda x: (x["start"] == "", x["start"]), reverse=True)
    counts = {k: q(f"SELECT COUNT(*) c FROM {k} WHERE workspace_id=?", (W(),), one=True)["c"] for k, *_ in CAMP_KINDS}
    return render_template("campaigns_all.html", rows=rows, want=want, kinds=CAMP_KINDS, counts=counts)


@route("/tools")
def tools_page():
    """Every tool that is not in the main sidebar, grouped and searchable: this is what "More tools" opens."""
    return render_template("tools.html")


@route("/healthz")
def healthz():
    return "ok", 200, {"Cache-Control": "no-store"}


@route("/about")
def about():
    return render_template("about.html")


@route("/channels")
def channels_page():
    return render_template("channels_page.html", groups=CHANNEL_GROUPS)


CHANNEL_GROUPS = [
    ("Social", "Plan posts, carousels, reels and stories", ["Instagram", "Facebook", "LinkedIn", "X / Threads", "YouTube & Shorts", "Pinterest", "ShareChat / Moj"]),
    ("Messaging", "Broadcasts, status and newsletters", ["WhatsApp Business", "Telegram", "Email newsletter", "SMS"]),
    ("Food and local", "Offers, menus, festival hours and reviews", ["Zomato", "Swiggy", "Google Business Profile", "Dineout", "Magicpin", "JustDial"]),
    ("Marketplaces", "Sale dates, listings and coupons", ["Amazon", "Flipkart", "Myntra", "Nykaa", "Meesho", "Your own website / Shopify"]),
    ("Industry platforms", "Where your buyers actually look", ["MakeMyTrip", "Booking.com", "99acres / MagicBricks", "Practo", "IndiaMART", "Product Hunt"]),
    ("Ads and search", "Budgets and results next to your content", ["Google Ads", "Meta Ads", "LinkedIn Ads", "SEO / blog"]),
    ("Offline", "Shelf, print and events", ["Sampling & events", "Shelf displays (POSM)", "Print & outdoor", "Distributor schemes"]),
]


@route("/changelog")
def changelog():
    return render_template("changelog.html", log=CHANGELOG)


AGENCY_SIZES = ["1-5 people", "6-15 people", "16-50 people", "50+ people"]


@route("/agency", methods=["GET", "POST"])
@limiter.limit("6 per hour", methods=["POST"])
def agency_enquiry():
    """Agency plans have no public price: the buyer tells us about their team and we come back with a quote."""
    f = {k: S.clean_text(request.form.get(k), 300) for k in ("name", "email", "phone", "company", "size", "clients", "message")}
    if request.method == "POST":
        if request.form.get("website"):                              # honeypot: real people leave this empty
            return redirect(url_for("agency_enquiry", sent=1))
        if not f["name"] or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", f["email"] or "") or not f["company"]:
            flash("Please add your name, a valid work email and your company name.")
            return render_template("agency.html", f=f, sizes=AGENCY_SIZES), 400
        body = "\n".join(f"{k.title()}: {v}" for k, v in f.items() if v)
        ins("feedback", dict(workspace_id=(g.ws["id"] if g.get("ws") else None), user_id=(g.user["id"] if g.get("user") else None), kind="agency", page="/agency", message=body))
        S.send_email(C.SUPPORT_EMAIL, f"[{C.APP_NAME}] Agency plan enquiry from {f['company']}", body)
        return redirect(url_for("agency_enquiry", sent=1))
    if g.get("user"):
        f["name"], f["email"] = g.user["name"], g.user["email"]
    return render_template("agency.html", f=f, sizes=AGENCY_SIZES, sent=bool(request.args.get("sent")))


@route("/manual")
def manual():
    return render_template("manual.html")


@route("/terms")
def terms():
    return render_template("terms.html")


@route("/privacy")
def privacy():
    return render_template("privacy.html")


@route("/health")
def health():
    try:
        q("SELECT 1 AS ok", one=True)
        from app import _asset_v
        return jsonify(status="ok", build=_asset_v(), menu="single-v3", switch=False)
    except Exception:
        return jsonify(status="db_error"), 503


@route("/glossary")
def glossary():
    """The jargon buster lives inside Help now - one place to look things up, not two."""
    return redirect(url_for("help_centre") + "#glossary")


@route("/help")
def help_centre():
    return render_template("help.html", terms=GLOSSARY)


@route("/contact")
def contact():
    return render_template("contact.html")


@route("/refunds")
def refunds():
    return render_template("refunds.html")


@route("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\nDisallow: /app\nDisallow: /m/\nDisallow: /api/\nDisallow: /hooks/\nDisallow: /r/\nDisallow: /lead/\nDisallow: /apply/\nDisallow: /calendar/\n"
                    f"Sitemap: {S.app_url()}/sitemap.xml\n", mimetype="text/plain")


@route("/sitemap.xml")
def sitemap():
    urls = ["/", "/features", "/templates", "/channels", "/about", "/changelog", "/pricing", "/terms", "/privacy", "/refunds", "/contact"]
    body = "".join(f"<url><loc>{S.app_url()}{u}</loc><changefreq>monthly</changefreq></url>" for u in urls)
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + body + "</urlset>", mimetype="application/xml")


# ----------------------------------------------------------------- dashboard
def _ws_age(today):
    """Days since this workspace was made; a missing or odd date counts as old rather than crashing Home."""
    try:
        return (today - dt.date.fromisoformat(str(g.ws["created_at"])[:10])).days
    except ValueError:
        return 999


@route("/app")
def dashboard():
    if g.role == "client":
        return redirect(url_for("portal"))
    w, today = W(), S.today()
    t, wk = today.isoformat(), (today + dt.timedelta(days=7)).isoformat()
    _ci, _cia = cscope("content_items")
    _ct, _cta = cscope("tasks")
    upcoming = q(f"SELECT * FROM content_items WHERE workspace_id=? AND {_ci} AND publish_date BETWEEN ? AND ? ORDER BY publish_date", [w] + _cia + [t, wk])
    overdue = q(f"SELECT * FROM tasks WHERE workspace_id=? AND {_ct} AND status!='Done' AND due_date!='' AND due_date<? ORDER BY due_date", [w] + _cta + [t])
    due_soon = q(f"SELECT * FROM tasks WHERE workspace_id=? AND {_ct} AND status!='Done' AND due_date BETWEEN ? AND ? ORDER BY due_date", [w] + _cta + [t, wk])
    camps = q("SELECT * FROM campaigns WHERE workspace_id=?", (w,))
    budget, spent = sum(num(c["budget"]) for c in camps), sum(num(c["spent"]) for c in camps)
    live = len([c for c in camps if c["status"] == "Live"])
    total = q("SELECT COUNT(*) c FROM launch_checklist WHERE workspace_id=?", (w,), one=True)["c"]
    done = q("SELECT COUNT(*) c FROM launch_checklist WHERE workspace_id=? AND status='Done'", (w,), one=True)["c"]
    pipeline = q(f"SELECT status, COUNT(*) c FROM content_items WHERE workspace_id=? AND {_ci} GROUP BY status", [w] + _cia)
    leads = q("SELECT stage, COUNT(*) c FROM leads WHERE workspace_id=? GROUP BY stage", (w,))
    refs = q("SELECT * FROM assets WHERE workspace_id=? AND url!='' ORDER BY id DESC LIMIT 5", (w,))
    promos = q("SELECT * FROM promotions WHERE workspace_id=? AND (status='Live' OR start_date BETWEEN ? AND ?) ORDER BY start_date", (w, t, (today + dt.timedelta(days=14)).isoformat()))
    events = q("SELECT * FROM events WHERE workspace_id=? AND date BETWEEN ? AND ? AND status!='Cancelled' ORDER BY date", (w, t, (today + dt.timedelta(days=30)).isoformat()))
    followups = q("SELECT * FROM influencers WHERE workspace_id=? AND next_followup!='' AND next_followup<=? AND status NOT IN ('Booked','Delivered','Rejected') ORDER BY next_followup", (w, t))
    # "Today": one short, auto-built list for a founder running marketing solo - what's overdue from
    # before (the rollover from yesterday and earlier) plus what's actually due today, so there's one
    # place to look each morning instead of checking every module by hand.
    content_catchup = q(f"SELECT * FROM content_items WHERE workspace_id=? AND {_ci} AND publish_date!='' AND publish_date<=? AND status NOT IN ('Published','On hold') ORDER BY publish_date", [w] + _cia + [t])
    due_today_tasks = [r for r in due_soon if r["due_date"] == t]
    # teams: "Mine" shows what is assigned to you (plus anything nobody owns); owners see everyone by default
    team_n = q("SELECT COUNT(*) c FROM memberships WHERE workspace_id=? AND role!='client'", (w,), one=True)["c"]
    can_toggle = team_n > 1 and g.role in ("owner", "admin", "lead", "manager")
    who = request.args.get("who") or ("all" if g.role in ("owner", "admin") else "mine")
    if can_toggle and who == "mine":
        me = {(g.user["name"] or "").strip().lower(), (g.user["email"] or "").strip().lower()} - {""}
        keep = lambda r, col: (r[col] or "").strip().lower() in me or not (r[col] or "").strip()
        overdue = [r for r in overdue if keep(r, "assignee")]
        due_today_tasks = [r for r in due_today_tasks if keep(r, "assignee")]
        content_catchup = [r for r in content_catchup if keep(r, "owner")]
    review_items = []
    if g.role in ("owner", "admin", "lead", "manager"):
        review_items = [dict(icon="👀", text=f"Waiting for your review: {r['title']}", href=url_for("m_edit", key="content_items", rid=r["id"]))
                        for r in q("SELECT id, title FROM content_items WHERE workspace_id=? AND status='Review' ORDER BY publish_date LIMIT 5", (w,))]
    rhythm = []
    if g.role in ("owner", "admin", "lead", "manager"):
        if today.weekday() == 0 and len(upcoming) < 3 and q("SELECT 1 FROM content_items WHERE workspace_id=? LIMIT 1", (w,), one=True):
            rhythm.append(dict(icon="🗓️", text=f"Plan the week: only {len(upcoming)} post{'s' if len(upcoming) != 1 else ''} scheduled in the next 7 days", href=url_for("calendar_view")))
        if today.weekday() >= 4 and "analytics" in g.plan["features"] and q("SELECT 1 FROM kpis WHERE workspace_id=? LIMIT 1", (w,), one=True) and not q("SELECT 1 FROM kpis WHERE workspace_id=? AND period>=?", (w, (today - dt.timedelta(days=6)).isoformat()), one=True):
            rhythm.append(dict(icon="📈", text="Log this week's numbers (or import a platform report)", href=url_for("analytics")))
    today_items = (
        [dict(icon="⏰", text=f"Overdue: {r['title']}", href=url_for("m_edit", key="tasks", rid=r["id"]), tid=r["id"], name=r["title"]) for r in overdue] +
        [dict(icon="📝", text=f"{'Publish today' if r['publish_date'] == t else 'Overdue to publish'}: {r['title']}", href=(url_for("studio.studio", item=r["id"], post=1) if (r["studio"] or "") else url_for("m_edit", key="content_items", rid=r["id"])), tid=r["id"], name=r["title"], key="content_items", val="Published", label="Mark posted") for r in content_catchup] +
        [dict(icon="🗂️", text=f"Due today: {r['title']}", href=url_for("m_edit", key="tasks", rid=r["id"]), tid=r["id"], name=r["title"]) for r in due_today_tasks] +
        [dict(icon="🤳", text=f"Follow up: {r['name']}", href=url_for("outreach", iid=r["id"])) for r in followups] +
        review_items + rhythm
    )
    today_more = max(0, len(today_items) - 8)
    today_items = today_items[:8]
    if g.role in ("owner", "admin", "manager", "lead"):      # untouched suggestions that have gone by are noise, not backlog
        ex("DELETE FROM content_items WHERE workspace_id=? AND status='Idea' AND notes LIKE 'Suggested by Debut%' AND publish_date<>'' AND publish_date<?", (w, (today - dt.timedelta(days=2)).isoformat()))
    week_plan = []
    welcome = False
    wa_url = ""
    if g.role in ("owner", "admin", "manager", "lead"):
        week_plan = q("SELECT id, title, channel, publish_date FROM content_items WHERE workspace_id=? AND status='Idea' AND publish_date BETWEEN ? AND ? ORDER BY publish_date LIMIT 8", (w, t, (today + dt.timedelta(days=7)).isoformat()))
        welcome = bool(q("SELECT 1 FROM content_items WHERE workspace_id=? AND status='Idea' AND notes LIKE 'Suggested by Debut%' LIMIT 1", (w,), one=True)) and not q("SELECT 1 FROM audit_log WHERE workspace_id=? AND action='welcome_done' LIMIT 1", (w,), one=True)
    first_week_card = (g.role in ("owner", "admin", "manager", "lead") and not welcome
                       and not q("SELECT 1 FROM kpis WHERE workspace_id=? LIMIT 1", (w,), one=True)
                       and bool(q("SELECT 1 FROM content_items WHERE workspace_id=? LIMIT 1", (w,), one=True))
                       and _ws_age(today) <= 21)
    low_cal = (g.role in ("owner", "admin", "manager", "lead") and not welcome and not week_plan and len(upcoming) < 3
               and bool(q("SELECT 1 FROM content_items WHERE workspace_id=? LIMIT 1", (w,), one=True)))
    topped = 0
    age_days = _ws_age(today)
    if low_cal and not (g.user["email"] or "").endswith("@demo.debut.invalid") and age_days >= 3:
        since_ts = (dt.datetime.utcnow() - dt.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        # claim the top-up in one atomic statement, so two tabs opening at once cannot both add posts
        claimed = ex("INSERT INTO audit_log (workspace_id, user_id, action, detail) SELECT CAST(? AS INTEGER), CAST(? AS INTEGER), 'auto_topup', 'claim' WHERE NOT EXISTS (SELECT 1 FROM audit_log WHERE workspace_id=? AND action='auto_topup' AND created_at>=?)",
                     (w, g.user["id"], w, since_ts))
        if claimed:      # the calendar ran low and nobody came back to refill it: do it quietly, as Ideas they can review
            topped = S.plan_more_posts(w, g.ws["industry"] or "general")
            if topped:
                low_cal = False
    lines = [f"Today on {g.ws['name']}:"] + [f"• {it['text']}" for it in today_items[:5]] + [f"• Coming up: {u['title']} ({u['publish_date']})" for u in list(upcoming)[:3]]
    if len(lines) > 1:
        from urllib.parse import quote
        wa_url = "https://wa.me/?text=" + quote("\n".join(lines))
    tiles = []
    for k in ("content_items", "campaigns", "promotions", "events", "content_orders", "creators", "tasks", "leads", "influencers"):
        if locked(k) or (g.role == "creator" and k not in CREATOR_MODULES):
            continue
        m = MODULES[k]
        _c, _ca = cscope(k)
        tiles.append((m["icon"], m["title"], q(f"SELECT COUNT(*) c FROM {k} WHERE workspace_id=? AND {_c}", [w] + _ca, one=True)["c"], url_for("m_list", key=k)))
    if True:
        tiles.append(("🖼️", "Mood Boards", q("SELECT COUNT(*) c FROM boards WHERE workspace_id=?", (w,), one=True)["c"], url_for("moodboards")))
    cnt = lambda tbl: q(f"SELECT COUNT(*) c FROM {tbl} WHERE workspace_id=?", (w,), one=True)["c"]
    industry = g.ws["industry"]
    # the "audience" step changes with the kind of business
    if industry in ("b2b", "saas", "agency", "fintech", "startup"):
        third = ("Add your first target account", cnt("accounts") > 0, url_for("m_new", key="accounts"))
    else:
        third = ("Add influencer prospects", cnt("influencers") > 0, url_for("discover"))
    steps = ([("Pick your industry (it tailors everything)", industry not in (None, "", "general"), url_for("ws.account"))] if g.role in ("owner", "admin") else []) + [
             ("Write your first GTM plan", cnt("gtm_plans") > 0, url_for("m_new", key="gtm_plans")),
             ("Add content to the calendar", cnt("content_items") > 0, url_for("m_new", key="content_items")),
             ("Create a mood board", cnt("boards") > 0, url_for("moodboards")),
             third,
             ("Capture your first lead", cnt("leads") > 0, url_for("ws.integrations") if g.role in ("owner", "admin", "lead", "manager") else url_for("m_new", key="leads")),
             ("Invite a teammate", cnt("memberships") > 1, url_for("ws.team")),
             ] + ([("Verify your email", bool(g.user["email_verified"]), url_for("ws.account"))] if C.SMTP_HOST else [])      # no mail server, no way to verify: do not show a step nobody can finish
    sug = q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status='Idea' AND notes LIKE 'Suggested by Debut%'", (w,), one=True)["c"]
    if sug and g.role in ("owner", "admin", "manager"):      # day one: the first job is to look at the two weeks already planned
        steps = [("Look over your first 2 weeks of posts", False, url_for("calendar_view"))] + steps
    if g.role in ("owner", "admin", "manager", "lead", "creator"):      # the studio is the wow moment, so it is the first thing a new person is pointed at
        made = q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND studio<>''", (w,), one=True)["c"]
        steps = [("Design your first post in 60 seconds", made > 0, url_for("studio.studio"))] + steps
    wins = cnt("content_items") - sug + cnt("campaigns") + cnt("leads")
    pending = [x for x in steps if not x[1]]
    if wins and cnt("memberships") <= 1 and g.role in ("owner", "admin"):
        pending.sort(key=lambda x: 0 if x[0] == "Invite a teammate" else 1)
    next_step = pending[0] if pending else None
    trial_card = pmf_ask = None
    if g.role in ("owner", "admin"):
        dl = S.trial_days_left(g.ws)
        if g.plan_key == "trial" and dl is not None and dl <= 2:
            trial_card = dict(days=max(dl, 0), posts=cnt("content_items"), plans=cnt("gtm_plans"), leads=cnt("leads"))
        try:
            age = (S.today() - dt.date.fromisoformat(str(g.user["created_at"])[:10])).days
        except Exception:
            age = 0
        if age >= 7 and not q("SELECT id FROM feedback WHERE user_id=? AND kind='pmf'", (g.user["id"],), one=True):
            pmf_ask = True
    late_posts = len([r for r in content_catchup if r["publish_date"] < t]) if g.role in ("owner", "admin", "manager", "lead") else 0
    promo = None
    if g.role not in ("viewer", "client", "creator"):
        try:
            import studio as ST
            sg = ST.suggestions(W(), g.ws["industry"], S.today())
            promo = next((c for c in sg if not c["trend"] and c["kind"] not in ("Evergreen",) and c["days"] <= 45), None) or next((c for c in sg if c["trend"]), None)
        except Exception:
            promo = None
    prog = _progress() if g.role not in ("viewer", "client") else None
    month_card = None
    if g.role not in ("client",):
        try:
            m0 = S.today().strftime("%Y-%m")
            _c = lambda sql, *a: q(sql, (w, *a), one=True)["c"]
            month_card = dict(
                posted=_c("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status='Published' AND publish_date LIKE ?", m0 + "%"),
                planned=_c("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status!='Published' AND publish_date LIKE ?", m0 + "%"),
                tasks=_c("SELECT COUNT(*) c FROM tasks WHERE workspace_id=? AND status='Done'"),
                leads=_c("SELECT COUNT(*) c FROM leads WHERE workspace_id=? AND created_at>=? AND created_at<?", m0 + "-01 00:00:00", (S.today().replace(day=28) + dt.timedelta(days=5)).replace(day=1).strftime("%Y-%m-%d") + " 00:00:00"),
                month=S.today().strftime("%B"))
        except Exception:
            month_card = None
    import deb as _deb
    S.fire_due_reminders(g.user["id"])
    my_rem = q("SELECT * FROM reminders WHERE workspace_id=? AND user_id=? AND done=0 ORDER BY remind_at LIMIT 6", (w, g.user["id"]))
    return render_template("dashboard.html", my_rem=my_rem, month_card=month_card, bento=_deb.bento(), streak_n=_streak_info()[0], spark=_spark(), prog=prog, promo=promo, topped=topped, late_posts=late_posts, week_plan=week_plan, low_cal=low_cal, first_week_card=first_week_card, welcome=welcome, wa_url=wa_url, goals_channels=CHANNELS, fresh=bool(sug), trial_card=trial_card, pmf_ask=pmf_ask, next_step=next_step, try_next=next_tools(w) if g.role in ("owner", "admin", "lead", "manager") else [], upcoming=upcoming, overdue=overdue, due_soon=due_soon, budget=budget, spent=spent, live=live, total=total, done=done,
                           pipeline=pipeline, leads=leads, refs=refs, tiles=tiles, promos=promos, events=events, followups=followups,
                           today_items=today_items, today_more=today_more, can_toggle=can_toggle, who=who,
                           steps=steps, steps_done=all(s[1] for s in steps), streak=_streak(), streak_froze=_streak_info()[1], kudos_latest=q("SELECT k.emoji, k.note, a.name AS aname, a.email AS aemail, b.name AS bname, b.email AS bemail FROM kudos k JOIN users a ON a.id=k.from_user JOIN users b ON b.id=k.to_user WHERE k.workspace_id=? ORDER BY k.id DESC LIMIT 3", (w,)),
                           ind=IND.get(g.ws["industry"]), pulse=S.latest_pulse(w),
                           usage=dict(records=S.record_count(w), boards=cnt("boards"), credits=S.credits_used(w)) if g.plan_key == "free" else None)



LEVELS = [(0, "Newcomer"), (30, "Planner"), (80, "Creator"), (160, "Publisher"), (280, "Strategist"), (450, "Brand builder"), (700, "Studio pro"), (1000, "Marketing machine"), (1500, "Legend")]
XP_WEIGHT = {"studio_save": 10, "studio_done": 15, "promo_plan": 20, "demo_blocked": 0}


def _progress():
    """Level and this-week wins for the person looking, worked out from what they have done (no extra tables)."""
    rows = q("SELECT action, COUNT(*) c FROM audit_log WHERE workspace_id=? AND user_id=? GROUP BY action", (W(), g.user["id"]))
    xp = sum(min(r["c"], 200) * XP_WEIGHT.get(r["action"], 1) for r in rows)
    i = max(n for n, (need, _) in enumerate(LEVELS) if xp >= need)
    nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
    base = LEVELS[i][0]
    since = (S.today() - dt.timedelta(days=6)).isoformat()
    wk = q("SELECT action, COUNT(*) c FROM audit_log WHERE workspace_id=? AND user_id=? AND created_at>=? AND action IN ('studio_save','studio_done','promo_plan') GROUP BY action", (W(), g.user["id"], since))
    wk = {r["action"]: r["c"] for r in wk}
    cnt = {r["action"]: r["c"] for r in rows}
    BADGES = [("🎨", "First design", cnt.get("studio_save", 0) >= 1), ("🗓️", "Series maker", cnt.get("studio_save", 0) >= 4), ("🚀", "Posted 5", cnt.get("studio_done", 0) >= 5),
              ("🎯", "Promo planner", cnt.get("promo_plan", 0) >= 1), ("🔗", "Bio is live", cnt.get("bio_save", 0) >= 1), ("🔥", "7-day streak", _streak_info()[0] >= 7)]
    return dict(badges=BADGES, level=i + 1, name=LEVELS[i][1], xp=xp, nxt=nxt[1] if nxt else "", to_next=(nxt[0] - xp) if nxt else 0,
                pct=int(100 * (xp - base) / (nxt[0] - base)) if nxt else 100, designed=wk.get("studio_save", 0), posted=wk.get("studio_done", 0), planned=wk.get("promo_plan", 0))


def _streak_info():
    """(days, froze). Consecutive days on which this user did something here. One missed day is forgiven (a free 'streak freeze'),
    and another is forgiven only after 7 more active days, so one bad day does not wipe out a long streak."""
    import datetime as _dt
    rows = q("SELECT created_at FROM audit_log WHERE workspace_id=? AND user_id=? ORDER BY id DESC LIMIT 1500", (W(), g.user["id"]))
    days = {str(r["created_at"])[:10] for r in rows}
    d, n, froze, since = S.today(), 0, False, 99
    if d.isoformat() not in days:
        d -= _dt.timedelta(days=1)
    while True:
        if d.isoformat() in days:
            n += 1
            since += 1
        elif n > 0 and since >= 7 and (d - _dt.timedelta(days=1)).isoformat() in days:
            froze, since = True, 0
        else:
            break
        d -= _dt.timedelta(days=1)
    return n, froze


SPARKS = ["Show the thing you made today, mess and all.", "Answer the question customers ask you most, in 30 seconds.", "Post a before and after.",
          "Share one mistake you made and what it taught you.", "Introduce the person behind the brand.", "Ask your followers to pick A or B.",
          "Tell the story of your first customer.", "Show how it is made, start to finish.", "Share a small win from this week.",
          "Bust a myth people believe about your industry.", "Post your top 3 tips, one per slide.", "Thank a customer and show their words.",
          "Give a peek at what is launching next.", "Show your workspace or your shelf."]


def _spark():
    import datetime as _dt
    return SPARKS[(S.today().toordinal() + (W() or 0)) % len(SPARKS)]


def _streak():
    return _streak_info()[0]


# ----------------------------------------------------------------- generic CRUD
GAP_BANNER_KEYS = {"brand_kit": {"brand_kit"}, "campaigns": {"campaigns"}, "content_items": {"content_items", "content_overdue"},
                    "tasks": {"tasks"}, "leads": {"leads"}}


FIRST_WINS = {"content_items": "First post planned! 🎉 That is how it starts. Next up: put a date on it so it lands on the calendar.",
              "campaigns": "Your first campaign is live in Debut! 🎉 Add a budget and a goal so you can see how it performs.",
              "leads": "First lead caught! 🎉 Follow up while they are warm."}
LIST_LAYOUT = {"leads": "people", "influencers": "people", "personas": "people", "creators": "people", "clients": "people", "pr_contacts": "people", "accounts": "people",
               "content_items": "cards", "campaigns": "cards", "tasks": "checklist", "promotions": "cards", "events": "cards", "gtm_plans": "cards", "experiments": "cards", "content_orders": "cards"}


@route("/m/<key>")
def m_list(key):
    m = mod(key)
    if key == "key_dates" and g.role not in ("viewer", "client"):
        S.dedupe_key_dates(W())      # "Christmas" and "Christmas Day" are one date
    hidden = HIDDEN_FOR_CREATOR.get(key, set()) if g.role == "creator" else set()
    gap_banner = None
    if key in GAP_BANNER_KEYS:
        cnt = sum(gp["count"] for gp in _marketing_gaps() if gp["key"] in GAP_BANNER_KEYS[key])
        gap_banner = cnt or None
    qs, f = request.args.get("q", "").strip(), request.args.get("f", "")
    sql, args, where = f"SELECT * FROM {key} WHERE workspace_id=?", [W()], []
    _c, _ca = cscope(key)
    if _ca:
        where.append(_c)
        args += _ca
    if qs:
        searchable = [x for x in m["fields"] if x[0] not in hidden]
        where.append("(" + " OR ".join(f"LOWER({qi(x[0])}) LIKE ?" for x in searchable) + ")")
        args += [f"%{qs.lower()}%"] * len(searchable)
    ffield = next((x for x in m["fields"] if x[0] == m.get("filter")), None)
    if f and ffield:
        where.append(f"{qi(ffield[0])}=?")
        args.append(f)
    if where:
        sql += " AND " + " AND ".join(where)
    default_manual = key in MANUAL_ORDER and key != "content_items"   # these open in the hand-made order (identical to newest-first until someone drags)
    default_order = f"sort_order ASC, {_tb(key)}" if default_manual else ("publish_date DESC, id DESC" if key == "content_items" else "id DESC")
    choices = sort_choices(key, m)
    sort = request.args.get("sort", "")
    direction = "desc" if request.args.get("dir") == "desc" else "asc"
    if sort.startswith("col:") and sort[4:] in [c for c in m["cols"] if c not in hidden]:
        order = order_sql(key, m, sort, direction)
    elif sort in [c for c, _ in choices]:
        order = order_sql(key, m, sort)
    else:
        sort, order = "", default_order
    page = min(max(1, S.to_int(request.args.get("page"), 1)), 10000)
    per = 100
    rows = q(sql + f" ORDER BY {order} LIMIT {per + 1} OFFSET {(page - 1) * per}", args)
    types = {x[0]: (x[1], x[2]) for x in m["fields"]}
    cols = [(c, types[c][0], types[c][1]) for c in m["cols"] if c not in hidden]
    dist = []
    if ffield and ffield[0] not in hidden:
        dist = [(r["v"], r["c"]) for r in q(f"SELECT {qi(ffield[0])} v, COUNT(*) c FROM {key} WHERE workspace_id=? AND {qi(ffield[0])} IS NOT NULL AND {qi(ffield[0])}<>'' GROUP BY {qi(ffield[0])} ORDER BY c DESC", (W(),))]
    return render_template("crud_list.html", choices=choices, sort=sort, sdir=direction, default_manual=default_manual, can_drag=((sort == "manual" or (sort == "" and default_manual)) and key in MANUAL_ORDER and g.role != "viewer"), dist=dist, layout=LIST_LAYOUT.get(key), view=request.args.get("view", ""), key=key, m=m, rows=rows[:per], more=len(rows) > per, page=page, cols=cols, q=qs, f=f, ffield=ffield, gap_banner=gap_banner, bkeys={"campaigns": ("budget", "spent"), "promotions": ("budget", "spend")}.get(key))


def _hidden(key):
    return HIDDEN_FOR_CREATOR.get(key, set()) if g.role == "creator" else set()


@route("/m/<key>/new")
def m_new(key):
    modal = request.args.get("modal") == "1"
    tpl = "crud_form_frag.html" if modal else "crud_form.html"
    return render_template(tpl, key=key, m=mod(key), row=None, defaults=request.args, nxt=safe_next(""), team_names=S.team_names(W()), hidden=_hidden(key), required=REQUIRED.get(key, set()), modal=modal)


@route("/m/<key>/<int:rid>/edit")
def m_edit(key, rid):
    row = row_or_404(key, rid)
    modal = request.args.get("modal") == "1"
    tpl = "crud_form_frag.html" if modal else "crud_form.html"
    comments = q("SELECT c.*, u.name AS uname FROM comments c LEFT JOIN users u ON u.id=c.user_id WHERE c.workspace_id=? AND c.module=? AND c.record_id=? ORDER BY c.id", (W(), key, rid))
    return render_template(tpl, key=key, m=mod(key), row=row, defaults={}, nxt=safe_next(""), team_names=S.team_names(W()), comments=comments, reacts=reactions_for(key, rid), hidden=_hidden(key), required=REQUIRED.get(key, set()), modal=modal)


_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def norm_date(v):
    """Turn the date formats people really type or paste (13/11/2026, 13-Nov-26, Nov 13 2026, 2026-11, Excel serials)
    into ISO yyyy-mm-dd. Day-first is assumed for ambiguous numeric dates (India). Returns '' when it can't be understood."""
    v = (v or "").strip()
    if not v:
        return ""
    v = re.split(r"[T ](?=\d{1,2}:\d{2})", v)[0].strip()
    try:
        if re.fullmatch(r"20\d{6}", v):      # 20261101, the way GA4 writes a day
            return dt.date(int(v[:4]), int(v[4:6]), int(v[6:])).isoformat()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            return dt.date.fromisoformat(v).isoformat()
        m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})(?:[-/.](\d{1,2}))?", v)
        if m:
            return dt.date(int(m[1]), int(m[2]), int(m[3] or 1)).isoformat()
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})", v)
        if m:
            a, b, y = int(m[1]), int(m[2]), int(m[3])
            y += 2000 if y < 100 else 0
            d_, mo = (b, a) if (b > 12 and a <= 12) else (a, b)   # 11/13/2026 can only be month-first
            return dt.date(y, mo, d_).isoformat()
        t = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", v.lower()).replace(",", " ")
        m = re.fullmatch(r"(\d{1,2})[\s\-/.]+([a-z]{3,9})[\s\-/.]+(\d{2}|\d{4})", t)
        if m and m[2][:3] in _MONTHS:
            y = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
            return dt.date(y, _MONTHS[m[2][:3]], int(m[1])).isoformat()
        m = re.fullmatch(r"([a-z]{3,9})[\s\-/.]+(\d{1,2})[\s\-/.]+(\d{4})", t)
        if m and m[1][:3] in _MONTHS:
            return dt.date(int(m[3]), _MONTHS[m[1][:3]], int(m[2])).isoformat()
        m = re.fullmatch(r"([a-z]{3,9})[\s\-/.]+(\d{4})", t)
        if m and m[1][:3] in _MONTHS:
            return dt.date(int(m[2]), _MONTHS[m[1][:3]], 1).isoformat()
        if re.fullmatch(r"\d{5}(\.\d+)?", v) and 20000 < float(v) < 80000:   # an Excel serial date
            return (dt.date(1899, 12, 30) + dt.timedelta(days=int(float(v)))).isoformat()
    except ValueError:
        return ""
    return ""


def clean_fields(m, source, quiet=False, partial=False, report=None):
    """Validate/normalise submitted field values. quiet: no flash messages (API use). partial: only fields present in source.
    report: a dict that collects what had to be fixed ('dates', 'options') so an import can tell the user."""
    data = {}
    for n, label, typ, opts in m["fields"]:
        if partial and n not in source:
            continue
        if typ == "multi":
            raw = source.getlist(n) if hasattr(source, "getlist") else re.split(r"[,;]", str(source.get(n, "") or ""))
            low = {o.lower(): o for o in opts}
            data[n] = ", ".join(dict.fromkeys(low.get(x.strip().lower(), "") for x in raw if x.strip().lower() in low))
            continue
        v = S.clean_text(source.get(n, ""))
        if typ == "url":
            cv = S.clean_url(v)
            if v and not cv and not quiet:
                flash(f"“{label}” must be a valid http(s) link and was cleared.")
            v = cv
        elif typ == "select" and v and opts and v not in opts:
            hit = next((o for o in opts if o.lower() == v.lower()), None)
            if hit is None and report is not None:
                report.setdefault("options", []).append(f"{label}: “{v}”")
            v = hit or opts[0]
        elif typ == "date" and v:
            nv = norm_date(v)
            if not nv:
                if report is not None:
                    report.setdefault("dates", []).append(f"{label}: “{v}”")
                elif not quiet:
                    flash(f"“{label}” — “{v}” isn't a date we understand, so it was left empty. Try 13/11/2026 or 13 Nov 2026.")
            v = nv
        elif typ == "number" and v and not re.match(r"^-?\d+(\.\d+)?$", v):
            v = re.sub(r"[^\d.\-]", "", v)
        data[n] = v
    return data


RESTRICTED = {"content_items": {"Approved", "Scheduled", "Published"}, "content_orders": {"Approved", "Delivered", "Invoiced"}}
FALLBACK = {"content_items": "Review", "content_orders": "Editing / QA"}


def gate_status(key, new, old):
    """Approvals belong to leads and managers: creators can move work to review but cannot approve or publish it themselves."""
    if g.role == "creator" and new in RESTRICTED.get(key, ()) and new != old:
        flash("Only a lead or manager can approve or publish. This was sent for review instead.")
        return old if old and old not in RESTRICTED[key] else FALLBACK[key]
    return new


def _title(m, d):
    return str(d.get(m["fields"][0][0]) or "")[:80]


def changed_hooks(key, rid, m, new, old):
    """Notifications when work is assigned, sent for approval, or approved."""
    wid, me = W(), g.user["id"]
    who, title, link = (g.user["name"] or g.user["email"]), _title(m, {**(dict(old) if old else {}), **new}), url_for("m_edit", key=key, rid=rid)
    for f in ("assignee", "owner"):
        if f in new:
            if new[f] and (old is None or old[f] != new[f]):
                mem = S.find_member(wid, new[f])
                if mem and mem["uid"] != me:
                    S.notify(wid, mem["uid"], "assigned", f"{who} assigned you: {title}", link)
            break
    if key in RESTRICTED and "status" in new and (old is None or old["status"] != new["status"]):
        st = new["status"]
        if st in ("Review", "Editing / QA", "Client review"):
            for mem in S.members(wid):
                if mem["role"] in ("owner", "admin", "lead", "manager") and mem["uid"] != me:
                    S.notify(wid, mem["uid"], "approval", f"{who} sent for approval: {title}", link)
            if key == "content_items" and st == "Review":
                for cm in S.client_members(wid, ({**(dict(old) if old else {}), **new}).get("client")):
                    S.notify(wid, cm["uid"], "client_review", f"Ready for your review: {title}", url_for("portal_item", iid=rid))
        elif st == "Approved":
            src = {**(dict(old) if old else {}), **new}
            mem = S.find_member(wid, src.get("owner") or src.get("assignee") or "")
            if mem and mem["uid"] != me:
                S.notify(wid, mem["uid"], "approved", f"{who} approved: {title}", link)


@route("/m/<key>/save", methods=["POST"])
def m_save(key):
    m = mod(key)
    first_win = None
    raw_id = request.form.get("id")
    rid = S.to_int(raw_id)
    if raw_id and not rid:
        abort(400)
    old = row_or_404(key, rid) if rid else None
    modal = request.form.get("modal") == "1"
    tpl = "crud_form_frag.html" if modal else "crud_form.html"
    data = clean_fields(m, request.form)
    for f in _hidden(key):          # freelancers can neither see nor change the agency's money fields
        data.pop(f, None)
    missing = [label for n, label, typ, opts in m["fields"] if n in REQUIRED.get(key, set()) and not (data.get(n) or "").strip()]
    if missing:
        flash("Almost! Still missing: " + ", ".join(missing) + ".")
        if rid:
            row = dict(old) if old else {}
            row.update(data)
            row["id"] = rid
            comments = q("SELECT c.*, u.name AS uname FROM comments c LEFT JOIN users u ON u.id=c.user_id WHERE c.workspace_id=? AND c.module=? AND c.record_id=? ORDER BY c.id", (W(), key, rid))
            return render_template(tpl, key=key, m=m, row=row, defaults={}, nxt=safe_next(url_for("m_list", key=key)), team_names=S.team_names(W()), comments=comments, hidden=_hidden(key), required=REQUIRED.get(key, set()), modal=modal), 400
        return render_template(tpl, key=key, m=m, row=None, defaults=data, nxt=safe_next(url_for("m_list", key=key)), team_names=S.team_names(W()), hidden=_hidden(key), required=REQUIRED.get(key, set()), modal=modal), 400
    if key in RESTRICTED and "status" in data:
        data["status"] = gate_status(key, data["status"], old["status"] if old else "")
    if rid:
        ex(f"UPDATE {key} SET " + ",".join(f"{qi(n)}=?" for n in data) + " WHERE id=? AND workspace_id=?", list(data.values()) + [rid, W()])
        chg = S.change_summary(m, old, data)
        moved = any(c.split(":")[0] in ("Status", "Stage", "Publish date", "Due date", "Date") for c in chg)
        S.audit("move" if moved else "update", f"{key}#{rid} “{S.rec_label(data or old, m) or S.rec_label(old, m)}”" + (": " + "; ".join(chg) if chg else ""))
    else:
        if S.record_count(W()) >= g.plan["records"]:
            flash(f"You've reached the {g.plan['name']} plan limit of {g.plan['records']} items." + C.upsell(g.plan_key, "records", "records", "items") + " You can still edit, delete or export.")
            return redirect(url_for("billing.billing") if g.role in ("owner", "admin") else url_for("dashboard"))
        if key == "watchlist" and q("SELECT COUNT(*) c FROM watchlist WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["watch"]:
            flash(f"Your {g.plan['name']} plan can track {g.plan['watch']} items in Market Pulse. Remove one" + (" or upgrade:" + C.upsell(g.plan_key, "watch", "watch", "topics") if C.next_plan(g.plan_key) else "."))
            return redirect(url_for("m_list", key="watchlist"))
        data["workspace_id"] = W()
        if g.role == "creator" and CREATOR_OWN.get(key) and not (data.get(CREATOR_OWN[key]) or "").strip():
            data[CREATOR_OWN[key]] = g.user["name"] or g.user["email"]
        rid = ins(key, data)
        S.audit("create", f"{key}#{rid} “{S.rec_label(data, m)}”")
        first_win = FIRST_WINS.get(key) if q(f"SELECT COUNT(*) c FROM {key} WHERE workspace_id=?", (W(),), one=True)["c"] == 1 else None
    changed_hooks(key, rid, m, data, old)
    if first_win:
        flash(first_win)
        return redirect(safe_next(url_for("m_list", key=key)))
    _win = {"done", "published", "won", "completed", "approved", "closed won", "signed"}
    flash("Saved. 🎉" if (str(data.get("status", "")).lower() in _win or str(data.get("stage", "")).lower() in _win) else "Saved.")
    return redirect(safe_next(url_for("m_list", key=key)))


@route("/m/<key>/<int:rid>/delete", methods=["POST"])
def m_delete(key, rid):
    mod(key)
    row = row_or_404(key, rid)
    ex(f"DELETE FROM {key} WHERE id=? AND workspace_id=?", (rid, W()))
    S.audit("delete", f"{key}#{rid} “{S.rec_label(row, mod(key))}”")
    snap = {k: row[k] for k in row.keys() if k not in ("id", "workspace_id") and row[k] is not None}
    if len(json.dumps(snap, default=str)) < 2500:      # keep the cookie small; bigger records just can't be undone
        session["undo"] = {"key": key, "row": snap, "w": W()}
    flash("Deleted. 🗑️")
    return redirect(safe_next(url_for("m_list", key=key)))


# Dates a copied record should move on to, so "repeat this" needs no typing for the usual cases.
REPEAT_WHEN = {"week": 7, "month": 30, "year": 365}


@route("/m/<key>/<int:rid>/repeat", methods=["POST"])
def m_repeat(key, rid):
    """Copy a record onto a later date. Small businesses post the same things every year - the Diwali
    offer, the Monday reminder - and retyping them is the most common bit of pointless work in the app."""
    m = mod(key)
    if g.role in ("viewer", "client"):
        abort(403)
    row = row_or_404(key, rid)
    date_field = next((f[0] for f in m["fields"] if f[2] == "date"), None)
    when = (request.form.get("when") or "week").strip()
    data = {f[0]: (row[f[0]] or "") for f in m["fields"] if f[0] in row.keys()}
    label = S.rec_label(row, m)
    if date_field:
        try:
            base = dt.date.fromisoformat((row[date_field] or "")[:10])
        except ValueError:
            base = S.today()
        if when in REPEAT_WHEN:
            new_date = base + dt.timedelta(days=REPEAT_WHEN[when])
            while new_date <= S.today():                 # a copy of something old still lands in the future
                new_date += dt.timedelta(days=REPEAT_WHEN[when])
        else:
            try:
                new_date = dt.date.fromisoformat(when[:10])
            except ValueError:
                new_date = S.today() + dt.timedelta(days=7)
        data[date_field] = new_date.isoformat()
    if "status" in data:
        data["status"] = "Idea" if key == "content_items" else data["status"]
    data["workspace_id"] = W()
    new_id = ins(key, data)
    S.audit("repeat", f"{key}#{rid} \u2192 #{new_id} \u201c{label}\u201d")
    flash(f"Copied. The new one is on {data.get(date_field, 'your list') if date_field else 'your list'} \u2014 edit it below. \U0001f501")
    return redirect(url_for("m_edit", key=key, rid=new_id))


# Posting rhythms people actually keep. Used to spread a batch of ideas across the coming weeks
# instead of dropping them all on one day.

# Posts that work for any business, whatever it sells. Used to top up "Plan my month" when an
# industry's own idea list is short - asking for 8 posts and getting 3 is a broken promise.
EVERGREEN_IDEAS = [
    ("Trust", "Behind the scenes: how we actually make this", "Instagram", "Reel / Short"),
    ("Trust", "Meet the team: one person, one question", "Instagram", "Post"),
    ("Proof", "A customer in their own words", "Instagram", "Post"),
    ("Proof", "Before and after, with the honest details", "Instagram", "Carousel"),
    ("Teach", "The one mistake people make, and what to do instead", "Instagram", "Reel / Short"),
    ("Teach", "Answering the question we get asked every week", "Instagram", "Carousel"),
    ("Teach", "Three things worth knowing before you buy", "Instagram", "Carousel"),
    ("Offer", "What's new this month", "Instagram", "Post"),
    ("Offer", "A reason to come in this week", "WhatsApp", "Post"),
    ("Story", "Why we started, and what we refuse to change", "Instagram", "Post"),
    ("Story", "A day in the life here", "Instagram", "Story"),
    ("Ask", "Ask the audience: which of these two should we do next?", "Instagram", "Story"),
]

FILL_RHYTHM = {"2": 3, "3": 2, "5": 1}            # posts per week -> days between posts


@route("/m/content_items/<int:rid>/rate", methods=["POST"])
def content_rate(rid):
    """Three taps, three days after a post goes out. Over a month this is better evidence about what
    works for this business than anything its industry average can tell it."""
    if g.role in ("viewer", "client"):
        abort(403)
    import learn as L
    row_or_404("content_items", rid)
    if not L.rate(W(), rid, (request.form.get("rating") or "").strip(), g.user["id"]):
        abort(400)
    w = L.what_works(W())
    flash("Noted. " + (L.headline(W()) if w["n"] else "") or "Noted.")
    return redirect(_next_or(url_for("m_edit", key="content_items", rid=rid)))


def _next_or(default):
    return safe_next(default)


@route("/m/content_items/<int:rid>/repurpose", methods=["POST"])
def content_repurpose(rid):
    """One piece of work, placed again somewhere else. The idea was the hard part; the reformatting
    should not cost another evening."""
    if g.role in ("viewer", "client"):
        abort(403)
    import reels as R
    row = row_or_404("content_items", rid)
    to = (request.form.get("to") or "").strip()
    if to not in R.REPURPOSE:
        abort(400)
    fmt, channel, how = R.REPURPOSE[to]
    if S.record_count(W()) >= g.plan["records"]:
        flash("You're at your plan's record limit, so I can't add this.")
        return redirect(url_for("m_edit", key="content_items", rid=rid))
    m = mod("content_items")
    opts = {x[0]: x[3] for x in m["fields"] if x[2] == "select" and len(x) > 3}
    try:
        when = (dt.date.fromisoformat((row["publish_date"] or "")[:10]) + dt.timedelta(days=3)).isoformat()
    except ValueError:
        when = (S.today() + dt.timedelta(days=3)).isoformat()
    nid = ins("content_items", dict(
        workspace_id=W(), title=f"{row['title']} ({to.lower()})"[:200], status="Idea", publish_date=when,
        channel=channel if channel in (opts.get("channel") or []) else "Other",
        format=fmt if fmt in (opts.get("format") or []) else "Post",
        campaign=row["campaign"] or "", client=row["client"] or "", persona=row["persona"] or "",
        copy=row["copy"] or "", cta=row["cta"] or "", hashtags=row["hashtags"] or "",
        notes=f"Repurposed from “{S.rec_label(row, m)}”. {how}"[:300]))
    S.audit("repurpose", f"content_items#{rid} \u2192 #{nid} as {to}")
    flash(f"Made a {to.lower()} from it. {how} \u267b")
    return redirect(url_for("m_edit", key="content_items", rid=nid))


@route("/m/content_items/<int:rid>/shotlist", methods=["POST"])
def content_shotlist(rid):
    """Put the shoot sheet into the post's own notes, so it is there on the day without re-opening Debut."""
    if g.role in ("viewer", "client"):
        abort(403)
    import reels as R
    row = row_or_404("content_items", rid)
    secs = request.form.get("secs", type=int) or 30
    plan = R.shot_list(row["title"], row["copy"] or "", secs)
    text = R.as_text(row["title"], plan)
    notes = (row["notes"] or "").strip()
    ex("UPDATE content_items SET notes=? WHERE id=? AND workspace_id=?",
       ((notes + "\n\n" + text).strip()[:4000], rid, W()))
    S.audit("shotlist", f"content_items#{rid} {plan['seconds']}s")
    flash("Shoot sheet saved into this post's notes. 🎬")
    return redirect(url_for("m_edit", key="content_items", rid=rid))


@route("/ideas/fill", methods=["POST"])
def ideas_fill():
    """Turn a pile of ideas into a planned month in one tap. The Idea Bank was already producing good
    ideas; what was missing was a way to get them onto the calendar without doing it one at a time."""
    if g.role not in ("owner", "admin", "lead", "manager"):
        abort(403)
    ind = IND.get(g.ws["industry"]) or {}
    per_week = request.form.get("per_week", "3")
    gap = FILL_RHYTHM.get(per_week, 2)
    want = max(1, min(request.form.get("n", type=int) or 8, 20))
    m = mod("content_items")
    opts = {x[0]: x[3] for x in m["fields"] if x[2] == "select" and len(x) > 3}
    have = {(r["title"] or "").strip().lower() for r in q("SELECT title FROM content_items WHERE workspace_id=?", (W(),))}
    day = S.today() + dt.timedelta(days=1)
    made = 0
    pool = list(ind.get("ideas") or [])
    try:                                           # then what is actually coming up: festivals, sales, key dates
        import studio as _st
        for s in _st.suggestions(W(), g.ws["industry"], S.today()):
            ch = (s.get("channels") or [{}])[0].get("channel") or "Instagram"
            pool.append(("What's coming up", s.get("title") or "", ch, "Post"))
    except Exception:
        pass
    pool += EVERGREEN_IDEAS                        # last resort, so you always get the number you asked for
    for pillar, title, ch, fmt in pool:
        if made >= want:
            break
        if S.record_count(W()) >= g.plan["records"]:
            flash("You're at your plan's record limit, so I stopped there.")
            break
        if (title or "").strip().lower() in have:                 # never plan the same idea twice
            continue
        while day.weekday() == 6:                                 # keep Sundays free
            day += dt.timedelta(days=1)
        ins("content_items", dict(workspace_id=W(), title=title[:200], status="Planned", publish_date=day.isoformat(),
                                  channel=ch if ch in (opts.get("channel") or []) else "Other",
                                  format=fmt if fmt in (opts.get("format") or []) else "Post",
                                  notes=f"Idea pillar: {pillar}"[:200]))
        have.add((title or "").strip().lower())
        made += 1
        day += dt.timedelta(days=gap)
    S.audit("ideas_fill", f"{made} posts planned")
    flash(f"{made} posts planned, {per_week} a week. Open any one to write the caption. \U0001f4c5" if made
          else "Every idea here is already on your calendar. \U0001f389")
    return redirect(safe_next(url_for("calendar_view")))


@route("/ideas/schedule", methods=["POST"])
def ideas_schedule():
    """One click: turn an Idea Bank idea into a content record that sits on a chosen day of the calendar."""
    f = request.form
    title = (f.get("title") or "").strip()[:200]
    try:
        day = dt.date.fromisoformat(f.get("date", ""))
    except ValueError:
        flash("Pick a date first, then schedule the idea.")
        return redirect(safe_next(url_for("ideas")))
    if not title:
        abort(400)
    if g.role not in ("owner", "admin", "lead", "manager"):      # everyone else suggests; a lead or manager approves it onto the calendar
        import team as _team
        return _team.idea_submit()
    if S.record_count(W()) >= g.plan["records"]:
        flash("You're at your plan's record limit, so I can't add this idea.")
        return redirect(safe_next(url_for("ideas")))
    m = mod("content_items")
    opts = {n: o for n, _l, t, o, *_ in [(x[0], x[1], x[2], x[3] if len(x) > 3 else None) for x in m["fields"]] if t == "select"}
    ch, fm = f.get("channel", ""), f.get("format", "")
    row = dict(workspace_id=W(), title=title, status="Planned", publish_date=day.isoformat(),
               channel=ch if ch in (opts.get("channel") or []) else "Other",
               format=fm if fm in (opts.get("format") or []) else "Post",
               notes=("Idea pillar: " + f["pillar"][:80]) if f.get("pillar") else "")
    nid = ins("content_items", row)
    S.audit("create", f"content_items#{nid} (from idea)")
    flash(f"Scheduled for {day.strftime('%a %d %b')}. 📅")
    return redirect(safe_next(url_for("calendar_view", d=day.isoformat())))


import palettes as _palettes
PALETTES = ("auto", "sunset", "lagoon", "meadow", "candy", "neon", "citrus") + _palettes.KEYS


@route("/pal", methods=["POST"])
def set_palette():
    """Remember the colour palette on the account so it follows the person across devices."""
    k = str((request.get_json(silent=True) or {}).get("pal", ""))
    if k not in PALETTES:
        return jsonify(ok=False), 400
    ex("UPDATE users SET pal=? WHERE id=?", ("" if k == "auto" else k, g.user["id"]))
    return jsonify(ok=True, pal=k)


@route("/account/focus", methods=["POST"])
def set_focus():
    """Profile > Menu: which sections the sidebar shows. Everything stays one search away, nothing is deleted."""
    from hubs import clean_focus
    if request.form.get("all"):
        val = ""
    else:
        val = clean_focus(request.form.getlist("hub"), more=bool(request.form.get("more")))
    ex("UPDATE users SET focus=? WHERE id=?", (val, g.user["id"]))
    flash("Menu saved. Anything you hid is still one search away (Ctrl+K)." if val else "Menu reset: every section is showing.")
    return redirect(url_for("ws.account") + "#menu")


@route("/m/undo", methods=["POST"])
def m_undo():
    u = session.pop("undo", None)
    if not u or u.get("w") != W() or u["key"] not in MODULES:
        flash("Nothing to undo.")
        return redirect(safe_next(url_for("dashboard")))
    key = u["key"]
    if S.record_count(W()) >= g.plan["records"]:
        flash("Can't restore: you're at your plan's record limit.")
        return redirect(safe_next(url_for("m_list", key=key)))
    cols = {x[0] for x in mod(key)["fields"]}
    row = {k: v for k, v in u["row"].items() if k in cols and re.match(r"^[a-z_0-9]+$", k)}
    row["workspace_id"] = W()
    ins(key, row)
    S.audit("restore", key)
    flash("Restored. ↩️")
    return redirect(safe_next(url_for("m_list", key=key)))


@route("/m/<key>/<int:rid>/duplicate", methods=["POST"])
def m_duplicate(key, rid):
    m = mod(key)
    row = row_or_404(key, rid)
    if S.record_count(W()) >= g.plan["records"]:
        flash("You're at your plan's record limit, so I can't make a copy.")
        return redirect(safe_next(url_for("m_list", key=key)))
    data = {n: row[n] for n, *_ in m["fields"] if row[n] is not None}
    first = m["fields"][0][0]
    if data.get(first):
        data[first] = (str(data[first])[:90] + " (copy)")
    data["workspace_id"] = W()
    nid = ins(key, data)
    S.audit("create", f"{key}#{nid} (copy of {rid})")
    flash("Copied. ⧉ Edit the copy below.")
    return redirect(url_for("m_edit", key=key, rid=nid))


def _csv_safe(v):
    v = "" if v is None else str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


@route("/m/<key>/export")
def m_export(key):
    m = mod(key)
    names = [x[0] for x in m["fields"]]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(names)
    for r in q(f"SELECT * FROM {key} WHERE workspace_id=? ORDER BY id", (W(),)):
        w.writerow([_csv_safe(r[n]) for n in names])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={key}.csv"})


@route("/m/<key>/template")
def m_template(key):
    """A blank, header-only CSV so people can see the exact column format before importing."""
    m = mod(key)
    names = [x[0] for x in m["fields"]]
    labels = [x[1] for x in m["fields"]]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(names)
    w.writerow([f"(e.g. {l})" for l in labels])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={key}-template.csv"})


_XLSX_SHEET_BAD_CHARS = re.compile(r"[\\/*\[\]:?]")


def _xlsx_sheet_title(raw, fallback):
    """Excel sheet names can't contain \\ / * [ ] : or ? and can't be blank or over 31 chars — strip/replace
    anything invalid (e.g. module titles like "Personas / ICP") so the workbook always saves successfully."""
    cleaned = _XLSX_SHEET_BAD_CHARS.sub("-", (raw or fallback)).strip()
    return (cleaned or fallback)[:31]


def _mock_value(label, typ, opts):
    """A plausible example value for one field, used to fill in the downloadable Excel mock."""
    if typ == "select" and opts:
        return opts[0]
    if typ == "number":
        return 1000
    if typ == "date":
        return S.today().isoformat()
    if typ == "url":
        return "https://example.com"
    return f"Example {label.lower()}"


@route("/m/<key>/template.xlsx")
def m_template_xlsx(key):
    """A downloadable Excel (.xlsx) mock of this module: real headers plus one filled-in example row, so the
    expected format is obvious before you build your own data and import it back with CSV import."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    m = mod(key)
    wb = Workbook()
    ws = wb.active
    ws.title = _xlsx_sheet_title(m["title"], key)
    names = [x[0] for x in m["fields"]]
    labels = [x[1] for x in m["fields"]]
    ws.append(labels)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="7C5CD6")
    ws.append([_mock_value(l, t, o) for n, l, t, o in m["fields"]])
    for i, l in enumerate(labels, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = max(14, min(32, len(l) + 4))
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     headers={"Content-Disposition": f"attachment; filename={key}-mock-template.xlsx"})


@route("/analytics/import", methods=["POST"])
def analytics_import():
    """Drop in a Meta / Instagram / Google Ads / GA4 export and its numbers land in the Results Log."""
    import datasync
    f = request.files.get("file")
    if not f:
        flash("Choose the report file you downloaded (CSV).")
        return redirect(url_for("analytics"))
    try:
        text = f.read(2_000_000).decode("utf-8-sig")
    except UnicodeDecodeError:
        flash("Could not read that file. In Excel or Sheets use Save as → CSV (UTF-8).")
        return redirect(url_for("analytics"))
    rows, info = datasync.read_export(text, f.filename or "", S.clean_text(request.form.get("channel"), 60), norm_date)
    if info.get("error") or not rows:
        flash(info.get("error") or "No numbers found in that file. Each column needs a name on top and plain numbers underneath.")
        return redirect(url_for("analytics"))
    today = S.today().isoformat()
    room = g.plan["records"] - S.record_count(W())
    added = updated = 0
    for r in rows[:3000]:
        per = r["period"] or today
        have = q("SELECT id FROM kpis WHERE workspace_id=? AND metric=? AND channel=? AND period=?", (W(), r["metric"], r["channel"], per), one=True)
        val = f"{r['value']:.2f}".rstrip("0").rstrip(".")
        if have:
            ex("UPDATE kpis SET value=? WHERE id=?", (val, have["id"]))
            updated += 1
        elif added < room:
            ins("kpis", dict(workspace_id=W(), metric=r["metric"], channel=r["channel"], period=per, value=val, target="", campaign="", notes="From a platform export"))
            added += 1
    S.audit("import", f"kpis x{added}")
    flash(f"Added {added} result(s) for {len(info['columns'])} metric(s) on {info['channel']}"
          + (f" and refreshed {updated} you had already." if updated else ".")
          + (f" Skipped {info['skipped']} row(s) with no readable date (totals or notes)." if info.get("skipped") else "")
          + (" Your plan's record limit was reached." if added >= room and room < len(rows) else ""))
    return redirect(url_for("analytics"))


@route("/m/<key>/import", methods=["POST"])
def m_import(key):
    m = mod(key)
    if "import" not in g.plan["features"]:
        flash("CSV import is available on paid plans.")
        return redirect(url_for("m_list", key=key))
    f = request.files.get("file")
    if not f:
        flash("Choose a CSV file.")
        return redirect(url_for("m_list", key=key))
    try:
        rd = csv.DictReader(io.StringIO(f.read(2_000_000).decode("utf-8-sig")))
    except UnicodeDecodeError:
        flash("Could not read that file. Save it as CSV (UTF-8).")
        return redirect(url_for("m_list", key=key))
    lookup = {}
    for n, label, typ, opts in m["fields"]:
        lookup[n.lower()] = n
        lookup[label.lower()] = n
    room = g.plan["records"] - S.record_count(W())
    added, rep = 0, {}
    for i, raw in enumerate(rd):
        if i >= 2000 or added >= room:
            break
        src = {lookup[k.strip().lower()]: v for k, v in raw.items() if k and k.strip().lower() in lookup and v is not None}
        if not any(src.values()):
            continue
        data = clean_fields(m, src, report=rep)
        data["workspace_id"] = W()
        ins(key, data)
        added += 1
    S.audit("import", f"{key} x{added}")
    flash(f"Imported {added} row(s)." + (" Plan record limit reached." if added >= room else ""))
    if rep.get("dates"):
        flash(f"{len(rep['dates'])} date(s) could not be read and were left empty (e.g. {rep['dates'][0]}). Use 13/11/2026 or 13 Nov 2026.")
    if rep.get("options"):
        flash(f"{len(rep['options'])} value(s) didn't match a dropdown option and were set to its first option (e.g. {rep['options'][0]}). Check them in the list.")
    return redirect(url_for("m_list", key=key))


# ----------------------------------------------------------------- sorting (boards + lists)
def _tb(key):
    """Tie-break among cards nobody has dragged yet: a pre-loaded checklist reads top-to-bottom in phase order,
    everything else shows the newest first."""
    return "id ASC" if key == "launch_checklist" else "id DESC"


def sort_choices(key, m):
    """The sort options a module offers: [(code, label)]. 'manual' is the drag-and-drop order."""
    names = {x[0]: x for x in m["fields"]}
    c = []
    if key in MANUAL_ORDER:
        c.append(("manual", "✋ My order"))
    c += [("new", "🆕 Newest first"), ("old", "📜 Oldest first"), ("az", "🔤 A → Z"), ("za", "🔡 Z → A")]
    if "due_date" in names:
        c.append(("due", "⏰ Due date"))
    if "priority" in names and names["priority"][2] == "select":
        c.append(("priority", "🔥 Priority"))
    dfield = next((x[0] for x in m["fields"] if x[2] == "date" and x[0] != "due_date"), None)
    if dfield:
        c.append(("date", "📅 " + next(x[1] for x in m["fields"] if x[0] == dfield)))
    return c


def order_sql(key, m, sort, direction="asc"):
    """Safe ORDER BY for a sort code. Every column name comes from the module definition, never from the request."""
    fields = {x[0]: x for x in m["fields"]}
    title = m["fields"][0][0]
    blank_last = lambda c: f"CASE WHEN {qi(c)} IS NULL OR {qi(c)}='' THEN 1 ELSE 0 END, "
    if sort.startswith("col:") and sort[4:] in fields:
        c, t = sort[4:], fields[sort[4:]][2]
        d = "DESC" if direction == "desc" else "ASC"
        expr = f"CAST({qi(c)} AS REAL)" if t == "number" else (qi(c) if t == "date" else f"LOWER({qi(c)})")
        return blank_last(c) + f"{expr} {d}, id DESC"
    if sort == "manual" and key in MANUAL_ORDER:
        return f"sort_order ASC, {_tb(key)}"
    if sort == "old":
        return "id ASC"
    if sort == "az":
        return f"LOWER({qi(title)}) ASC, id DESC"
    if sort == "za":
        return f"LOWER({qi(title)}) DESC, id DESC"
    if sort == "due" and "due_date" in fields:
        return blank_last("due_date") + "due_date ASC, id DESC"
    if sort == "priority" and "priority" in fields and fields["priority"][2] == "select":
        opts = fields["priority"][3]
        case = " ".join(f"WHEN {qi('priority')}='{str(o).replace(chr(39), chr(39) * 2)}' THEN {len(opts) - i}" for i, o in enumerate(opts))
        return f"CASE {case} ELSE 99 END ASC, id DESC"
    if sort == "date":
        d = next((x[0] for x in m["fields"] if x[2] == "date" and x[0] != "due_date"), None)
        if d:
            return blank_last(d) + f"{qi(d)} ASC, id DESC"
    return "id DESC"


def board_fields(m):
    """Select fields a board can be grouped by: [(name, label, options)]."""
    return [(x[0], x[1], x[3]) for x in m["fields"] if x[2] == "select" and x[3] and len(x[3]) <= 12]



@route("/kanban/<key>")
def kanban(key):
    m = mod(key)
    base = m.get("kanban") or abort(404)
    groups = board_fields(m)
    by = request.args.get("by", base)
    if by not in [x[0] for x in groups]:
        by = base
    field = by
    opts = next(x for x in m["fields"] if x[0] == field)[3]
    choices = sort_choices(key, m)
    codes = [c for c, _ in choices]
    # default is the hand-made order where the module supports it, else newest first
    sort = request.args.get("sort") or ("manual" if "manual" in codes else "new")
    if sort not in codes:
        sort = "manual" if "manual" in codes else "new"
    _c, _ca = cscope(key)
    rows = q(f"SELECT * FROM {key} WHERE workspace_id=? AND {_c} ORDER BY {order_sql(key, m, sort)} LIMIT 500", [W()] + _ca)
    return render_template("kanban.html", key=key, m=m, field=field, base=base, groups=groups, opts=opts, rows=rows, title_f=m["fields"][0][0],
                           sub_f=m["cols"][1] if len(m["cols"]) > 1 else m["fields"][0][0], sort=sort, choices=choices,
                           can_drag=g.role != "viewer", manual=(sort == "manual"),
                           prio=next((x[3] for x in m["fields"] if x[0] == "priority" and x[2] == "select"), []))


def _group_field(key, m):
    """The select field a board move applies to: ?by= / by= when valid, else the module's own board field."""
    by = request.values.get("by") or m.get("kanban") or ""
    if by not in [x[0] for x in board_fields(m)]:
        by = m.get("kanban") or abort(400)
    return by


@route("/m/<key>/<int:rid>/status", methods=["POST"])
def m_status(key, rid):
    m = mod(key)
    field = _group_field(key, m)
    opts = next(x for x in m["fields"] if x[0] == field)[3]
    v = request.form.get("value", "")
    if v not in opts:
        abort(400)
    row = row_or_404(key, rid)
    if field == "status":
        v = gate_status(key, v, row["status"])
    ex(f"UPDATE {key} SET {qi(field)}=? WHERE id=? AND workspace_id=?", (v, rid, W()))
    S.audit("move", f"{key}#{rid} “{S.rec_label(row, m)}”: {field} {row[field] or 'empty'} → {v}")
    if field == "status":
        changed_hooks(key, rid, m, {"status": v}, row)
        if key == "content_items" and v == "Published" and row["status"] != "Published":
            import voice as _vo
            flash(_vo.tn("win"))
    return redirect(safe_next(url_for("kanban", key=key)))


@route("/plan-week/accept", methods=["POST"])
def plan_week_accept():
    """One tap: the suggested posts for the next 7 days become planned work. `skip` ids are dropped instead."""
    if g.role not in ("owner", "admin", "manager", "lead"):
        abort(403)
    w, t = W(), S.today()
    skip = {int(x) for x in request.form.getlist("skip") if x.isdigit()}
    rows = q("SELECT id FROM content_items WHERE workspace_id=? AND status='Idea' AND publish_date BETWEEN ? AND ?", (w, t.isoformat(), (t + dt.timedelta(days=7)).isoformat()))
    n = 0
    for r in rows:
        if r["id"] in skip:
            ex("DELETE FROM content_items WHERE id=? AND workspace_id=?", (r["id"], w))
        else:
            ex("UPDATE content_items SET status='Planned' WHERE id=? AND workspace_id=?", (r["id"], w)); n += 1
    flash(f"🎉 {n} post{'s' if n != 1 else ''} locked in for this week." if n else "Nothing to accept.")
    return redirect(safe_next(url_for("dashboard")))


@route("/plan-more", methods=["POST"])
def plan_more():
    """One tap when the calendar is running low."""
    if g.role not in ("owner", "admin", "manager", "lead"):
        abort(403)
    n = S.plan_more_posts(W(), g.ws["industry"] or "general")
    flash(f"🎉 {n} new post idea{'s' if n != 1 else ''} added to the next 2 weeks." if n else "Your calendar already has everything this bank of ideas suggests. Try AI Studio for fresh ones.")
    return redirect(url_for("calendar_view"))


@route("/overdue/<what>", methods=["POST"])
def overdue_posts(what):
    """One tap for a calendar that has fallen behind: move late posts to the days ahead, or park them."""
    if g.role not in ("owner", "admin", "manager", "lead"):
        abort(403)
    t = S.today()
    rows = q("SELECT id FROM content_items WHERE workspace_id=? AND publish_date!='' AND publish_date<? AND status NOT IN ('Published','On hold') ORDER BY publish_date", (W(), t.isoformat()))
    if what == "skip":
        for r in rows:
            ex("UPDATE content_items SET status='On hold' WHERE id=? AND workspace_id=?", (r["id"], W()))
        flash(f"Parked {len(rows)} late post{'s' if len(rows) != 1 else ''} as On hold. They are still in the list when you want them.")
    else:
        for i, r in enumerate(rows):      # two a day, starting today
            ex("UPDATE content_items SET publish_date=? WHERE id=? AND workspace_id=?", ((t + dt.timedelta(days=i // 2)).isoformat(), r["id"], W()))
        flash(f"Moved {len(rows)} late post{'s' if len(rows) != 1 else ''} to the next {max(1, (len(rows) + 1) // 2)} days, two a day.")
    return redirect(request.form.get("next") if (request.form.get("next") or "").startswith("/app") else "/app")


@route("/checklist/full", methods=["POST"])
def checklist_full():
    if g.role not in ("owner", "admin", "manager", "lead"):
        abort(403)
    n = S.apply_industry(W(), g.ws["industry"] or "general", full=True)["checklist"]
    flash(f"Added {n} more checklist step{'s' if n != 1 else ''}." if n else "You already have the full checklist.")
    return redirect(url_for("m_list", key="launch_checklist"))


@route("/welcome", methods=["POST"])
def welcome_setup():
    """Three quick questions after sign-up: where do you post, how often, what is the goal. Re-plans the suggested posts around the answers."""
    if g.role not in ("owner", "admin"):
        abort(403)
    w = W()
    chans = [c for c in request.form.getlist("channels") if c in CHANNELS][:4]
    per_week = request.form.get("per_week", "3")
    per_week = int(per_week) if per_week.isdigit() and 1 <= int(per_week) <= 7 else 3
    goal = (request.form.get("goal") or "").strip()[:140]
    if chans or request.form.get("per_week"):
        ex("DELETE FROM content_items WHERE workspace_id=? AND status='Idea' AND notes LIKE 'Suggested by Debut%'", (w,))
        S.seed_suggested_posts(w, g.ws["industry"] or "general", per_week * 2, chans or None)
    if goal:
        eom = (S.today().replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
        ins("tasks", dict(workspace_id=w, title=f"🎯 This month: {goal}", due_date=eom.isoformat(), priority="High", status="To do", assignee=g.user["name"] or ""))
    S.audit("welcome_done", "", wid=w, uid=g.user["id"])
    flash("🎉 Your next 2 weeks are ready. Edit, move or delete anything.")
    return redirect(url_for("calendar_view"))


@route("/m/tasks/<int:rid>/snooze", methods=["POST"])
def task_snooze(rid):
    """Push a task's due date to tomorrow (or one day later than it already is, if that is further out)."""
    row = row_or_404("tasks", rid)
    base = S.today()
    try:
        cur = dt.date.fromisoformat((row["due_date"] or "")[:10])
        if cur > base:
            base = cur
    except ValueError:
        pass
    new = (base + dt.timedelta(days=1)).isoformat()
    ex("UPDATE tasks SET due_date=? WHERE id=? AND workspace_id=?", (new, rid, W()))
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True, due=new)
    return redirect(safe_next(url_for("m_list", key="tasks")))


@route("/m/<key>/<int:rid>/reorder", methods=["POST"])
def m_reorder(key, rid):
    """Drag a board card to a new spot - possibly a new column and/or a new position within it.
    before_id is the card it was dropped in front of, or blank to drop at the end. Answers JSON when called
    from the page's script (so the board never reloads) and redirects for a plain form post."""
    m = mod(key)
    field = _group_field(key, m)
    opts = next(x for x in m["fields"] if x[0] == field)[3]
    status = request.form.get("status", "")
    wants_json = request.headers.get("X-Requested-With") == "fetch"
    if status not in opts:
        abort(400)
    row = row_or_404(key, rid)
    new_val = gate_status(key, status, row["status"]) if field == "status" else status
    if new_val != row[field]:
        ex(f"UPDATE {key} SET {qi(field)}=? WHERE id=? AND workspace_id=?", (new_val, rid, W()))
        if field == "status":
            changed_hooks(key, rid, m, {"status": new_val}, row)
    if key in MANUAL_ORDER:
        before_id = request.form.get("before_id", "").strip()
        siblings = [r["id"] for r in q(f"SELECT id FROM {key} WHERE workspace_id=? AND {qi(field)}=? ORDER BY sort_order ASC, {_tb(key)}", (W(), new_val))]
        old_i = siblings.index(rid) if rid in siblings else None
        if rid in siblings:
            siblings.remove(rid)
        if before_id.isdigit() and int(before_id) in siblings:
            ti = siblings.index(int(before_id))
            # the page tells us which side of the target card it was dropped on (after=1) only when it knows;
            # the old form-post flow assumed "dragging down lands after the target".
            after = request.form.get("after")
            if after in ("0", "1"):
                siblings.insert(ti + 1 if after == "1" else ti, rid)
            else:
                siblings.insert(ti + 1 if old_i is not None and old_i <= ti else ti, rid)
        else:
            siblings.append(rid)
        for i, sid in enumerate(siblings):
            ex(f"UPDATE {key} SET sort_order=? WHERE id=? AND workspace_id=?", (i * 10, sid, W()))
    if wants_json:
        from flask import get_flashed_messages
        return jsonify(ok=True, status=new_val, moved=(new_val == status), msgs=get_flashed_messages())
    return redirect(safe_next(url_for("kanban", key=key)))


@route("/m/<key>/reorder-list", methods=["POST"])
def m_reorder_list(key):
    """Save a hand-made order for the rows on screen (list, cards or checklist). The rows on screen take the
    slots they already occupied, so reordering one page of a long list never disturbs the rest."""
    mod(key)
    if key not in MANUAL_ORDER:
        abort(400)
    ids = [int(x) for x in request.form.get("ids", "").split(",") if x.strip().isdigit()][:500]
    if not ids:
        abort(400)
    allrows = [r["id"] for r in q(f"SELECT id FROM {key} WHERE workspace_id=? ORDER BY sort_order ASC, {_tb(key)}", (W(),))]
    present = [i for i in ids if i in set(allrows)]
    slots = [n for n, i in enumerate(allrows) if i in set(present)]
    for n, i in zip(slots, present):
        allrows[n] = i
    for n, rid in enumerate(allrows):
        ex(f"UPDATE {key} SET sort_order=? WHERE id=? AND workspace_id=?", (n * 10, rid, W()))
    return jsonify(ok=True)


# ----------------------------------------------------------------- search
GLOSSARY = [
    ("GTM (go-to-market)", "Your plan for how a product or offer reaches customers: who it's for, what you say, where you show up and how you'll know it worked.", "Debut: Launch Plans (GTM)"),
    ("ICP / Persona", "A short description of your ideal customer: who they are, what they want and what stops them buying.", "Debut: Ideal Customers"),
    ("UTM link", "A normal link with a few tags added, so your analytics can tell which post or ad a click came from.", "Debut: Trackable Links (UTM)"),
    ("KPI", "A number you watch to know if things are working, for example followers, leads or sales per month.", "Debut: Results Log (KPIs)"),
    ("ROI", "Return on investment: what you got back compared with what you spent.", ""),
    ("ROAS", "Return on ad spend: sales made for every rupee spent on ads.", ""),
    ("CAC", "Customer acquisition cost: what it costs, on average, to win one new customer.", ""),
    ("CTR", "Click-through rate: of the people who saw something, the share who clicked.", ""),
    ("CPC / CPM", "Cost per click / cost per 1,000 views. Two common ways ads are priced.", ""),
    ("Conversion", "When someone does the thing you wanted: signs up, buys, books a call.", ""),
    ("Funnel", "The steps people go through, from first hearing about you to becoming a customer.", "Debut: Analytics"),
    ("SEO", "Search engine optimisation: making your pages easier to find on Google.", "Debut: Search Keywords (SEO)"),
    ("CTA", "Call to action: the line or button that tells people what to do next, such as 'Book now'.", ""),
    ("Battlecard", "A one-page cheat sheet on a competitor: what they offer, where you're stronger and what to say.", "Debut: Competitors"),
    ("Brand kit", "Your logo, colours, fonts and tone of voice, saved once so everything looks like you.", "Debut: Brand Kit"),
    ("Mood board", "A collage of images, colours and notes that captures the look and feel of a launch.", "Debut: Mood Boards"),
    ("UGC", "User-generated content: posts, photos or videos made by customers or creators rather than by you.", ""),
    ("PR", "Public relations: getting press, media and influencers to talk about you.", "Debut: PR & Media"),
    ("Lead", "Someone who has shown interest and could become a customer.", "Debut: Leads"),
    ("Content calendar", "A schedule of what you'll post, where and when.", "Debut: Calendar"),
    ("Market Pulse", "Live news and trends for your industry, so you don't need ten tabs open.", "Debut: Live news (Market Pulse)"),
    ("A/B test", "Trying two versions of one thing to see which does better.", "Debut: Experiments"),
    ("POSM", "Point-of-sale material: in-store displays, shelf strips and posters that help a product sell.", ""),
    ("Rate card", "A price list for your services or for what creators charge.", "Debut: Rate Card"),
]

# Plain-English words people actually type when they are looking for a tool (not the tool's own name).
TOOL_WORDS = {
    "content_items": "post posts reel reels caption blog video instagram schedule publish write", "tasks": "todo to-do task work checklist deadline",
    "reviews": "review google maps rating stars word of mouth qr", "templates": "template playbook plan campaign diwali launch sale starter", "publishing": "instagram post publish auto schedule insta facebook", "campaigns": "campaign ads ad budget promote", "leads": "lead customers enquiries inquiry sales prospects crm", "kpis": "results numbers metrics performance kpi stats",
    "gtm_plans": "launch plan strategy gtm go to market", "personas": "audience customer icp persona who buys", "competitors": "rivals competition competitor battlecard",
    "brand_kit": "logo colours colors fonts voice brand tone", "launch_checklist": "launch checklist steps", "influencers": "influencer creator collab outreach dm",
    "payments": "invoice invoices payout pay money payment", "utm_links": "utm tracking link links track clicks", "keywords": "seo keyword search google rank",
    "key_dates": "festival dates sale date holiday", "events": "event events offline", "promotions": "promotion offer discount sale",
    "pr_contacts": "pr press media journalist", "creators": "creator freelancer writer designer", "clients": "client clients customer account", 
    "assets": "files library images assets media inspiration references links save", "experiments": "test ab a/b experiment", "feeds": "news rss sources", "watchlist": "watch topics news trends",
}
TOOL_PAGES = [("calendar_view", "📅 Calendar", "calendar schedule month plan dates"), ("moodboards", "🖼️ Mood Boards", "mood board vibe inspiration pinterest"), ("ideas", "💡 Idea Bank", "ideas inspiration stuck content ideas"),
              ("ai_studio", "🤖 AI Studio", "ai write draft generate caption chatgpt"), ("pulse_page", "📡 Live news & trends", "news trends market pulse competitors"), ("analytics", "📈 Analytics", "analytics charts results funnel"),
              ("analytics", "🩺 Marketing Health (on Numbers)", "health score check consistency gaps"), ("report", "📑 Client report", "report pdf client monthly"), ("whatnow", "🫠 Idk what to do", "stuck lost help next what now bored"),
              ("glossary", "📖 Jargon buster", "meaning what is glossary jargon terms explain gtm utm kpi icp roi"), ("help_centre", "❓ Help & guides", "help guide manual how to")]


def find_tools(term):
    """'Where is X?' - match a typed word against every tool's name, plain-English keywords and short hint."""
    t = (term or "").strip().lower()
    if len(t) < 2:
        return []
    out = []
    for key, m in MODULES.items():
        if locked(key) or (g.role == "creator" and key not in CREATOR_MODULES):
            continue
        hay = f"{m['title']} {TOOL_WORDS.get(key, '')}".lower()
        if t in hay:
            out.append((f"{m['icon']} {m['title']}", url_for("m_list", key=key)))
    if g.role != "creator" or True:
        for ep, label, words in TOOL_PAGES:
            if g.role == "creator" and ep not in ("calendar_view", "moodboards", "ideas", "whatnow", "glossary", "help_centre"):
                continue
            if g.role == "client":
                continue
            if t in f"{label} {words}".lower():
                out.append((label, url_for(ep)))
    return out[:8]



@route("/search")
def search():
    term, results = request.args.get("q", "").strip(), []
    if len(term) >= 2:
        for key, m in MODULES.items():
            if locked(key) or (g.role == "creator" and key not in CREATOR_MODULES):
                continue
            fields = [f[0] for f in m["fields"] if f[2] in ("text", "textarea", "url")][:6]
            where = " OR ".join(f"LOWER({qi(f)}) LIKE ?" for f in fields)
            _c, _ca = cscope(key)
            rows = q(f"SELECT * FROM {key} WHERE workspace_id=? AND {_c} AND ({where}) ORDER BY id DESC LIMIT 5", [W()] + _ca + [f"%{term.lower()}%"] * len(fields))
            if rows:
                results.append((key, m, rows, m["fields"][0][0]))
    return render_template("search.html", term=term, results=results, tools=find_tools(term), has_key=bool(C.ANTHROPIC_API_KEY))


# ----------------------------------------------------------------- calendar
@route("/calendar/print")
def calendar_print():
    """One page you can stick near the till. Plenty of small businesses still work off paper, and a
    plan on the wall is seen by everyone in the shop, not just whoever has the app."""
    w, today = W(), S.today()
    try:
        y = int(request.args.get("y") or today.year)
        mth = int(request.args.get("m") or today.month)
        first = dt.date(y, mth, 1)
    except (ValueError, OverflowError):
        abort(400)
    last = (first + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
    _c, _ca = cscope("content_items")
    rows = q(f"""SELECT * FROM content_items WHERE workspace_id=? AND {_c} AND publish_date BETWEEN ? AND ?
                 ORDER BY publish_date, id""", [w, *_ca, first.isoformat(), last.isoformat()])
    days = {}
    for r in rows:
        days.setdefault(r["publish_date"], []).append(r)
    dates = [first + dt.timedelta(days=i) for i in range((last - first).days + 1)]
    kd = {}
    for r in q("SELECT * FROM key_dates WHERE workspace_id=? AND date BETWEEN ? AND ?",
               (w, first.isoformat(), last.isoformat())):
        kd.setdefault(r["date"], []).append(r["name"])
    tasks = q("""SELECT * FROM tasks WHERE workspace_id=? AND due_date BETWEEN ? AND ? AND status<>'Done'
                 ORDER BY due_date""", (w, first.isoformat(), last.isoformat()))
    return render_template("calendar_print.html", dates=dates, days=days, kd=kd, tasks=tasks,
                           month=first.strftime("%B %Y"), y=y, m=mth, n=len(rows), bare=True)


@route("/calendar")
def calendar_view():
    w, today = W(), S.today()
    if g.role not in ("viewer", "client"):
        S.dedupe_key_dates(w)
    sel = today
    try:
        if request.args.get("d"):
            sel = dt.date.fromisoformat(request.args["d"])
        y = int(request.args.get("y", sel.year if request.args.get("d") else today.year))
        mth = int(request.args.get("m", sel.month if request.args.get("d") else today.month))
        weeks = pycal.Calendar(0).monthdatescalendar(y, mth)
    except (ValueError, OverflowError, pycal.IllegalMonthError):
        abort(400)
    ch = request.args.get("channel", "")
    start, end = weeks[0][0].isoformat(), weeks[-1][-1].isoformat()
    _c, _ca = cscope("content_items")
    sql, args = f"SELECT * FROM content_items WHERE workspace_id=? AND {_c} AND publish_date BETWEEN ? AND ?", [w, *_ca, start, end]
    if ch:
        sql += " AND channel=?"
        args.append(ch)
    by = {}
    for r in q(sql + " ORDER BY id", args):
        by.setdefault(r["publish_date"], []).append(r)
    kd = {}
    for r in q("SELECT * FROM key_dates WHERE workspace_id=? AND date BETWEEN ? AND ?", (w, start, end)):
        kd.setdefault(r["date"], []).append(r["name"])
    for r in q("SELECT * FROM promotions WHERE workspace_id=? AND (start_date BETWEEN ? AND ? OR end_date BETWEEN ? AND ?)", (w, start, end, start, end)):
        if start <= (r["start_date"] or "") <= end:
            kd.setdefault(r["start_date"], []).append("🏷 " + r["name"] + " starts")
        if start <= (r["end_date"] or "") <= end:
            kd.setdefault(r["end_date"], []).append("🏁 " + r["name"] + " ends")
    for r in q("SELECT * FROM events WHERE workspace_id=? AND date BETWEEN ? AND ?", (w, start, end)):
        kd.setdefault(r["date"], []).append("🎪 " + r["name"] + " (" + r["mode"] + ")")
    for _d, _names in kd.items():       # "Children's Day" and "Children's Day (India)" on one date are one thing
        _seen, _keep = [], []
        for _n in _names:
            _base = re.sub(r"\s*\(.*?\)", "", _n).strip().lower()
            if _base not in _seen:
                _seen.append(_base)
                _keep.append(_n)
        kd[_d] = _keep
    py, pm = (y, mth - 1) if mth > 1 else (y - 1, 12)
    ny, nm = (y, mth + 1) if mth < 12 else (y + 1, 1)
    unscheduled = q(f"SELECT * FROM content_items WHERE workspace_id=? AND {_c} AND (publish_date='' OR publish_date IS NULL) ORDER BY id DESC LIMIT 50", [w] + _ca)
    key_ = g.ws["ics_key"] or secrets.token_hex(6)
    if not g.ws["ics_key"]:
        ex("UPDATE workspaces SET ics_key=? WHERE id=?", (key_, w))
    ics = S.app_url() + url_for("ics_feed", token=URLSafeSerializer(C.SECRET_KEY, salt="ics").dumps([w, key_]))
    return render_template("calendar.html", weeks=weeks, by=by, kd=kd, y=y, mth=mth, month_name=pycal.month_name[mth], ch=ch, channels=CHANNELS,
                           py=py, pm=pm, ny=ny, nm=nm, unscheduled=unscheduled, ics=ics, sel=sel.isoformat(), open_day=request.args.get("open") == "1",
                           ideas=(IND.get(g.ws["industry"]) or {}).get("ideas", []),
                           years=list(range(max(1970, y - 6), min(2100, y + 7))), months=[(i, pycal.month_name[i]) for i in range(1, 13)])


@route("/calendar/<token>.ics")
def ics_feed(token):
    try:
        w, key_ = URLSafeSerializer(C.SECRET_KEY, salt="ics").loads(token)
    except (BadSignature, ValueError, TypeError):
        abort(404)
    if not q("SELECT 1 FROM workspaces WHERE id=? AND ics_key=? AND ics_key!=''", (S.to_int(w) or 0, str(key_)), one=True):
        abort(404)
    esc = lambda s: (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{C.APP_NAME}//EN", "CALSCALE:GREGORIAN"]
    for r in q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date!='' ORDER BY publish_date LIMIT 2000", (w,)):
        try:
            d = dt.date.fromisoformat(r["publish_date"])
        except ValueError:
            continue
        lines += ["BEGIN:VEVENT", f"UID:content-{r['id']}@{C.APP_NAME.replace(' ', '').lower()}", f"DTSTAMP:{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}",
                  f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + dt.timedelta(days=1):%Y%m%d}",
                  f"SUMMARY:{esc((r['channel'] or '') + ' - ' + (r['title'] or ''))}", f"DESCRIPTION:{esc((r['status'] or '') + ' | ' + (r['copy'] or '')[:300])}", "END:VEVENT"]
    for r in q("SELECT * FROM tasks WHERE workspace_id=? AND due_date!='' AND status NOT IN ('Done','Cancelled') ORDER BY due_date LIMIT 1000", (w,)):      # deadlines that still need someone
        try:
            d = dt.date.fromisoformat(r["due_date"])
        except ValueError:
            continue
        lines += ["BEGIN:VEVENT", f"UID:task-{r['id']}@{C.APP_NAME.replace(' ', '').lower()}", f"DTSTAMP:{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}",
                  f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + dt.timedelta(days=1):%Y%m%d}",
                  f"SUMMARY:{esc('Task - ' + (r['title'] or ''))}", f"DESCRIPTION:{esc((r['assignee'] or '') + ' | ' + (r['status'] or ''))}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return Response("\r\n".join(lines), mimetype="text/calendar")


@route("/calendar/reset-link", methods=["POST"])
@S.roles("owner", "admin", "lead", "manager")
def ics_reset():
    ex("UPDATE workspaces SET ics_key=? WHERE id=?", (secrets.token_hex(6), W()))
    S.audit("ics_link_reset")
    flash("Calendar link reset. Anyone using the old link is now cut off; re-subscribe with the new one.")
    return redirect(url_for("calendar_view"))


@route("/api/reschedule", methods=["POST"])
def api_reschedule():
    d = S.jbody()
    try:
        date = dt.date.fromisoformat(str(d.get("date", ""))).isoformat()
    except ValueError:
        return jsonify(error="bad date"), 400
    rid = S.to_int(d.get("id")) or abort(400)
    row = row_or_404("content_items", rid)
    ex("UPDATE content_items SET publish_date=? WHERE id=? AND workspace_id=?", (date, rid, W()))
    S.audit("move", f"content_items#{rid} “{S.rec_label(row)}”: publish date {row['publish_date'] or 'empty'} → {date}")
    return jsonify(ok=True)


# ----------------------------------------------------------------- mood boards
def board_or_404(bid):
    return q("SELECT * FROM boards WHERE id=? AND workspace_id=?", (bid, W()), one=True) or abort(404)


@route("/moodboards")
def moodboards():
    boards = q("SELECT b.*, (SELECT COUNT(*) FROM board_items i WHERE i.board_id=b.id) AS n FROM boards b WHERE b.workspace_id=? ORDER BY b.id DESC", (W(),))
    covers = {b["id"]: q("SELECT * FROM board_items WHERE board_id=? AND workspace_id=? AND kind='image' AND content NOT LIKE 'data:image/svg%' LIMIT 1", (b["id"], W()), one=True) for b in boards}
    return render_template("moodboards.html", boards=boards, covers=covers, lib=BL.B, cats=BL.CATS)


@route("/moodboards/new", methods=["POST"])
def board_new():
    if q("SELECT COUNT(*) c FROM boards WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["boards"]:
        flash(f"The {g.plan['name']} plan includes {g.plan['boards']} mood boards. Upgrade for more.")
        return redirect(url_for("moodboards"))
    bid = ins("boards", dict(workspace_id=W(), name=S.clean_text(request.form.get("name"), 120) or "Untitled board", description=S.clean_text(request.form.get("description"), 300)))
    S.audit("create", f"board#{bid}")
    return redirect(url_for("board_view", bid=bid))


def _svg_placeholder(label, bg="#6a3df0", fg="#ffffff"):
    """A self-contained placeholder picture (no external image host involved) so the sample board always
    renders, even offline — a real upload or image URL replaces it in seconds via the 🔄 button."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
           f'<rect width="100%" height="100%" fill="{bg}"/>'
           f'<text x="50%" y="46%" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="{fg}" text-anchor="middle">{label}</text>'
           f'<text x="50%" y="58%" font-family="Arial, sans-serif" font-size="14" fill="{fg}" text-anchor="middle" opacity=".85">tap 🔄 on the card to replace it</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


SAMPLE_BOARD_ITEMS = [
    ("image", _svg_placeholder("Reference shot"), "Reference shot — swap for your own"),
    ("color", "#6a3df0", "Primary brand colour"), ("color", "#f1ecff", "Light background tint"),
    ("note", "Mood: warm, festive, a little playful. Think golden-hour light, not studio-flat.", "Overall mood"),
    ("note", "Hero shot idea: product on a textured surface, soft natural light, one prop max.", "Hero shot"),
    ("link", "https://www.pinterest.com/search/pins/?q=festive%20product%20photography", "Inspiration search"),
    ("note", "Caption tone: short, warm, one emoji max. Avoid hard-sell language.", "Caption style"),
    ("image", _svg_placeholder("Palette / texture", bg="#2b2442"), "Palette / texture reference"),
]


@route("/moodboards/sample", methods=["POST"])
def board_sample():
    """A ready-made example board so a first-time user sees the format before building their own."""
    if q("SELECT COUNT(*) c FROM boards WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["boards"]:
        flash(f"The {g.plan['name']} plan includes {g.plan['boards']} mood boards. Upgrade for more.")
        return redirect(url_for("moodboards"))
    bid = ins("boards", dict(workspace_id=W(), name="Sample board (edit or delete me)", description="A worked example — drag things around, then make your own."))
    for kind, content, caption in SAMPLE_BOARD_ITEMS:
        ins("board_items", dict(workspace_id=W(), board_id=bid, kind=kind, content=content, caption=caption, **_next_slot(bid)))
    S.audit("create", f"board#{bid} (sample)")
    return redirect(url_for("board_view", bid=bid))


import boards_lib as BL
BL.LIB["launch"] = BL.LIB["product"]


@route("/moodboards/template/<tkey>", methods=["POST"])
def board_from_template(tkey):
    row = BL.LIB.get(tkey) or abort(404)
    if q("SELECT COUNT(*) c FROM boards WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["boards"]:
        flash(f"The {g.plan['name']} plan includes {g.plan['boards']} mood boards. Upgrade for more.")
        return redirect(url_for("moodboards"))
    name, desc, items = BL.build(row)
    bid = ins("boards", dict(workspace_id=W(), name=name, description=desc[:300]))
    for kind, content, caption in items:
        ins("board_items", dict(workspace_id=W(), board_id=bid, kind=kind, content=content, caption=caption, **_next_slot(bid)))
    S.audit("create", f"board#{bid} (template {tkey})")
    return redirect(url_for("board_view", bid=bid))


@route("/moodboards/request", methods=["POST"])
def board_request():
    msg = S.clean_text(request.form.get("what"), 300)
    if msg:
        ins("feedback", dict(workspace_id=W(), user_id=g.user["id"], kind="board_request", page="/moodboards", message="Mood board wanted: " + msg))
        flash("Noted! We are building more boards, and yours is on the list.")
    return redirect(url_for("moodboards"))


@route("/moodboards/<int:bid>/rename", methods=["POST"])
def board_rename(bid):
    board_or_404(bid)
    name = S.clean_text(request.form.get("name"), 120)
    if name:
        ex("UPDATE boards SET name=?, description=? WHERE id=? AND workspace_id=?", (name, S.clean_text(request.form.get("description"), 300), bid, W()))
        flash("Board updated.")
    return redirect(url_for("board_view", bid=bid))


@route("/moodboards/<int:bid>/duplicate", methods=["POST"])
def board_duplicate(bid):
    b = board_or_404(bid)
    if q("SELECT COUNT(*) c FROM boards WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["boards"]:
        flash(f"The {g.plan['name']} plan includes {g.plan['boards']} mood boards. Upgrade for more.")
        return redirect(url_for("board_view", bid=bid))
    nid = ins("boards", dict(workspace_id=W(), name=(b["name"] or "Board")[:110] + " (copy)", description=b["description"] or ""))
    for it in q("SELECT * FROM board_items WHERE board_id=? AND workspace_id=? ORDER BY z, id", (bid, W())):
        d = {k: it[k] for k in ("kind", "content", "caption", "x", "y", "w", "h", "z")}
        if it["kind"] == "image" and not str(it["content"]).startswith(("http", "data:")):
            d["content"] = it["content"]          # uploaded files are shared by reference; deleting one board's copy is guarded below
        ins("board_items", dict(workspace_id=W(), board_id=nid, **d))
    S.audit("create", f"board#{nid} (copy of {bid})")
    flash("Board duplicated.")
    return redirect(url_for("board_view", bid=nid))


@route("/moodboards/<int:bid>/save-colours", methods=["POST"])
def board_save_colours(bid):
    board_or_404(bid)
    have = {(r["value"] or "").lower() for r in q("SELECT value FROM brand_kit WHERE workspace_id=? AND kind='Colour'", (W(),))}
    n = 0
    for it in q("SELECT * FROM board_items WHERE board_id=? AND workspace_id=? AND kind='color' ORDER BY id", (bid, W())):
        if it["content"].lower() not in have:
            ins("brand_kit", dict(workspace_id=W(), name=it["caption"] or "Board colour", kind="Colour", value=it["content"], notes="From a mood board"))
            have.add(it["content"].lower())
            n += 1
    flash(f"Saved {n} new colour(s) to your Brand Kit." if n else "Those colours are already in your Brand Kit (or this board has none).")
    return redirect(url_for("board_view", bid=bid))


@route("/moodboards/<int:bid>/share", methods=["POST"])
def board_share(bid):
    board_or_404(bid)
    act = request.form.get("do", "on")
    if act == "off":
        ex("UPDATE boards SET share_token='' WHERE id=? AND workspace_id=?", (bid, W()))
        S.audit("board_share_off", f"board#{bid}")
        flash("Public link turned off — anyone who had it can no longer open the board.")
    else:                                   # "on" and "reset" both mint a fresh unguessable token (reset invalidates the old link)
        ex("UPDATE boards SET share_token=? WHERE id=? AND workspace_id=?", (secrets.token_urlsafe(18), bid, W()))
        S.audit("board_share_on" if act == "on" else "board_share_reset", f"board#{bid}")
        flash("Public link ready — copy it below." if act == "on" else "New public link created; the old one no longer works.")
    return redirect(url_for("board_view", bid=bid, share=1))


def _public_board(token):
    if not token or len(token) < 16:
        abort(404)
    return q("SELECT * FROM boards WHERE share_token=? AND share_token!=''", (token,), one=True) or abort(404)


@route("/b/<token>")
def board_public(token):
    b = _public_board(token)
    items = q("SELECT * FROM board_items WHERE board_id=? AND workspace_id=? ORDER BY z, id", (b["id"], b["workspace_id"]))
    ws = q("SELECT name, logo_url FROM workspaces WHERE id=?", (b["workspace_id"],), one=True)
    r = make_response(render_template("moodboard_public.html", b=b, items=items, ws=ws, token=token, hide_chrome=True, bare=True))
    r.headers["X-Robots-Tag"] = "noindex, nofollow"
    r.headers["Referrer-Policy"] = "no-referrer"
    return r


@route("/b/<token>/img/<int:iid>")
def board_public_img(token, iid):
    b = _public_board(token)
    it = q("SELECT * FROM board_items WHERE id=? AND board_id=? AND kind='image'", (iid, b["id"]), one=True) or abort(404)
    c = it["content"] or ""
    if c.startswith("/media/"):
        _, _, wid, name = c.split("/", 3)
        return send_from_directory(os.path.join(C.UPLOAD_DIR, str(b["workspace_id"])), os.path.basename(name))
    return redirect(S.media_url(c))


@route("/moodboards/<int:bid>")
def board_view(bid):
    b = board_or_404(bid)
    unplaced = q("SELECT id FROM board_items WHERE board_id=? AND workspace_id=? AND x<0 ORDER BY id", (bid, W()))
    if unplaced:  # boards created before drag-and-drop existed: give their items a tidy starting position, once
        base = q("SELECT COUNT(*) c FROM board_items WHERE board_id=? AND x>=0", (bid,), one=True)["c"]
        topz = q("SELECT COALESCE(MAX(z),0) z FROM board_items WHERE board_id=?", (bid,), one=True)["z"]
        for i, r in enumerate(unplaced):
            col, row = (base + i) % ITEM_COLS, (base + i) // ITEM_COLS
            ex("UPDATE board_items SET x=?, y=?, w=?, h=?, z=? WHERE id=?",
               (ITEM_GAP + col * (ITEM_W + ITEM_GAP), ITEM_GAP + row * (ITEM_H + ITEM_GAP), ITEM_W, ITEM_H, topz + i + 1, r["id"]))
    return render_template("moodboard.html", b=b, items=q("SELECT * FROM board_items WHERE board_id=? AND workspace_id=? ORDER BY z, id", (bid, W())))


ITEM_W, ITEM_H, ITEM_GAP, ITEM_COLS = 240, 170, 24, 4


def _next_slot(bid):
    """Where a freshly added item lands on the canvas: a tidy cascading grid, so a beginner never has to place the first item themselves."""
    n = q("SELECT COUNT(*) c FROM board_items WHERE board_id=?", (bid,), one=True)["c"]
    col, row = n % ITEM_COLS, n // ITEM_COLS
    top = q("SELECT COALESCE(MAX(z),0) z FROM board_items WHERE board_id=?", (bid,), one=True)["z"]
    return dict(x=ITEM_GAP + col * (ITEM_W + ITEM_GAP), y=ITEM_GAP + row * (ITEM_H + ITEM_GAP), w=ITEM_W, h=ITEM_H, z=top + 1)


@route("/moodboards/<int:bid>/add", methods=["POST"])
def board_add(bid):
    board_or_404(bid)
    kind, cap = request.form.get("kind"), S.clean_text(request.form.get("caption"), 200)
    if q("SELECT COUNT(*) c FROM board_items WHERE board_id=? AND workspace_id=?", (bid, W()), one=True)["c"] >= 300:
        flash("Board is full (300 items).")
        return redirect(url_for("board_view", bid=bid))
    if kind == "upload":
        n = 0
        for f in request.files.getlist("file")[:20]:
            data = f.read(10 * 1024 * 1024 + 1)
            ext = S.sniff_image(data) if data and len(data) <= 10 * 1024 * 1024 else None
            if ext:
                ins("board_items", dict(workspace_id=W(), board_id=bid, kind="image", content=S.store_file(W(), ext, data), caption=cap, **_next_slot(bid)))
                n += 1
        flash(f"Added {n} image(s)." if n else "No valid image (PNG, JPG, GIF or WebP up to 10 MB).")
    else:
        content = S.clean_text(request.form.get("content"), 2000)
        if kind in ("image", "link"):
            content = S.clean_url(content)
        elif kind == "color":
            content = content if re.match(r"^#[0-9a-fA-F]{6}$", content) else ""
        elif kind == "note":
            content = content[:2000]
        else:
            abort(400)
        if content:
            ins("board_items", dict(workspace_id=W(), board_id=bid, kind=kind, content=content, caption=cap, **_next_slot(bid)))
        else:
            flash("That value isn't valid.")
    return redirect(url_for("board_view", bid=bid))


@route("/moodboards/item/<int:iid>/place", methods=["POST"])
def board_item_place(iid):
    """Drag/resize/bring-to-front, saved instantly from the canvas (no page reload)."""
    it = q("SELECT id FROM board_items WHERE id=? AND workspace_id=?", (iid, W()), one=True) or abort(404)
    d = S.jbody()
    try:
        x, y = max(0, min(20000, int(d.get("x")))), max(0, min(20000, int(d.get("y"))))
        w, h = max(80, min(1000, int(d.get("w")))), max(60, min(1000, int(d.get("h"))))
        z = max(0, min(100000, int(d.get("z"))))
    except (TypeError, ValueError):
        abort(400)
    ex("UPDATE board_items SET x=?, y=?, w=?, h=?, z=? WHERE id=? AND workspace_id=?", (x, y, w, h, z, iid, W()))
    return jsonify(ok=True)


@route("/moodboards/item/<int:iid>/edit", methods=["POST"])
def board_item_edit(iid):
    """Edit a note/colour/link card's text in place on the canvas (no page reload) — images keep their file but can get a new caption."""
    it = q("SELECT * FROM board_items WHERE id=? AND workspace_id=?", (iid, W()), one=True) or abort(404)
    d = S.jbody()
    caption = S.clean_text(d.get("caption", ""), 200)
    if it["kind"] == "note":
        content = S.clean_text(d.get("content", ""), 2000)
        if not content:
            return jsonify(error="Note can't be empty."), 400
        ex("UPDATE board_items SET content=?, caption=? WHERE id=?", (content, caption, iid))
    elif it["kind"] == "color":
        content = d.get("content", "")
        if not re.match(r"^#[0-9a-fA-F]{6}$", content or ""):
            return jsonify(error="Enter a valid hex colour, e.g. #6a3df0."), 400
        ex("UPDATE board_items SET content=?, caption=? WHERE id=?", (content, caption, iid))
    elif it["kind"] == "link":
        content = S.clean_url(d.get("content", ""))
        if not content:
            return jsonify(error="Enter a valid http(s) link."), 400
        ex("UPDATE board_items SET content=?, caption=? WHERE id=?", (content, caption, iid))
    else:  # image: caption always changes here; the picture can be swapped either by pasting a new URL or by uploading a file (board_item_replace_image below)
        new_url = S.clean_url(d.get("content", ""))
        if new_url:
            old_content = it["content"]
            ex("UPDATE board_items SET content=?, caption=? WHERE id=?", (new_url, caption, iid))
            _drop_file(old_content, (iid,))
        else:
            ex("UPDATE board_items SET caption=? WHERE id=?", (caption, iid))
    return jsonify(ok=True)


@route("/moodboards/<int:bid>/photos")
def board_photos(bid):
    """Search real photos for this board (JSON). Providers: Pexels / Unsplash with a key, otherwise Openverse."""
    board_or_404(bid)
    import photos
    term = S.clean_text(request.args.get("q", ""), 80)
    if not term:
        return jsonify(results=[], provider=photos.provider())
    try:
        res = photos.search(term)
    except Exception:
        return jsonify(error="The photo library didn't answer. Try again in a moment, or upload your own.", results=[]), 502
    return jsonify(results=res, provider=photos.provider())


@route("/moodboards/<int:bid>/photos/add", methods=["POST"])
def board_photo_add(bid):
    """Copy one chosen photo onto the board (downloaded once and stored with the board, with its credit as the caption)."""
    board_or_404(bid)
    d = S.jbody()
    url, credit = str(d.get("url") or ""), S.clean_text(d.get("credit") or "", 200)
    if not url.startswith("https://"):
        abort(400)
    if q("SELECT COUNT(*) c FROM board_items WHERE board_id=? AND workspace_id=?", (bid, W()), one=True)["c"] >= 300:
        return jsonify(error="Board is full (300 items)."), 400
    try:
        data = S.safe_get(url, timeout=12, limit=10 * 1024 * 1024)
    except Exception:
        return jsonify(error="Couldn't download that photo. Try another."), 502
    ext = S.sniff_image(data) if data and len(data) <= 10 * 1024 * 1024 else None
    if not ext:
        return jsonify(error="That file isn't a usable photo."), 400
    iid = ins("board_items", dict(workspace_id=W(), board_id=bid, kind="image", content=S.store_file(W(), ext, data), caption=credit, **_next_slot(bid)))
    return jsonify(ok=True, id=iid)


@route("/moodboards/item/<int:iid>/replace-image", methods=["POST"])
def board_item_replace_image(iid):
    """Swap the picture on an existing image card in place — position, size and z-order stay put, so a card never has to be deleted and re-added just to change the photo."""
    it = q("SELECT * FROM board_items WHERE id=? AND workspace_id=? AND kind='image'", (iid, W()), one=True) or abort(404)
    f = request.files.get("file")
    data = f.read(10 * 1024 * 1024 + 1) if f else b""
    ext = S.sniff_image(data) if data and len(data) <= 10 * 1024 * 1024 else None
    if not ext:
        return jsonify(error="Choose a PNG, JPG, GIF or WebP image up to 10 MB."), 400
    new_content = S.store_file(W(), ext, data)
    old_content = it["content"]
    ex("UPDATE board_items SET content=? WHERE id=?", (new_content, iid))
    _drop_file(old_content, (iid,))
    return jsonify(ok=True, url=S.media_url(new_content))


@route("/moodboards/<int:bid>/arrange", methods=["POST"])
def board_arrange(bid):
    """One-click tidy-up: snap every item on this board back into a neat grid."""
    board_or_404(bid)
    rows = q("SELECT id FROM board_items WHERE board_id=? AND workspace_id=? ORDER BY z, id", (bid, W()))
    for i, r in enumerate(rows):
        col, row = i % ITEM_COLS, i // ITEM_COLS
        ex("UPDATE board_items SET x=?, y=?, w=?, h=?, z=? WHERE id=?",
           (ITEM_GAP + col * (ITEM_W + ITEM_GAP), ITEM_GAP + row * (ITEM_H + ITEM_GAP), ITEM_W, ITEM_H, i + 1, r["id"]))
    flash("Tidied up.")
    return redirect(url_for("board_view", bid=bid))


def _drop_file(content, exclude_ids=()):
    """Delete an uploaded file only if no other board card still uses it (duplicated boards share files)."""
    if not content or content.startswith(("http", "data:")):
        return
    rows = q("SELECT id FROM board_items WHERE content=? AND workspace_id=?", (content, W()))
    if any(r["id"] not in exclude_ids for r in rows):
        return
    S.delete_file(content)


@route("/moodboards/item/<int:iid>/delete", methods=["POST"])
def board_item_delete(iid):
    it = q("SELECT * FROM board_items WHERE id=? AND workspace_id=?", (iid, W()), one=True) or abort(404)
    if it["kind"] == "image":
        _drop_file(it["content"], (iid,))
    ex("DELETE FROM board_items WHERE id=? AND workspace_id=?", (iid, W()))
    return redirect(url_for("board_view", bid=it["board_id"]))


@route("/moodboards/<int:bid>/delete", methods=["POST"])
def board_delete(bid):
    board_or_404(bid)
    mine = q("SELECT * FROM board_items WHERE board_id=? AND workspace_id=? AND kind='image'", (bid, W()))
    ids = tuple(r["id"] for r in q("SELECT id FROM board_items WHERE board_id=? AND workspace_id=?", (bid, W())))
    for it in mine:
        _drop_file(it["content"], ids)
    ex("DELETE FROM board_items WHERE board_id=? AND workspace_id=?", (bid, W()))
    ex("DELETE FROM boards WHERE id=? AND workspace_id=?", (bid, W()))
    S.audit("delete", f"board#{bid}")
    return redirect(url_for("moodboards"))


@route("/media/<int:wid>/<name>")
def media(wid, name):
    if wid != W():
        abort(404)
    return send_from_directory(os.path.join(C.UPLOAD_DIR, str(wid)), os.path.basename(name))


# ----------------------------------------------------------------- latest updates (RSS/Atom)
@route("/updates/save", methods=["POST"])
def updates_save():
    url = S.clean_url(request.form.get("url", ""))
    if url:
        ins("assets", dict(workspace_id=W(), title=S.clean_text(request.form.get("title"), 200), url=url, type="Article", tags=S.clean_text(request.form.get("source"), 100), body="Saved from Live news", favorite="No", status="Approved"))
        flash("Saved to your Library.")
    return redirect(url_for("pulse_page"))


# ----------------------------------------------------------------- kudos and reactions
REACTIONS = ("👏", "🔥", "❤️", "🎉", "👀")
KUDOS_EMOJI = ("👏", "🔥", "🌟", "🎉", "💪", "🙌")


def reactions_for(key, rid):
    """[(emoji, count, mine)] for one record, in a fixed order."""
    rows = q("SELECT emoji, user_id FROM reactions WHERE workspace_id=? AND module=? AND record_id=?", (W(), key, rid))
    out = []
    for e in REACTIONS:
        mine = any(r["user_id"] == g.user["id"] and r["emoji"] == e for r in rows)
        n = sum(1 for r in rows if r["emoji"] == e)
        out.append((e, n, mine))
    return out


@route("/m/<key>/<int:rid>/presence", methods=["POST"])
def presence(key, rid):
    """Heartbeat from an open record page; returns teammates who pinged in the last 40 seconds."""
    import time as _t
    mod(key)
    row_or_404(key, rid)
    now = int(_t.time())
    ex("DELETE FROM presence WHERE workspace_id=? AND module=? AND record_id=? AND user_id=?", (W(), key, rid, g.user["id"]))
    ex("INSERT INTO presence (workspace_id, module, record_id, user_id, seen_at) VALUES (?,?,?,?,?)", (W(), key, rid, g.user["id"], now))
    rows = q("SELECT u.name, u.email FROM presence p JOIN users u ON u.id=p.user_id WHERE p.workspace_id=? AND p.module=? AND p.record_id=? AND p.user_id!=? AND p.seen_at>=?", (W(), key, rid, g.user["id"], now - 40))
    return jsonify(here=[(r["name"] or r["email"]).split("@")[0] for r in rows])


@route("/m/<key>/<int:rid>/react", methods=["POST"])
def react(key, rid):
    row_or_404(key, rid)
    e = request.form.get("emoji", "")
    back = url_for("m_edit", key=key, rid=rid)
    if e not in REACTIONS:
        return redirect(back)
    have = q("SELECT id FROM reactions WHERE workspace_id=? AND module=? AND record_id=? AND user_id=? AND emoji=?", (W(), key, rid, g.user["id"], e), one=True)
    if have:
        ex("DELETE FROM reactions WHERE id=?", (have["id"],))
    else:
        ins("reactions", dict(workspace_id=W(), module=key, record_id=rid, user_id=g.user["id"], emoji=e))
        row, m = row_or_404(key, rid), mod(key)
        for f in ("assignee", "owner"):
            if f in row.keys():
                mem = S.find_member(W(), row[f])
                if mem and mem["uid"] != g.user["id"]:
                    S.notify(W(), mem["uid"], "reaction", f"{g.user['name'] or g.user['email']} reacted {e} to {_title(m, row)}", back)
                break
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True)
    return redirect(back)


@route("/kudos")
def kudos():
    mates = [m for m in S.members(W()) if m["uid"] != g.user["id"]]
    wall = q("SELECT k.*, a.name AS aname, a.email AS aemail, b.name AS bname, b.email AS bemail FROM kudos k JOIN users a ON a.id=k.from_user JOIN users b ON b.id=k.to_user WHERE k.workspace_id=? ORDER BY k.id DESC LIMIT 60", (W(),))
    return render_template("kudos.html", mates=mates, wall=wall, emojis=KUDOS_EMOJI)


@route("/kudos/send", methods=["POST"])
def kudos_send():
    to = S.to_int(request.form.get("to"), 0)
    note = S.clean_text(request.form.get("note"), 200)
    emoji = request.form.get("emoji", "")
    emoji = emoji if emoji in KUDOS_EMOJI else KUDOS_EMOJI[0]
    mem = next((m for m in S.members(W()) if m["uid"] == to), None)
    if not mem or to == g.user["id"]:
        flash("Pick a teammate to send kudos to.")
        return redirect(url_for("kudos"))
    if not note:
        flash("Say what they nailed, even a few words.")
        return redirect(url_for("kudos"))
    ins("kudos", dict(workspace_id=W(), from_user=g.user["id"], to_user=to, emoji=emoji, note=note))
    S.audit("kudos", f"to user {to}")
    S.notify(W(), to, "kudos", f"{emoji} {g.user['name'] or g.user['email']} sent you kudos: {note[:100]}", url_for("kudos"))
    flash("Cheer sent. Made their day 🎉")
    return redirect(url_for("kudos"))


# ----------------------------------------------------------------- first week
ENQUIRY_INDS = {"b2b", "realestate", "education", "healthcare", "agency", "saas", "fintech", "startup", "personal_brand"}


def _first_week_numbers(industry):
    """Three numbers anyone can type in 20 seconds. They land on the Numbers page straight away, so results show up on day one instead of after a data import."""
    sells = "Enquiries" if industry in ENQUIRY_INDS else "Orders"
    return [("followers", "Followers (all platforms)", "Followers"), ("reach", "Reach or views this week", "Reach"), ("orders", f"{sells} this week", sells)]


@route("/first-week")
def first_week():
    w, t = W(), S.today()
    wk0 = (t - dt.timedelta(days=6)).isoformat()
    c = lambda sql, *a: q(sql, (w,) + a, one=True)["c"]
    published = c("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status='Published' AND publish_date>=?", wk0)
    planned = c("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status NOT IN ('Published') AND publish_date BETWEEN ? AND ?", t.isoformat(), (t + dt.timedelta(days=7)).isoformat())
    done = c("SELECT COUNT(*) c FROM tasks WHERE workspace_id=? AND status='Done'")
    ideas = c("SELECT COUNT(*) c FROM content_items WHERE workspace_id=?")
    days = len({str(r["created_at"])[:10] for r in q("SELECT created_at FROM audit_log WHERE workspace_id=? AND user_id=? ORDER BY id DESC LIMIT 400", (w, g.user["id"]))})
    nxt = q("SELECT name, date FROM key_dates WHERE workspace_id=? AND date>=? ORDER BY date LIMIT 1", (w, t.isoformat()), one=True)
    have_numbers = c("SELECT COUNT(*) c FROM kpis WHERE workspace_id=?") > 0
    stats = [("📝", "Posts planned or live", ideas), ("🚀", "Published this week", published), ("🗓️", "Coming up in 7 days", planned), ("✅", "Tasks finished", done), ("🔥", "Days you showed up", days)]
    share = f"My first week with Debut for {g.ws['name']}: {ideas} posts planned, {published} published, {done} tasks done. Planning content has never been this calm."
    from urllib.parse import quote
    return render_template("first_week.html", stats=stats, nxt=nxt, have_numbers=have_numbers, fields=_first_week_numbers(g.ws["industry"]), share=share, wa="https://wa.me/?text=" + quote(share), brand_name=g.ws["name"])


@route("/first-week/numbers", methods=["POST"])
def first_week_numbers():
    if g.role in ("viewer", "client"):
        abort(403)
    w, t = W(), S.today()
    n = 0
    for key, _label, metric in _first_week_numbers(g.ws["industry"]):
        raw = (request.form.get(key) or "").replace(",", "").strip()
        try:
            val = float(raw)
        except ValueError:
            continue
        if val < 0 or val > 1e12:
            continue
        ins("kpis", dict(workspace_id=w, metric=metric, channel="All", period=t.isoformat(), value=int(val) if val == int(val) else val, target=""))
        n += 1
    flash(f"🎉 {n} number{'s' if n != 1 else ''} saved. This is your starting line." if n else "Type at least one number to see it on your Numbers page.")
    return redirect(url_for("analytics") if n else url_for("first_week"))


# ----------------------------------------------------------------- analytics & UTM
@route("/analytics")
def analytics():
    w, series = W(), {}
    for r in q("SELECT * FROM kpis WHERE workspace_id=? AND period!='' ORDER BY period, id LIMIT 3000", (w,)):
        series.setdefault(r["metric"], []).append(dict(d=r["period"], v=num(r["value"]), t=num(r["target"]) if r["target"] else None))
    cards = []
    for name, pts in list(series.items())[:12]:
        last, prev = pts[-1], (pts[-2] if len(pts) > 1 else None)
        pct = round(last["v"] / last["t"] * 100) if last["t"] else None
        vals = [p["v"] for p in pts][-12:]
        lo, hi = min(vals), max(vals)
        spark = ""
        if len(vals) > 1:
            span = (hi - lo) or 1
            spark = " ".join(f"{'M' if i == 0 else 'L'}{i * 100 / (len(vals) - 1):.1f},{26 - (x - lo) / span * 22:.1f}" for i, x in enumerate(vals))
        cards.append(dict(name=name, pts=pts, last=last["v"], target=last["t"], when=last["d"], pct=pct, spark=spark,
                          delta=(last["v"] - prev["v"]) if prev else None,
                          tone=("win" if pct is not None and pct > 100 else "good" if pct is not None and pct > 90 else "mid" if pct is not None and pct >= 60 else "low" if pct is not None else "")))
    camps = [dict(n=c["name"], b=num(c["budget"]), s=num(c["spent"])) for c in q("SELECT * FROM campaigns WHERE workspace_id=?", (w,)) if num(c["budget"]) or num(c["spent"])]
    funnel = [dict(s=r["stage"], c=r["c"]) for r in q("SELECT stage, COUNT(*) c FROM leads WHERE workspace_id=? GROUP BY stage", (w,))]
    moves = []      # change over the last 4 entries, as a percentage of where it started
    for c in cards:
        vs = [p["v"] for p in c["pts"]][-4:]
        if len(vs) >= 3 and vs[0]:
            moves.append((c["name"], round((vs[-1] - vs[0]) / abs(vs[0]) * 100)))
    working = []
    if moves:
        best, worst = max(moves, key=lambda m: m[1]), min(moves, key=lambda m: m[1])
        if best[1] > 0:
            working.append(f"{best[0]} is your strongest mover: up {best[1]}% over your last few entries. Do more of whatever fed it.")
        if worst[1] < 0 and worst[0] != best[0]:
            working.append(f"{worst[0]} slipped {abs(worst[1])}%. Check what changed around then before you add more effort.")
        hit = [c["name"] for c in cards if c["pct"] is not None and c["pct"] > 100]
        if hit:
            working.append("Over target: " + ", ".join(hit[:3]) + ".")
    import learn as _L
    return render_template("analytics.html", works=_L.what_works(W()), works_line=_L.headline(W()),
                           cards=cards, camps=camps, funnel=funnel, working=working, **_health_ctx())


# ----------------------------------------------------------------- Marketing Health (KPIs + a single gap checklist, for a one-person marketing team)
def _brand_checks():
    kinds = {r["kind"] for r in q("SELECT kind FROM brand_kit WHERE workspace_id=?", (W(),))}
    return [("Primary colour", bool(g.ws["brand_color"]) or "Colour" in kinds),
            ("Logo", bool(g.ws["logo_url"])),
            ("Font", "Font" in kinds),
            ("Voice & tone", "Voice & tone" in kinds)]


def _marketing_gaps():
    w, t = W(), S.today().isoformat()
    missing_brand = len([c for c in _brand_checks() if not c[1]])
    return [
        dict(key="brand_kit", label="Brand Kit categories not filled in yet (colour, logo, font, voice & tone)",
             count=missing_brand, href=url_for("m_list", key="brand_kit")),
        dict(key="campaigns", label="Live or planned campaigns with no KPI target set",
             count=q("SELECT COUNT(*) c FROM campaigns WHERE workspace_id=? AND status IN ('Planning','Live') AND (kpi_target IS NULL OR kpi_target='')", (w,), one=True)["c"],
             href=url_for("m_list", key="campaigns")),
        dict(key="content_items", label="Content items with no publish date (won't show on the calendar)",
             count=q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND (publish_date IS NULL OR publish_date='') AND status NOT IN ('Published','On hold')", (w,), one=True)["c"],
             href=url_for("m_list", key="content_items")),
        dict(key="content_overdue", label="Content items past their publish date but not marked Published",
             count=q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND publish_date!='' AND publish_date<? AND status NOT IN ('Published','On hold')", (w, t), one=True)["c"],
             href=url_for("calendar_view")),
        dict(key="tasks", label="Overdue tasks",
             count=q("SELECT COUNT(*) c FROM tasks WHERE workspace_id=? AND status!='Done' AND due_date!='' AND due_date<?", (w, t), one=True)["c"],
             href=url_for("m_list", key="tasks")),
        dict(key="leads", label="Leads in progress with no next step planned",
             count=q("SELECT COUNT(*) c FROM leads WHERE workspace_id=? AND stage NOT IN ('Won','Lost') AND (next_step IS NULL OR next_step='')", (w,), one=True)["c"],
             href=url_for("m_list", key="leads")),
    ]


def _health_ctx():
    w, t = W(), S.today().isoformat()
    brand_checks = _brand_checks()
    brand_score = round(100 * sum(1 for _, ok in brand_checks if ok) / len(brand_checks))
    due = q("SELECT status FROM content_items WHERE workspace_id=? AND publish_date!='' AND publish_date<=?", (w, t))
    n_due, n_published = len(due), len([r for r in due if r["status"] == "Published"])
    posting_pct = round(100 * n_published / n_due) if n_due else None
    camps = q("SELECT * FROM campaigns WHERE workspace_id=?", (w,))
    budgeted = [c for c in camps if c["status"] in ("Live", "Completed") and num(c["budget"]) > 0]
    util_pct = round(100 * sum(num(c["spent"]) for c in budgeted) / sum(num(c["budget"]) for c in budgeted)) if budgeted else None
    over_budget = len([c for c in budgeted if num(c["spent"]) > num(c["budget"])])
    leads = q("SELECT stage, value FROM leads WHERE workspace_id=?", (w,))
    won = [r for r in leads if r["stage"] == "Won"]
    conv_pct = round(100 * len(won) / len(leads)) if leads else None
    gaps = _marketing_gaps()
    return dict(brand_checks=brand_checks, brand_score=brand_score,
                           n_due=n_due, n_published=n_published, posting_pct=posting_pct,
                           n_campaigns=len(camps), util_pct=util_pct, over_budget=over_budget,
                           n_leads=len(leads), n_won=len(won), conv_pct=conv_pct, won_value=sum(num(r["value"]) for r in won),
                           gaps=gaps, smtp_on=bool(C.SMTP_HOST))


@route("/utm/new")
def utm_new():
    modal = request.args.get("modal") == "1"
    return render_template("utm_form_frag.html" if modal else "utm_form.html", modal=modal,
                           camps=[r["name"] for r in q("SELECT name FROM campaigns WHERE workspace_id=?", (W(),))])


@route("/utm")
def utm():
    return render_template("utm.html", rows=q("SELECT * FROM utm_links WHERE workspace_id=? ORDER BY id DESC LIMIT 50", (W(),)),
                           camps=[r["name"] for r in q("SELECT name FROM campaigns WHERE workspace_id=?", (W(),))])


# ----------------------------------------------------------------- AI studio (metered)
@route("/ai")
def ai_studio():
    industry = g.ws["industry"]
    mine = [(k, v[0], C.AI_COST.get(k, 1) + (C.AI_RESEARCH_EXTRA if k in FORCE_RESEARCH else 0)) for k, v in AI_TASKS.items() if industry in AI_TASK_FOR.get(k, ())]
    live = [(k, AI_TASKS[k][0], C.AI_COST.get(k, 1) + C.AI_RESEARCH_EXTRA) for k in AI_TASKS if k in FORCE_RESEARCH] if C.AI_WEB_SEARCH else []
    rest = [(k, v[0], C.AI_COST.get(k, 1)) for k, v in AI_TASKS.items() if k not in AI_TASK_FOR and k not in FORCE_RESEARCH and k not in HIDDEN_TASKS]
    return render_template("ai.html", tasks=mine + live + rest, n_mine=len(mine), n_live=len(live), ind=IND.get(industry), has_key=bool(C.ANTHROPIC_API_KEY),
                           used=S.credits_used(W()), limit=g.plan["ai_credits"], web=C.AI_WEB_SEARCH, extra=C.AI_RESEARCH_EXTRA, force=sorted(FORCE_RESEARCH), voice=g.ws["ai_voice"] or "", lang=g.ws["ai_lang"] or "English", langs=list(AI_LANGS))


AI_LANGS = {"English": "English", "Hinglish": "Hinglish: natural Hindi and English mixed in Roman script, the way urban Indians talk and post (not translated textbook Hindi)", "Hindi": "Hindi in Devanagari script"}


class ClaudeError(Exception):
    pass


def claude_call(system, prompt, max_tokens, research=False):
    """One Claude request (optionally with live web search). Returns (text, sources). Sources are the pages Claude actually used."""
    body = {"model": C.GTM_MODEL, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": prompt}]}
    if research:
        body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 4, "user_location": {"type": "approximate", "country": "IN", "timezone": "Asia/Kolkata"}}]
    headers = {"x-api-key": C.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    texts, sources, first = [], {}, list(body["messages"])
    for _ in range(3):                                   # a long search can pause the turn; continue up to twice
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=180)
        data = r.json()
        if r.status_code != 200:
            msg = (data.get("error", {}).get("message", "") if isinstance(data, dict) else "") or ""
            raise ClaudeError("web" if research and ("web_search" in msg.lower() or "web search" in msg.lower()) else "")
        for blk in data.get("content", []):
            if blk.get("type") == "text":
                texts.append(blk.get("text", ""))
                for c in blk.get("citations") or []:
                    u = S.clean_url(c.get("url"))
                    if u:
                        sources.setdefault(u, S.clean_text(c.get("title"), 140) or u)
            elif blk.get("type") == "web_search_tool_result" and isinstance(blk.get("content"), list):
                for c in blk["content"]:
                    u = S.clean_url(c.get("url")) if isinstance(c, dict) else ""
                    if u:
                        sources.setdefault(u, S.clean_text(c.get("title"), 140) or u)
        if data.get("stop_reason") != "pause_turn":
            break
        body["messages"] = first + [{"role": "assistant", "content": data["content"]}]
    return "".join(texts), list(sources.items())[:12]


def ai_guard(cost):
    """Shared checks before any AI call: configured, verified email, platform daily cap, monthly credits. Returns (error_response, used, limit)."""
    if not C.ANTHROPIC_API_KEY:
        return (jsonify(error="AI is not configured on this server yet."), 400), 0, 0
    if S.needs_verify(g.user):
        return (jsonify(error="Please verify your email to use AI Studio (use the link in the yellow banner, or press Resend link)."), 403), 0, 0
    used, limit = S.credits_used(W()), g.plan["ai_credits"]
    if C.AI_DAILY_CAP and q("SELECT COALESCE(SUM(credits),0) c FROM ai_usage WHERE created_at>=?", (dt.datetime.now(dt.timezone.utc).date().isoformat(),), one=True)["c"] + cost > C.AI_DAILY_CAP:
        S.audit("ai_daily_cap_hit")
        return (jsonify(error="AI Studio is very busy today and has reached its daily limit. Please try again tomorrow."), 503), used, limit
    if used + cost > limit:
        return (jsonify(error=f"You've used {used} of {limit} AI credits this month. Upgrade your plan or wait for the monthly reset."), 402), used, limit
    return None, used, limit


def workspace_context():
    """Plan, personas and brand kit, for prompts that should sound like this business."""
    parts = []
    p = q("SELECT * FROM gtm_plans WHERE workspace_id=? ORDER BY id DESC LIMIT 1", (W(),), one=True)
    if p:
        parts.append("LATEST GTM PLAN:\n" + "\n".join(f"{k}: {p[k]}" for k in p.keys() if p[k] and k not in ("id", "created_at", "workspace_id")))
    pers = q("SELECT * FROM personas WHERE workspace_id=? ORDER BY id DESC LIMIT 3", (W(),))
    if pers:
        parts.append("PERSONAS:\n" + "\n".join(f"{p['name']} ({p['role']}): pains {p['pain_points']}; goals {p['goals']}; objections {p['objections']}" for p in pers))
    brand = q("SELECT * FROM brand_kit WHERE workspace_id=? LIMIT 40", (W(),))
    if brand:
        parts.append("BRAND KIT:\n" + "\n".join(f"{b['kind']} - {b['name']}: {b['value']} {b['notes']}" for b in brand))
    return parts


def ai_fail(e):
    if isinstance(e, ClaudeError) and str(e) == "web":
        return jsonify(error="Live web research isn't enabled for this server's AI account yet. Ask the administrator to enable web search in the Anthropic console, or untick live research."), 502
    return jsonify(error="The AI service returned an error. Please try again." if isinstance(e, ClaudeError) else "Could not reach the AI service. Please try again."), 502


@route("/api/ai", methods=["POST"])
@limiter.limit("5 per minute;60 per hour")
def api_ai():
    d = S.jbody()
    if not C.ANTHROPIC_API_KEY:
        return jsonify(error="AI is not configured on this server yet."), 400
    task = d.get("task")
    if task not in AI_TASKS or task in HIDDEN_TASKS:
        return jsonify(error="Unknown task"), 400
    research = bool(d.get("research")) or task in FORCE_RESEARCH
    if research and not C.AI_WEB_SEARCH:
        return jsonify(error="Live web research is switched off on this server."), 400
    cost = C.AI_COST.get(task, 1) + (C.AI_RESEARCH_EXTRA if research else 0)
    err, used, limit = ai_guard(cost)
    if err:
        return err
    t = lambda k, n=1000: S.clean_text(d.get(k, ""), n)
    ind = IND.get(g.ws["industry"])
    voice, lang = (g.ws["ai_voice"] or ""), (g.ws["ai_lang"] or "English")
    if "voice" in d and g.role in ("owner", "admin", "manager", "lead"):      # saved once, used every time
        voice = t("voice", 600)
        lang = d.get("lang") if d.get("lang") in AI_LANGS else "English"
        ex("UPDATE workspaces SET ai_voice=?, ai_lang=? WHERE id=?", (voice, lang, W()))
    parts = [f"TASK: {AI_TASKS[task][1]}", f"Business industry: {ind['label']}", f"Brand voice (write the way this brand talks): {voice or 'not set'}", f"Write in: {AI_LANGS.get(lang, AI_LANGS['English'])}", f"Product/brand: {t('product')}", f"Target audience: {t('audience')}", f"Tone: {t('tone')}", f"Extra instructions: {t('extra', 8000)}"]
    if d.get("use_plan"):
        parts += workspace_context()
    if task == "report":
        parts.append("KPI LOG (latest 80):\n" + "\n".join(f"{r['period']} {r['metric']} ({r['channel']}): actual {r['value']} vs target {r['target']}" for r in q("SELECT * FROM kpis WHERE workspace_id=? ORDER BY period DESC LIMIT 80", (W(),))))
        parts.append("CAMPAIGNS:\n" + "\n".join(f"{c['name']} [{c['status']}] budget {c['budget']} spent {c['spent']} KPI {c['kpi_target']}" for c in q("SELECT * FROM campaigns WHERE workspace_id=?", (W(),))))
    if research:
        parts.append("Use the web search tool for current facts. Prefer recent, reputable sources (Indian and global). Do not present anything you did not find as fact.")
    try:
        text, sources = claude_call(SYSTEM + "\nINDUSTRY CONTEXT: " + ind["ai_context"], "\n".join(parts), 6000 if task == "calendar" else 4000, research)
    except Exception as e:
        return ai_fail(e)
    ins("ai_usage", dict(workspace_id=W(), user_id=g.user["id"], task=task, credits=cost, month=S.month_key()))
    return jsonify(text=text, sources=[dict(url=u, title=tl) for u, tl in sources], used=used + cost, limit=limit)


@route("/api/ask", methods=["POST"])
@limiter.limit("10 per minute;60 per hour")
def api_ask():
    """Ask Debut: a free-form question answered using this workspace's own data as context."""
    d = S.jbody()
    question = S.clean_text(d.get("q", ""), 500)
    if not question:
        return jsonify(error="Type a question first."), 400
    if not C.ANTHROPIC_API_KEY:
        return jsonify(error="AI is not configured on this server yet."), 400
    if S.needs_verify(g.user):
        return jsonify(error="Please verify your email to use Ask Debut."), 403
    cost = C.AI_COST.get("ask_debut", 1)
    err, used, limit = ai_guard(cost)
    if err:
        return err
    parts = ["The user is asking a question inside their own marketing workspace. Answer directly and specifically using the context below where relevant. "
             "If the answer depends on their own data and nothing below covers it, say so plainly instead of guessing. Keep it concise — a few sentences or a short list, not an essay.",
             f"QUESTION: {question}"]
    parts += workspace_context()
    counts = {m["title"]: q(f"SELECT COUNT(*) c FROM {key} WHERE workspace_id=?", (W(),), one=True)["c"] for key, m in list(MODULES.items())[:12] if not locked(key)}
    parts.append("WHAT THEY HAVE IN THE APP RIGHT NOW: " + ", ".join(f"{k}: {v}" for k, v in counts.items() if v))
    try:
        text, _ = claude_call(SYSTEM + "\nYou are 'Ask Debut', a built-in assistant inside the Debut marketing app. You can also point the user to the right page in the app by name (e.g. 'see GTM Plans' or 'check Market Pulse') when that's the real answer.",
                               "\n".join(parts), 900, research=False)
    except Exception as e:
        return ai_fail(e)
    ins("ai_usage", dict(workspace_id=W(), user_id=g.user["id"], task="ask_debut", credits=cost, month=S.month_key()))
    return jsonify(text=text, used=used + cost, limit=limit)


@route("/api/save_asset", methods=["POST"])
def api_save_asset():
    d = S.jbody()
    ins("assets", dict(workspace_id=W(), title=S.clean_text(d.get("title", "AI output"), 200), type=S.clean_text(d.get("type", "AI"), 50), channel="Other", status="Draft", campaign="", body=S.clean_text(d.get("body", ""), 50000)))
    return jsonify(ok=True)


@route("/api/import_calendar", methods=["POST"])
def api_import_calendar():
    txt = str(S.jbody().get("text", ""))
    a, b = txt.find("["), txt.rfind("]")
    try:
        arr = json.loads(txt[a:b + 1])
    except Exception:
        return jsonify(error="Could not parse JSON from the AI output. Try generating again."), 400
    n = 0
    room = g.plan["records"] - S.record_count(W())
    for it in arr[:120]:
        if not isinstance(it, dict) or n >= room:
            continue
        ch, fm = it.get("channel", "Other"), it.get("format", "Post")
        try:
            date = dt.date.fromisoformat(str(it.get("publish_date", ""))[:10]).isoformat()
        except ValueError:
            date = ""
        ins("content_items", dict(workspace_id=W(), title=S.clean_text(it.get("title", ""), 200), channel=ch if ch in CHANNELS else "Other", format=fm if fm in FORMATS else "Post", status="Planned",
                                  publish_date=date, copy=S.clean_text(it.get("copy", "")), cta=S.clean_text(it.get("cta", ""), 300), hashtags=S.clean_text(it.get("hashtags", ""), 500)))
        n += 1
    return jsonify(ok=True, n=n)


# ----------------------------------------------------------------- content ops
@route("/content-ops")
def content_ops():
    w, today = W(), S.today().isoformat()
    orders = q("SELECT * FROM content_orders WHERE workspace_id=?", (w,))
    done = [o for o in orders if o["status"] in DONE_ORDER]
    rev, cost = sum(num(o["price_client"]) for o in done), sum(num(o["cost_creator"]) for o in done)
    open_orders = [o for o in orders if o["status"] not in DONE_ORDER + ("Cancelled",)]
    pipe = sum(num(o["price_client"]) for o in open_orders)
    by = {}
    for o in orders:
        if o["creator"]:
            d = by.setdefault(o["creator"], dict(n=0, done=0, qs=[], rev=0))
            d["n"] += 1
            if o["status"] in DONE_ORDER:
                d["done"] += 1
                d["rev"] += num(o["price_client"]) - num(o["cost_creator"])
            if o["quality_score"]:
                d["qs"].append(num(o["quality_score"]))
    creators = sorted([(k, v["n"], v["done"], round(sum(v["qs"]) / len(v["qs"]), 1) if v["qs"] else "-", v["rev"]) for k, v in by.items()], key=lambda x: -x[2])
    pays = q("SELECT * FROM payments WHERE workspace_id=? AND status!='Paid'", (w,))
    slug = g.ws["slug"]
    return render_template("content_ops.html", rev=rev, cost=cost, pipe=pipe, overdue=[o for o in open_orders if o["due_date"] and o["due_date"] < today],
                           unassigned=[o for o in open_orders if not o["creator"]], stat=Counter(o["status"] for o in orders), creators=creators,
                           money_in=sum(num(p["amount"]) for p in pays if p["direction"].endswith("(in)")), money_out=sum(num(p["amount"]) for p in pays if p["direction"].endswith("(out)")),
                           pc=Counter(c["status"] for c in q("SELECT status FROM creators WHERE workspace_id=?", (w,))), n_orders=len(orders), statuses=ORDER_STATUS,
                           apply_url=S.app_url() + url_for("apply_form", slug=slug))


@route("/orders/<int:oid>/match")
def order_match(oid):
    o = row_or_404("content_orders", oid)
    skill, lang = ORDER_SKILL.get(o["type"], ""), request.args.get("lang", "").strip().lower()
    cs = [c for c in q("SELECT * FROM creators WHERE workspace_id=? AND status IN ('Vetted','Active')", (W(),))
          if (not skill or skill.lower() in (c["skills"] or "").lower()) and (not lang or lang in (c["languages"] or "").lower())]
    cs.sort(key=lambda c: (-num(c["rating"]), -num(c["test_score"])))
    return render_template("match.html", o=o, skill=skill, cs=cs, lang=lang)


@route("/orders/<int:oid>/assign/<int:cid>", methods=["POST"])
def order_assign(oid, cid):
    row_or_404("content_orders", oid)
    c = row_or_404("creators", cid)
    ex("UPDATE content_orders SET creator=?, status=CASE WHEN status='Brief received' THEN 'Assigned' ELSE status END WHERE id=? AND workspace_id=?", (c["name"], oid, W()))
    flash(f"Assigned to {c['name']}.")
    return redirect(url_for("m_edit", key="content_orders", rid=oid))


@route("/apply/<slug>", methods=["GET", "POST"])
@limiter.limit("6 per hour", methods=["POST"])
def apply_form(slug):
    """Public creator application form. Each workspace has its own link."""
    ws = q("SELECT * FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    if not S.feature_ok(ws, "content_ops"):
        abort(404)
    if request.method == "POST":
        f = request.form
        if not f.get("website"):  # honeypot: bots fill hidden fields
            if q("SELECT COUNT(*) c FROM creators WHERE workspace_id=?", (ws["id"],), one=True)["c"] < 5000:
                t = S.clean_text
                ins("creators", dict(workspace_id=ws["id"], name=t(f.get("name"), 100), email=t(f.get("email"), 150), phone=t(f.get("phone"), 40), skills=t(f.get("skills"), 300),
                                     niches=t(f.get("niches"), 300), languages=t(f.get("languages"), 200), city=t(f.get("city"), 80), portfolio_url=S.clean_url(f.get("portfolio_url", "")),
                                     rate=t(f.get("rate"), 80), status="Applied", notes=t(f.get("notes"), 1000)))
        return render_template("apply.html", done=True, skills_hint=SKILLS_HINT, ws=ws, bare=True)
    return render_template("apply.html", done=False, skills_hint=SKILLS_HINT, ws=ws, bare=True)


# ----------------------------------------------------------------- influencer discovery & outreach
def discover_links(kw, city, lang):
    query = " ".join(x for x in [kw, city, lang] if x).strip()
    tag = re.sub(r"[^a-z0-9]", "", kw.lower())
    gg = lambda s: "https://www.google.com/search?q=" + quote_plus(s)
    Q = quote_plus(query)
    out = OrderedDict()
    out["Instagram"] = ([("Hashtag: #" + tag, f"https://www.instagram.com/explore/tags/{tag}/")] if tag else []) + [
        ("Google: profiles", gg(f'site:instagram.com "{query}"')), ("Google: with contact / collab info", gg(f'site:instagram.com "{query}" ("collab" OR "email" OR "DM for" OR "business")'))]
    out["YouTube"] = [("Channels search", f"https://www.youtube.com/results?search_query={Q}&sp=EgIQAg%253D%253D"), ("Videos search", f"https://www.youtube.com/results?search_query={Q}")]
    out["LinkedIn"] = [("People", f"https://www.linkedin.com/search/results/people/?keywords={Q}"), ("Posts", f"https://www.linkedin.com/search/results/content/?keywords={Q}")]
    out["X / Twitter"] = [("Accounts", f"https://x.com/search?q={Q}&f=user"), ("Posts", f"https://x.com/search?q={Q}")]
    out["Facebook"] = [("Pages", f"https://www.facebook.com/search/pages?q={Q}"), ("Groups", f"https://www.facebook.com/search/groups?q={Q}")]
    out["Threads"] = [("Search", f"https://www.threads.net/search?q={Q}")]
    out["Pinterest"] = [("Creators", f"https://www.pinterest.com/search/users/?q={Q}")]
    out["Reddit"] = [("Communities & posts", f"https://www.reddit.com/search/?q={Q}")]
    out["ShareChat / Moj"] = [("Google: profiles", gg(f'site:sharechat.com "{query}"'))]
    out["Podcasts"] = [("Apple Podcasts via Google", gg(f'site:podcasts.apple.com "{query}"'))]
    out["Blogs & newsletters"] = [("Blogs open to collabs", gg(f'"{query}" blog ("collaborate" OR "work with brands" OR "write for us")')), ("Substack", gg(f'site:substack.com "{query}"'))]
    out["Any platform"] = [("Influencer lists / rate cards", gg(f'"{query}" influencers list India')), ("Contact emails (public)", gg(f'"{query}" influencer "business enquiries" OR "collab" email'))]
    return out


DISCOVERY_TOOLS = [("Modash", "https://www.modash.io"), ("Qoruz", "https://www.qoruz.com"), ("Winkl", "https://www.winkl.co"),
                   ("Kofluence", "https://www.kofluence.com"), ("Plixxo", "https://www.plixxo.com"), ("Upfluence", "https://www.upfluence.com")]


@route("/discover")
def discover():
    kw, city, lang = request.args.get("kw", "").strip()[:100], request.args.get("city", "").strip()[:60], request.args.get("lang", "").strip()[:40]
    return render_template("discover.html", kw=kw, city=city, lang=lang, links=discover_links(kw, city, lang) if kw else None, tools=DISCOVERY_TOOLS, platforms=PLATFORMS)


@route("/influencers/<int:iid>/outreach")
def outreach(iid):
    inf = row_or_404("influencers", iid)
    tpls = q("SELECT * FROM outreach_templates WHERE workspace_id=? ORDER BY id", (W(),))
    tid = request.args.get("t") or (tpls[0]["id"] if tpls else None)
    brand, campaign, sender = request.args.get("brand", "our brand")[:80], request.args.get("campaign", "our upcoming campaign")[:120], request.args.get("sender", "")[:80]
    tpl = next((t for t in tpls if str(t["id"]) == str(tid)), None)
    subject = body = ""
    if tpl:
        def fill(t):
            for k, v in dict(name=(inf["name"] or "there").split(" ")[0], brand=brand, platform=inf["platform"], campaign=campaign, sender=sender).items():
                t = t.replace("{" + k + "}", v or "")
            return t
        subject, body = fill(tpl["subject"]), fill(tpl["body"])
    mailto = f"mailto:{quote(inf['email'])}?subject={quote(subject)}&body={quote(body)}" if inf["email"] else ""
    return render_template("outreach.html", inf=inf, tpls=tpls, tid=str(tid), brand=brand, campaign=campaign, sender=sender, subject=subject, body=body, mailto=mailto)


@route("/influencers/<int:iid>/contacted", methods=["POST"])
def influencer_contacted(iid):
    row_or_404("influencers", iid)
    t = S.today()
    ex("UPDATE influencers SET last_contacted=?, next_followup=?, status=CASE WHEN status IN ('Prospect','Shortlisted') THEN 'Contacted' ELSE status END WHERE id=? AND workspace_id=?",
       (t.isoformat(), (t + dt.timedelta(days=4)).isoformat(), iid, W()))
    flash("Marked as contacted; follow-up set for 4 days from now.")
    return redirect(url_for("m_list", key="influencers"))


@route("/events/<int:eid>/checklist", methods=["POST"])
def event_checklist(eid):
    e = row_or_404("events", eid)
    items = ONLINE_CHECK if request.form.get("mode") == "online" else OFFLINE_CHECK
    try:
        base = dt.date.fromisoformat(e["date"])
    except (ValueError, TypeError):
        base = None
    for title, off in items:
        ins("tasks", dict(workspace_id=W(), title=title, description="", assignee=e["owner"], due_date=(base + dt.timedelta(days=off)).isoformat() if base else "", priority="Medium", status="To do", related=e["name"]))
    flash(f"Added {len(items)} checklist tasks to Tasks" + ("" if base else " (set an event date to auto-fill due dates)") + ".")
    return redirect(url_for("m_list", key="tasks", q=e["name"]))


# ----------------------------------------------------------------- group mode: team hub (lead / admin / owner) and idea bank
@route("/team-hub")
@S.roles(*C.TEAM_MANAGERS)
def team_hub():
    """One screen for a team lead: who is doing what, what is overdue, what needs approval, what publishes soon."""
    w, today = W(), S.today()
    t, wk, ago = today.isoformat(), (today + dt.timedelta(days=7)).isoformat(), (today - dt.timedelta(days=7)).isoformat()
    members = q("SELECT m.role, u.id AS uid, u.name, u.email, u.last_login FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=? AND m.role!='client' ORDER BY m.id", (w,))
    tasks = q("SELECT * FROM tasks WHERE workspace_id=? AND status!='Done' ORDER BY due_date LIMIT 3000", (w,))
    items = q("SELECT owner, status FROM content_items WHERE workspace_id=? AND status NOT IN ('Published') LIMIT 5000", (w,))
    acts = {r["user_id"]: r["c"] for r in q("SELECT user_id, COUNT(*) c FROM audit_log WHERE workspace_id=? AND created_at>=? GROUP BY user_id", (w, ago))}
    rows = []
    for m in members:
        keys = {(m["name"] or "").strip().lower(), (m["email"] or "").lower()} - {""}
        mine = [x for x in tasks if (x["assignee"] or "").strip().lower() in keys]
        rows.append(dict(m=m, open=len(mine), overdue=len([x for x in mine if x["due_date"] and x["due_date"] < t]),
                         content=len([x for x in items if (x["owner"] or "").strip().lower() in keys]), actions=acts.get(m["uid"], 0)))
    overdue = [x for x in tasks if x["due_date"] and x["due_date"] < t]
    unassigned = [x for x in tasks if not (x["assignee"] or "").strip()]
    review = q("SELECT * FROM content_items WHERE workspace_id=? AND status='Review' ORDER BY publish_date LIMIT 30", (w,))
    orders = q("SELECT * FROM content_orders WHERE workspace_id=? AND status IN ('Editing / QA','Client review') ORDER BY due_date LIMIT 30", (w,))
    soon = q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ? AND status!='Published' ORDER BY publish_date LIMIT 30", (w, t, wk))
    feed = q("SELECT a.*, u.name AS uname FROM audit_log a LEFT JOIN users u ON u.id=a.user_id WHERE a.workspace_id=? ORDER BY a.id DESC LIMIT 15", (w,))
    return render_template("team_hub.html", rows=rows, overdue=overdue[:10], unassigned=unassigned[:10], n_overdue=len(overdue), n_open=len(tasks), review=review, orders=orders, soon=soon, feed=feed, today=t)


NEXT_TOOLS = [("content_items", "📝", "Plan a post", "Put your first post on the calendar"),
              ("tasks", "🗂️", "Make a to-do", "Turn a thought into a task with a date"),
              ("campaigns", "📣", "Start a campaign", "Group your posts under one goal"),
              ("leads", "🧲", "Catch a lead", "Keep track of people who are interested"),
              ("events", "🎪", "Plan a drop or event", "Dates, budget and checklist in one place"),
              ("influencers", "🤳", "Find your people", "Track who you've pinged and who replied")]


def next_tools(w, limit=2):
    """Gentle, never-locked suggestions: the first few tools this workspace hasn't touched yet."""
    out = []
    for k, ic, title, why in NEXT_TOOLS:
        if k not in MODULES or locked(k) or (g.role == "creator" and k not in CREATOR_MODULES):
            continue
        if q(f"SELECT COUNT(*) c FROM {k} WHERE workspace_id=?", (w,), one=True)["c"] == 0:
            out.append(dict(icon=ic, title=title, why=why, href=url_for("m_new", key=k)))
        if len(out) >= limit:
            break
    return out


WHATNOW_VIBES = ["Okay bestie, here's the move.", "No overthinking. Just this one thing.", "Tiny step, big glow-up.", "Main character move, coming right up.", "You've got this. Start here.", "Low effort, high payoff. Go."]


@route("/whatnow")
def whatnow():
    w, t = g.ws["id"], S.today().isoformat()
    picks = []
    for r in q("SELECT * FROM tasks WHERE workspace_id=? AND due_date!='' AND due_date<=? AND status NOT IN ('Done','Completed') ORDER BY due_date LIMIT 3", (w, t)):
        picks.append(dict(icon="⏰", title=f"Finish: {r['title']}", why="It's due, so clear it and feel lighter.", href=url_for("m_edit", key="tasks", rid=r["id"])))
    for r in q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date!='' AND publish_date<=? AND status NOT IN ('Published','On hold') ORDER BY publish_date LIMIT 3", (w, t)):
        picks.append(dict(icon="📝", title=f"Get this out: {r['title']}", why="It's meant to go live today or earlier.", href=url_for("m_edit", key="content_items", rid=r["id"])))
    for r in q("SELECT * FROM influencers WHERE workspace_id=? AND next_followup!='' AND next_followup<=? AND status NOT IN ('Booked','Delivered','Rejected') ORDER BY next_followup LIMIT 2", (w, t)):
        picks.append(dict(icon="🤳", title=f"Slide into {r['name']}'s DMs", why="Follow-up time. Quick message, done.", href=url_for("outreach", iid=r["id"])))
    soon_end = (S.today() + dt.timedelta(days=3)).isoformat()
    for r in q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date>? AND publish_date<=? AND status IN ('Idea','Drafting','Planned') ORDER BY publish_date LIMIT 2", (w, t, soon_end)):
        picks.append(dict(icon="✍️", title=f"Get “{r['title']}” ready", why=f"It goes live on {r['publish_date']} and is still marked {r['status']}.", href=url_for("m_edit", key="content_items", rid=r["id"])))
    for r in q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ? AND (copy IS NULL OR copy='') AND status NOT IN ('Published','On hold') ORDER BY publish_date LIMIT 2", (w, t, (S.today() + dt.timedelta(days=7)).isoformat())):
        picks.append(dict(icon="📝", title=f"Write the caption for “{r['title']}”", why=f"It publishes on {r['publish_date']} and has no copy yet.", href=url_for("m_edit", key="content_items", rid=r["id"])))
    if q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=?", (w,), one=True)["c"] and not q("SELECT 1 FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ?", (w, t, (S.today() + dt.timedelta(days=7)).isoformat()), one=True):
        picks.append(dict(icon="📅", title="Nothing is planned for the next 7 days", why="A quiet calendar means a quiet feed. Pick two ideas and give them dates.", href=url_for("ideas")))
    for r in q("SELECT * FROM leads WHERE workspace_id=? AND stage NOT IN ('Won','Lost') AND (next_step IS NULL OR next_step='') ORDER BY id DESC LIMIT 1", (w,)):
        picks.append(dict(icon="🧲", title=f"Decide the next step for {r['name'] or r['company'] or 'a lead'}", why="A lead with no next step goes cold fast.", href=url_for("m_edit", key="leads", rid=r["id"])))
    for r in q("SELECT * FROM kpis WHERE workspace_id=? AND target!='' AND value!='' ORDER BY period DESC, id DESC LIMIT 40", (w,)):
        if num(r["target"]) and num(r["value"]) / num(r["target"]) < 0.6 and not any(p_["title"].startswith(f"{r['metric']} is") for p_ in picks):
            picks.append(dict(icon="📉", title=f"{r['metric']} is at {round(num(r['value']) / num(r['target']) * 100)}% of target", why="The biggest gap on your scoreboard. See what moved it.", href=url_for("analytics")))
            break
    picks += next_tools(w, 3)
    picks.append(dict(icon="💡", title="Steal an idea", why="Stuck? The Idea Bank has starters for your industry.", href=url_for("ideas")))
    picks.append(dict(icon="🖼️", title="Vibe check", why="Pin a few images to a mood board. Zero pressure.", href=url_for("moodboards")))
    n = request.args.get("n", type=int) or 0
    pick = picks[n % len(picks)]
    return render_template("whatnow.html", pick=pick, n=n, more=len(picks) > 1, vibe=WHATNOW_VIBES[(n + len(picks)) % len(WHATNOW_VIBES)])


@route("/ideas")
def ideas():
    ind = IND.get(g.ws["industry"])
    have = {r["name"] for r in q("SELECT name FROM personas WHERE workspace_id=?", (W(),))}
    import studio as _st
    today = S.today()
    return render_template("ideas.html", ind=ind, can_kpi="analytics" in g.plan["features"], have_personas=have,
                           items=_st.suggestions(W(), g.ws["industry"], today), today=today.isoformat(), canwrite=g.role not in ("viewer", "client"))


@route("/ideas/picker")
def ideas_picker():
    """A handful of content ideas only - just the part of Idea Bank someone drafting a content item actually
    needs - shown as a small overlay (pop-up, with a close/cross) instead of leaving the page for the full
    Idea Bank. There's no separate 'idea bank for this' destination: it's the same ideas, in a smaller box."""
    ind = IND.get(g.ws["industry"])
    return render_template("ideas_picker.html", ind=ind)


# ----------------------------------------------------------------- comments, notifications
@route("/m/<key>/<int:rid>/comment", methods=["POST"])
def comment_add(key, rid):
    m = mod(key)
    row = row_or_404(key, rid)
    body = S.clean_text(request.form.get("body"), 2000)
    back = url_for("m_edit", key=key, rid=rid) + "#comments"
    if not body:
        flash("Write a comment first.")
        return redirect(back)
    shared = bool(request.form.get("client_visible")) and key == "content_items" and g.role in ("owner", "admin", "lead", "manager") and bool((row["client"] or "").strip())
    ins("comments", dict(workspace_id=W(), module=key, record_id=rid, user_id=g.user["id"], body=body, client_visible=1 if shared else 0))
    S.audit("comment", f"{key}#{rid}" + (" (shared with client)" if shared else ""))
    if shared:
        for cm in S.client_members(W(), row["client"]):
            S.notify(W(), cm["uid"], "client_comment", f"{g.user['name'] or g.user['email']} replied on {_title(m, row)}: {body[:80]}", url_for("portal_item", iid=rid))
    targets = set(S.mentioned_ids(W(), body))
    for f in ("assignee", "owner"):
        if f in row.keys():
            mem = S.find_member(W(), row[f])
            if mem:
                targets.add(mem["uid"])
            break
    targets.discard(g.user["id"])
    for uid in targets:
        S.notify(W(), uid, "comment", f"{g.user['name'] or g.user['email']} commented on {_title(m, row)}: {body[:80]}", back)
    return redirect(back)


@route("/comments/<int:cid>/delete", methods=["POST"])
def comment_delete(cid):
    c = q("SELECT * FROM comments WHERE id=? AND workspace_id=?", (cid, W()), one=True) or abort(404)
    if c["user_id"] != g.user["id"] and g.role not in C.TEAM_MANAGERS:
        abort(403)
    ex("DELETE FROM comments WHERE id=? AND workspace_id=?", (cid, W()))
    return redirect(url_for("m_edit", key=c["module"], rid=c["record_id"]) + "#comments")


@route("/notifications")
def notifications():
    rows = q("SELECT * FROM notifications WHERE user_id=? AND workspace_id=? ORDER BY id DESC LIMIT 60", (g.user["id"], W()))
    return render_template("notifications.html", rows=rows)


@route("/notifications/recent")
def notifications_recent():
    """Powers the bell's corner pop-up (the full Notifications page stays as its own tab)."""
    rows = q("SELECT id, message, link, is_read, created_at FROM notifications WHERE user_id=? AND workspace_id=? ORDER BY id DESC LIMIT 8", (g.user["id"], W()))
    return jsonify(items=[dict(id=r["id"], message=r["message"], link=url_for("notification_open", nid=r["id"]), is_read=bool(r["is_read"]),
                               created_at=str(r["created_at"])[:16]) for r in rows])


@route("/notifications/read", methods=["POST"])
def notifications_read():
    ex("UPDATE notifications SET is_read=1 WHERE user_id=? AND workspace_id=?", (g.user["id"], W()))
    return redirect(url_for("notifications"))


@route("/notifications/<int:nid>/open")
def notification_open(nid):
    n = q("SELECT * FROM notifications WHERE id=? AND user_id=? AND workspace_id=?", (nid, g.user["id"], W()), one=True) or abort(404)
    ex("UPDATE notifications SET is_read=1 WHERE id=?", (nid,))
    return redirect(n["link"] if (n["link"] or "").startswith("/") and not n["link"].startswith("//") else url_for("notifications"))


@route("/unsubscribe/<token>")
def unsubscribe(token):
    try:
        uid = URLSafeSerializer(C.SECRET_KEY, salt="unsub").loads(token)
    except BadSignature:
        abort(404)
    ex("UPDATE users SET digest=0 WHERE id=?", (S.to_int(uid) or 0,))
    return render_template("error.html", code="✓", msg="You're unsubscribed from the daily digest. You can turn it back on in Account.", bare=True)


# ----------------------------------------------------------------- client report (printable) + public share link
def build_report(wid, month):
    y, mo = int(month[:4]), int(month[5:7])
    first = dt.date(y, mo, 1)
    nxt = (first + dt.timedelta(days=32)).replace(day=1)
    start, end, nxt_s = first.isoformat(), (nxt - dt.timedelta(days=1)).isoformat(), nxt.isoformat()
    kp = {}
    for r in q("SELECT * FROM kpis WHERE workspace_id=? AND period BETWEEN ? AND ? ORDER BY period", (wid, start, end)):
        kp.setdefault(r["metric"], []).append(r)
    kpis = []
    for name, rows in kp.items():
        last = rows[-1]
        v, t = num(last["value"]), num(last["target"]) if last["target"] else None
        kpis.append(dict(metric=name, channel=last["channel"], value=last["value"], target=last["target"], pct=round(v / t * 100) if t else None, points=len(rows)))
    camps = [c for c in q("SELECT * FROM campaigns WHERE workspace_id=? ORDER BY id DESC LIMIT 200", (wid,))
             if c["status"] == "Live" or ((c["start_date"] or "") <= end and ((c["end_date"] or "9999") >= start))]
    content = q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ? ORDER BY publish_date", (wid, start, end))
    by_channel = Counter(c["channel"] for c in content)
    published = len([c for c in content if c["status"] == "Published"])
    leads = q("SELECT * FROM leads WHERE workspace_id=? AND created_at>=? AND created_at<? ORDER BY id DESC LIMIT 500", (wid, start, nxt_s))
    promos = q("SELECT * FROM promotions WHERE workspace_id=? AND start_date<=? AND (end_date>=? OR end_date='') ORDER BY start_date LIMIT 50", (wid, end, start))
    events = q("SELECT * FROM events WHERE workspace_id=? AND date BETWEEN ? AND ? ORDER BY date", (wid, start, end))
    return dict(month=month, label=first.strftime("%B %Y"), kpis=kpis, camps=camps, content=content, by_channel=by_channel.most_common(), published=published,
                leads=leads, lead_stage=Counter(l["stage"] for l in leads).most_common(), promos=promos, events=events,
                budget=sum(num(c["budget"]) for c in camps), spent=sum(num(c["spent"]) for c in camps))


def _month(arg):
    return arg if re.match(r"^\d{4}-(0[1-9]|1[0-2])$", arg or "") else S.today().strftime("%Y-%m")


def report_token():
    return URLSafeSerializer(C.SECRET_KEY, salt="report").dumps([W(), g.ws["ics_key"]])


@route("/report")
def report():
    month = _month(request.args.get("month"))
    share = None
    if "analytics" in g.plan["features"] and g.role in ("owner", "admin", "lead", "manager") and g.ws["ics_key"]:
        share = S.app_url() + url_for("report_public", token=report_token())
    return render_template("report.html", r=build_report(W(), month), ws=g.ws, share=share, public=False, prev_m=(dt.date.fromisoformat(month + "-01") - dt.timedelta(days=1)).strftime("%Y-%m"),
                           next_m=(dt.date.fromisoformat(month + "-01") + dt.timedelta(days=32)).strftime("%Y-%m"))


@route("/r/<token>")
def report_public(token):
    try:
        wid, key_ = URLSafeSerializer(C.SECRET_KEY, salt="report").loads(token)
    except (BadSignature, ValueError, TypeError):
        abort(404)
    ws = q("SELECT * FROM workspaces WHERE id=? AND ics_key=? AND ics_key!=''", (S.to_int(wid) or 0, str(key_)), one=True) or abort(404)
    if not S.feature_ok(ws, "analytics"):
        abort(404)
    month = _month(request.args.get("month"))
    return render_template("report.html", r=build_report(ws["id"], month), ws=ws, share=None, public=True, hide_chrome=True, bare=True,
                           prev_m=(dt.date.fromisoformat(month + "-01") - dt.timedelta(days=1)).strftime("%Y-%m"), next_m=(dt.date.fromisoformat(month + "-01") + dt.timedelta(days=32)).strftime("%Y-%m"))


# ----------------------------------------------------------------- lead capture: hosted form + website webhook
def _add_lead(ws, f, source, consent=False):
    if q("SELECT COUNT(*) c FROM leads WHERE workspace_id=?", (ws["id"],), one=True)["c"] >= 20000:
        return False
    t = S.clean_text
    note = t(f.get("message") or f.get("notes"), 1900)
    if consent:
        note = (note + "\n" if note else "") + f"[Consent to be contacted given on the enquiry form, {S.today().isoformat()}]"
    ins("leads", dict(workspace_id=ws["id"], name=t(f.get("name"), 120), company=t(f.get("company"), 120), email=t(f.get("email"), 200), phone=t(f.get("phone"), 40),
                      source=t(f.get("source"), 120) or source, stage="New", value="", next_step="Follow up", notes=note))
    return True


@route("/lead/<slug>", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def lead_form(slug):
    """Public enquiry form for a workspace: link it from your bio, website or QR code. Creates a lead."""
    ws = q("SELECT * FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    done = False
    if request.method == "POST":
        f = request.form
        if not f.get("website"):     # honeypot
            if not f.get("consent") or not (f.get("email") or f.get("phone")):
                flash("Add an email or phone number and tick the consent box, then we are good.")
                return render_template("lead_form.html", ws=ws, done=False, bare=True, hide_chrome=True, form=f), 400
            _add_lead(ws, f, "Link in bio" if request.args.get("src") == "bio" else "Website form", consent=True)
        done = True
    return render_template("lead_form.html", ws=ws, done=done, bare=True, hide_chrome=True, form={})


@route("/hooks/lead/<key>", methods=["POST", "OPTIONS"])
@limiter.limit("300 per hour", methods=["POST"])
def lead_hook(key):
    """Webhook for your own website form (or Zapier/Make): POST JSON or form fields name, email, phone, company, message, source."""
    cors = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"}
    if request.method == "OPTIONS":
        return Response("", 204, cors)
    ws = q("SELECT * FROM workspaces WHERE hook_key=? AND hook_key!=''", (key,), one=True)
    if not ws:
        return jsonify(error="unknown key"), 404, cors
    f = request.get_json(silent=True) if request.is_json else request.form
    if not isinstance(f, dict) and not hasattr(f, "get"):
        return jsonify(error="send a JSON object or form fields"), 400, cors
    if not (f.get("email") or f.get("phone")):
        return jsonify(error="email or phone is required"), 400, cors
    if not _add_lead(ws, f, "Webhook"):
        return jsonify(error="workspace is at capacity"), 403, cors
    return jsonify(ok=True), 200, cors


# ----------------------------------------------------------------- feedback (goes to you, with context)
@route("/pmf", methods=["POST"])
def pmf_answer():
    a = request.form.get("a", "")
    if a in ("very", "somewhat", "not"):
        ins("feedback", dict(workspace_id=W(), user_id=g.user["id"], kind="pmf", page="/app", message="How disappointed if Debut went away? " + a))
        flash("Thanks, that really helps us.")
    return redirect(url_for("dashboard"))


FEEDBACK_KINDS = ["idea", "problem", "question", "praise"]


@route("/feedback", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def feedback():
    page = S.clean_text(request.values.get("page") or request.args.get("from"), 200)
    if request.method == "POST":
        msg, kind = S.clean_text(request.form.get("message"), 3000), request.form.get("kind", "idea")
        if not msg:
            flash("Write a message first, then hit send.")
            return render_template("feedback.html", page=page, kinds=FEEDBACK_KINDS), 400
        kind = kind if kind in FEEDBACK_KINDS else "idea"
        fid = ins("feedback", dict(workspace_id=W(), user_id=g.user["id"], kind=kind, page=page, message=msg))
        S.audit("feedback", f"#{fid} {kind}")
        S.send_email(C.SUPPORT_EMAIL, f"[{C.APP_NAME} feedback: {kind}] from {g.user['email']}",
                     f"{msg}\n\n---\nUser: {g.user['name']} <{g.user['email']}> (role {g.role})\nWorkspace: {g.ws['name']} (#{W()}, plan {g.plan_key}, industry {g.ws['industry']})\nPage: {page}\n")
        flash("Thank you! Your feedback reached us. We read every message.")
        return redirect(page if page.startswith("/") and not page.startswith("//") else url_for("dashboard"))
    return render_template("feedback.html", page=page, kinds=FEEDBACK_KINDS)


# ----------------------------------------------------------------- installable app (PWA)
@route("/manifest.webmanifest")
def manifest():
    icons = [dict(src=url_for("static", filename="icons/icon-192.png"), sizes="192x192", type="image/png", purpose="any"),
             dict(src=url_for("static", filename="icons/icon-512.png"), sizes="512x512", type="image/png", purpose="any"),
             dict(src=url_for("static", filename="icons/maskable-512.png"), sizes="512x512", type="image/png", purpose="maskable")]
    return Response(json.dumps(dict(name=C.APP_NAME, short_name=C.APP_NAME[:12], start_url="/app", scope="/", display="standalone", display_override=["standalone", "minimal-ui"], orientation="any", background_color="#faf8ff", theme_color="#6a3df0", icons=icons,
                                     description="Plan, post, launch and report your marketing in one place.", categories=["business", "productivity"],
                                     screenshots=[dict(src=url_for("static", filename="icons/shot-wide.png"), sizes="1280x800", type="image/png", form_factor="wide", label="Home"), dict(src=url_for("static", filename="icons/shot-narrow.png"), sizes="390x844", type="image/png", form_factor="narrow", label="Home on phone")],
                                     shortcuts=[dict(name="Calendar", url="/calendar"), dict(name="Tasks", url="/m/tasks"), dict(name="Idk what to do", url="/whatnow")])),
                    mimetype="application/manifest+json")


def _sw_cache_version():
    """A cache name that changes whenever static/style.css changes, so every deploy that touches the stylesheet
    automatically invalidates the installed service worker's old cached copy (see SW_JS below) — without this,
    a browser that already has the old service worker installed would keep serving a stale style.css forever,
    since the worker's own script (and so its cache name) would otherwise never change between deploys."""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "style.css")
        with open(p, "rb") as f:
            return "gtm-" + hashlib.md5(f.read()).hexdigest()[:10]
    except OSError:
        return "gtm-v1"


SW_JS = """const V='%s';
self.addEventListener('push',e=>{let d={};try{d=e.data.json()}catch(x){}e.waitUntil(self.registration.showNotification(d.title||'Debut',{body:d.body||'',data:{url:d.url||'/app'},icon:'/static/icons/apple-touch-icon.png',badge:'/static/icons/apple-touch-icon.png'}));});
self.addEventListener('notificationclick',e=>{e.notification.close();const u=(e.notification.data&&e.notification.data.url)||'/app';e.waitUntil(clients.matchAll({type:'window'}).then(l=>{for(const c of l){if('focus' in c){c.navigate(u);return c.focus()}}return clients.openWindow(u)}));});
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(['/static/style.css','/offline'])));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET')return;const u=new URL(r.url);if(u.origin!==location.origin)return;
if(u.pathname.startsWith('/static/')){e.respondWith(caches.match(r).then(m=>m||fetch(r).then(x=>{const cp=x.clone();caches.open(V).then(c=>c.put(r,cp));return x;})));return;}
if(r.mode==='navigate'){e.respondWith(fetch(r).catch(()=>caches.match('/offline')));}});
""" % _sw_cache_version()


@route("/sw.js")
def service_worker():
    """Only static assets and an offline page are cached: signed-in pages and data are never stored on the device."""
    return Response(SW_JS, mimetype="application/javascript", headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@route("/push/key")
def push_key():
    try:
        return jsonify(key=S.vapid()[0])
    except Exception:
        return jsonify(key="")


@route("/push/subscribe", methods=["POST"])
def push_subscribe():
    d = request.get_json(silent=True) or {}
    k = d.get("keys") or {}
    ep, p256, au = str(d.get("endpoint", ""))[:600], str(k.get("p256dh", ""))[:200], str(k.get("auth", ""))[:100]
    if not (ep.startswith("https://") and p256 and au):
        abort(400)
    ex("DELETE FROM push_subs WHERE endpoint=?", (ep,))
    ins("push_subs", dict(user_id=g.user["id"], endpoint=ep, p256dh=p256, auth=au))
    return jsonify(ok=True)


@route("/push/test", methods=["POST"])
def push_test():
    n = q("SELECT COUNT(*) c FROM push_subs WHERE user_id=?", (g.user["id"],), one=True)["c"]
    if not n:
        return jsonify(ok=False, error="Turn on push on this device first."), 400
    S.send_push(g.user["id"], "✅ Push works. This is how Debut will ping you.", "/notifications")
    return jsonify(ok=True, devices=n)


@route("/push/unsubscribe", methods=["POST"])
def push_unsubscribe():
    ep = str((request.get_json(silent=True) or {}).get("endpoint", ""))
    ex("DELETE FROM push_subs WHERE endpoint=? AND user_id=?", (ep, g.user["id"]))
    return jsonify(ok=True)


@route("/offline")
def offline():
    return render_template("error.html", code="📡", msg="You're offline. Reconnect to keep working; nothing you saved is lost.", bare=True)


# ----------------------------------------------------------------- client portal: clients see only their own work
STAFF_PREVIEW = ("owner", "admin", "lead", "manager")


def _portal_client():
    """Whose portal this is: a client's own, or (staff preview) the ?client= name."""
    if g.role == "client":
        m = q("SELECT client_name FROM memberships WHERE workspace_id=? AND user_id=?", (W(), g.user["id"]), one=True)
        return (m["client_name"] or "").strip()
    if g.role in STAFF_PREVIEW:
        return S.clean_text(request.args.get("client") or request.form.get("client"), 120)
    abort(403)


def _portal_item(iid, cn):
    it = q("SELECT * FROM content_items WHERE id=? AND workspace_id=?", (iid, W()), one=True) or abort(404)
    if not cn or (it["client"] or "").strip().lower() != cn.lower():
        abort(404)
    return it


def _tell_team(kind, msg, iid, item):
    """Notify the item's owner and every approver when a client acts."""
    seen = set()
    link = url_for("m_edit", key="content_items", rid=iid)
    owner = S.find_member(W(), item["owner"])
    for mem in ([owner] if owner else []) + [x for x in S.members(W()) if x["role"] in ("owner", "admin", "lead", "manager")]:
        if mem["uid"] not in seen:
            seen.add(mem["uid"])
            S.notify(W(), mem["uid"], kind, msg, link)


@route("/portal")
def portal():
    cn = _portal_client()
    if not cn:                                   # staff without a client chosen: pick one
        names = sorted({(r["client"] or "").strip() for k in ("content_items", "campaigns") for r in q(f"SELECT DISTINCT client FROM {k} WHERE workspace_id=?", (W(),)) if (r["client"] or "").strip()}
                       | {(m["client_name"] or "").strip() for m in q("SELECT client_name FROM memberships WHERE workspace_id=? AND role='client'", (W(),))})
        return render_template("portal.html", cn="", names=names, preview=True)
    w, today = W(), S.today().isoformat()
    items = q("SELECT * FROM content_items WHERE workspace_id=? AND LOWER(client)=LOWER(?) ORDER BY publish_date, id", (w, cn))
    camps = q("SELECT * FROM campaigns WHERE workspace_id=? AND LOWER(client)=LOWER(?) ORDER BY id DESC", (w, cn))
    return render_template("portal.html", cn=cn, names=[], preview=g.role != "client",
                           review=[i for i in items if i["status"] == "Review"],
                           upcoming=[i for i in items if i["status"] in ("Approved", "Scheduled") and (i["publish_date"] or "") >= today],
                           published=[i for i in items if i["status"] == "Published"][-10:][::-1], camps=camps, total=len(items))


@route("/portal/item/<int:iid>")
def portal_item(iid):
    cn = _portal_client()
    it = _portal_item(iid, cn)
    thread = q("SELECT c.*, u.name AS uname FROM comments c LEFT JOIN users u ON u.id=c.user_id WHERE c.workspace_id=? AND c.module='content_items' AND c.record_id=? AND c.client_visible=1 ORDER BY c.id", (W(), iid))
    return render_template("portal_item.html", it=it, cn=cn, thread=thread, preview=g.role != "client")


@route("/portal/item/<int:iid>/decide", methods=["POST"])
def portal_decide(iid):
    if g.role != "client":
        abort(403)
    cn = _portal_client()
    it = _portal_item(iid, cn)
    action, note = request.form.get("action"), S.clean_text(request.form.get("comment"), 2000)
    if it["status"] != "Review" or action not in ("approve", "changes"):
        flash("This item is not waiting for your review.")
        return redirect(url_for("portal_item", iid=iid))
    if action == "changes" and not note:
        flash("Tell us what to change and we will take it from there.")
        return redirect(url_for("portal_item", iid=iid))
    if note:
        ins("comments", dict(workspace_id=W(), module="content_items", record_id=iid, user_id=g.user["id"], body=note, client_visible=1))
    who = g.user["name"] or g.user["email"]
    if action == "approve":
        ex("UPDATE content_items SET status='Approved' WHERE id=? AND workspace_id=?", (iid, W()))
        S.audit("client_approved", f"content_items#{iid} by {who}")
        _tell_team("client_approved", f"{cn} approved: {it['title']}", iid, it)
        flash("Approved. Thank you! The team has been notified.")
    else:
        ex("UPDATE content_items SET status='In progress' WHERE id=? AND workspace_id=?", (iid, W()))
        S.audit("client_changes", f"content_items#{iid} by {who}")
        _tell_team("client_changes", f"{cn} requested changes on {it['title']}: {note[:80]}", iid, it)
        flash("Thanks. We've sent your changes to the team.")
    return redirect(url_for("portal"))


@route("/portal/item/<int:iid>/comment", methods=["POST"])
def portal_comment(iid):
    if g.role != "client":
        abort(403)
    it = _portal_item(iid, _portal_client())
    note = S.clean_text(request.form.get("comment"), 2000)
    if note:
        ins("comments", dict(workspace_id=W(), module="content_items", record_id=iid, user_id=g.user["id"], body=note, client_visible=1))
        S.audit("client_comment", f"content_items#{iid}")
        _tell_team("client_comment", f"{g.user['name'] or g.user['email']} ({it['client']}) commented on {it['title']}: {note[:80]}", iid, it)
    return redirect(url_for("portal_item", iid=iid) + "#thread")


# ----------------------------------------------------------------- Market Pulse: live signals for this workspace
PULSE_ROLES = ("owner", "admin", "lead", "manager")
HOLIDAY_COUNTRIES = [("IN", "India"), ("US", "United States"), ("GB", "United Kingdom"), ("AE", "United Arab Emirates"), ("SG", "Singapore"), ("AU", "Australia"), ("CA", "Canada")]


@route("/pulse")
def pulse_page():
    data = S.latest_pulse(W())
    age = S.pulse_age_minutes(data) if data else None
    watch = S.pulse_watch(W(), g.plan["watch"])
    watch_rows = q("SELECT * FROM watchlist WHERE workspace_id=? ORDER BY id DESC", (W(),))
    return render_template("pulse.html", data=data, age=age, watch=watch, watch_rows=watch_rows, limit=g.plan["watch"], can_refresh=g.role in PULSE_ROLES and g.role != "viewer",
                           wait=max(0, C.PULSE_MIN_REFRESH_MINUTES - int(age)) if age is not None else 0, stale=age is None or age > C.PULSE_CACHE_MINUTES,
                           yt=bool(C.YOUTUBE_API_KEY), provider=C.NEWS_PROVIDER, countries=HOLIDAY_COUNTRIES, year=S.today().year, ai=bool(C.ANTHROPIC_API_KEY), cost=C.AI_COST.get("pulse_brief", 2))


@route("/pulse/refresh", methods=["POST"])
@limiter.limit("20 per hour")
@S.roles(*PULSE_ROLES)
def pulse_refresh():
    data = S.latest_pulse(W())
    if data and S.pulse_age_minutes(data) < C.PULSE_MIN_REFRESH_MINUTES:
        flash(f"Market Pulse was refreshed a moment ago. Try again in {C.PULSE_MIN_REFRESH_MINUTES} minutes.")
        return redirect(url_for("pulse_page"))
    if not S.pulse_watch(W(), g.plan["watch"]):
        flash("Add something to track first (see the watchlist below).")
        return redirect(url_for("pulse_page"))
    fresh = S.run_pulse(W(), g.ws["industry"], g.plan)
    S.audit("pulse_refresh", f"{sum(len(x['items']) for x in fresh['groups'])} items")
    flash("Market Pulse refreshed. Fresh headlines are in 📡" + (f" {len(fresh['errors'])} source(s) had a problem: see the notes at the bottom." if fresh["errors"] else ""))
    return redirect(url_for("pulse_page"))


@route("/pulse/watch/add", methods=["POST"])
@S.roles(*PULSE_ROLES)
def pulse_watch_add():
    """Add a source to track, right from the Market Pulse page itself - no separate Watchlist tab to find."""
    term = S.clean_text(request.form.get("term"), 120)
    if not term:
        flash("Enter a keyword, brand, competitor or subreddit to track.")
        return redirect(url_for("pulse_page"))
    if q("SELECT COUNT(*) c FROM watchlist WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["watch"]:
        flash(f"Your {g.plan['name']} plan can track {g.plan['watch']} items in Market Pulse. Remove one" + (" or upgrade:" + C.upsell(g.plan_key, "watch", "watch", "topics") if C.next_plan(g.plan_key) else "."))
        return redirect(url_for("pulse_page"))
    typ = request.form.get("type", "Keyword")
    region = request.form.get("region", "India")
    ins("watchlist", dict(workspace_id=W(), term=term, type=typ if typ in ("Keyword", "Competitor", "Brand", "Subreddit") else "Keyword",
                           region=region if region in ("India", "Global", "Both") else "India", notes=""))
    S.audit("create", "watchlist")
    flash(f"Now tracking “{term}”.")
    return redirect(url_for("pulse_page"))


@route("/pulse/watch/<int:wid>/remove", methods=["POST"])
@S.roles(*PULSE_ROLES)
def pulse_watch_remove(wid):
    ex("DELETE FROM watchlist WHERE id=? AND workspace_id=?", (wid, W()))
    S.audit("delete", f"watchlist#{wid}")
    return redirect(url_for("pulse_page"))


@route("/pulse/holidays", methods=["POST"])
@limiter.limit("10 per hour")
@S.roles(*PULSE_ROLES)
def pulse_holidays():
    """Add a country's public holidays to Key Dates (live from the Nager.Date public API)."""
    import pulse
    country, year = (request.form.get("country") or "").upper(), S.to_int(request.form.get("year"), 0)
    if country not in dict(HOLIDAY_COUNTRIES) or not (2020 <= year <= 2100):
        abort(400)
    try:
        days = pulse.public_holidays(country, year)
    except Exception:
        flash("Could not fetch holidays right now. That country might not be covered, or try again in a bit.")
        return redirect(url_for("pulse_page"))
    have = [(S.date_name_key(r["name"]), r["date"]) for r in q("SELECT name, date FROM key_dates WHERE workspace_id=?", (W(),))]
    n = 0
    for h in days[:60]:
        nm, dte = S.clean_text(h["name"], 120), S.clean_text(h["date"], 10)
        if nm and re.match(r"^\d{4}-\d{2}-\d{2}$", dte) and not S.date_seen(have, nm, dte):      # "Christmas" and "Christmas Day" are one date
            ins("key_dates", dict(workspace_id=W(), name=nm, date=dte, kind="Festival"))
            have.append((S.date_name_key(nm), dte))
            n += 1
    S.audit("holidays_import", f"{country} {year} x{n}")
    flash(f"Added {n} public holiday(s) for {dict(HOLIDAY_COUNTRIES)[country]} {year} to your Key Dates." if n else "Those holidays are already in your Key Dates.")
    return redirect(url_for("pulse_page"))


@route("/api/pulse/brief", methods=["POST"])
@limiter.limit("5 per minute;30 per hour")
@S.roles(*PULSE_ROLES)
def pulse_brief():
    """AI reads this week's live items and writes an actionable brief, citing item numbers."""
    data = S.latest_pulse(W())
    if not data or not any(g_["items"] for g_ in data["groups"]):
        return jsonify(error="Refresh Market Pulse first so there is something to analyse."), 400
    cost = C.AI_COST.get("pulse_brief", 2)
    err, used, limit = ai_guard(cost)
    if err:
        return err
    items, n = [], 0
    for grp in data["groups"]:
        for it in grp["items"][:6]:
            n += 1
            if n <= 40:
                items.append(f"[{n}] ({grp['term']}) {it['title']} | {it['source']} | {it['date']} | {it['url']}")
    trends = "; ".join(f"{k}: " + ", ".join(t["term"] for t in v[:8]) for k, v in data.get("trends", {}).items() if v)
    ind = IND.get(g.ws["industry"])
    prompt = "\n".join([f"TASK: Turn this week's live market signals into a practical brief for a {ind['label']} business in India. Use ONLY the numbered items below and cite them like [3]. "
                        "Sections: 1) What is happening (5 bullets). 2) What it means for us. 3) Five opportunities. 4) Three risks or watch-outs. 5) Five content ideas (channel, hook, why now). 6) Three actions for this week. "
                        "If the items are thin or irrelevant, say so plainly instead of stretching them.", f"TRENDING SEARCHES TODAY: {trends or 'not available'}",
                        "RISING WORDS IN HEADLINES: " + ", ".join(t[0] for t in data.get("terms", [])[:10]), "LIVE ITEMS:\n" + "\n".join(items)] + workspace_context())
    try:
        text, _ = claude_call(SYSTEM + "\nINDUSTRY CONTEXT: " + ind["ai_context"], prompt, 3500, False)
    except Exception as e:
        return ai_fail(e)
    ins("ai_usage", dict(workspace_id=W(), user_id=g.user["id"], task="pulse_brief", credits=cost, month=S.month_key()))
    return jsonify(text=text, sources=[], used=used + cost, limit=limit)
