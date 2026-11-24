"""Debut: go-to-market and marketing workspace (multi-tenant SaaS). Run locally: python app.py   Production: gunicorn wsgi:app"""
import re
import logging
import datetime as dt
import os
from jinja2 import ChoiceLoader, FileSystemLoader
from flask import Flask, g, request, session, render_template, redirect, url_for, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import config as C
from modules import HINTS as M_HINTS
from hubs import HUBS, MORE_TABS, PRO_TABS, GROUPS, FOLDED, focus_keys as _hubs_focus
import db as D
import services as S
import industries as IND
import views
from db import q
from extensions import csrf, limiter
from modules import MODULES, MODULE_FEATURE, CREATOR_MODULES
from collections import OrderedDict
from werkzeug.routing import IntegerConverter
from sqlalchemy.exc import DataError, StatementError


class SafeInt(IntegerConverter):
    """URL ints that fit a 32-bit database integer (anything bigger is a 404, not a 500)."""
    def __init__(self, map, **kw):
        kw.setdefault("max", 2**31 - 1)
        super().__init__(map, **kw)

MARKETING = {"features", "templates_gallery", "pricing", "terms", "privacy", "data_deletion", "contact", "refunds", "changelog", "about", "channels_page"}
PUBLIC = {"media", "bio.public", "bio.go", "bio.qr", "bio.review_go", "bio.review_qr", "data_deletion", "cron_morning", "cron_evening", "auth.demo_exit", "about", "channels_page", "healthz", "agency_enquiry", "templates_gallery", "features", "demo", "changelog", "survey.public", "survey.submit", "board_public", "board_public_img", "landing", "pricing", "terms", "privacy", "health", "robots", "static", "auth.login", "auth.login_2fa", "auth.login_pin", "auth.signup", "auth.forgot", "auth.reset",
          "auth.verify", "auth.invite", "apply_form", "billing.webhook", "ics_feed", "lead_form", "lead_hook", "report_public", "manifest", "service_worker", "offline", "unsubscribe", "contact", "refunds", "sitemap", "manual"}
VIEWER_WRITE_OK = {"deb.set_tone", "tm.send", "tm.send_channel", "tm.channel", "tm.new_channel", "tm.react", "tm.pin", "tm.delete_msg", "tm.share", "tm.cancel", "tm.access_request", "auth.logout", "auth.switch_ws", "admin.exit_support", "admin.support", "ws.account_profile", "ws.account_password", "ws.account_verify",
                   "ws.twofa_enable", "ws.twofa_disable", "ws.account_digest", "comment_add", "comment_delete", "notifications_read", "feedback", "ws.onboarded"}
CLIENT_OK = {"push_key", "push_subscribe", "push_unsubscribe", "push_test", "dashboard", "portal", "portal_item", "portal_decide", "portal_comment", "notifications", "notifications_recent", "notifications_read", "notification_open", "feedback", "help_centre", "auth.logout", "auth.switch_ws",
             "ws.account", "ws.account_profile", "ws.account_password", "ws.account_verify", "ws.twofa", "ws.twofa_enable", "ws.twofa_disable", "ws.onboarded"}
CREATOR_OK = {"deb.wrapped", "deb.quick", "deb.set_tone", "tm.approvals", "tm.idea_submit", "tm.chat", "tm.thread", "tm.send", "tm.send_channel", "tm.channel", "tm.new_channel", "tm.react", "tm.pin", "tm.delete_msg", "tm.share", "tm.cancel", "tm.access_request", "ideas_schedule", "dashboard", "m_list", "m_new", "m_edit", "m_save", "kanban", "m_status", "calendar_view", "search", "moodboards", "board_view", "media", "ideas",
              "auth.logout", "auth.switch_ws", "ws.account", "ws.account_profile", "ws.account_password", "ws.account_verify",
              "ws.twofa", "ws.twofa_enable", "ws.twofa_disable", "ws.account_digest", "comment_add", "comment_delete", "presence", "push_key", "push_subscribe", "push_unsubscribe", "push_test", "kudos", "kudos_send", "react", "presence", "push_key", "push_subscribe", "push_unsubscribe", "notifications", "notifications_read", "notification_open", "feedback", "help_centre", "ws.onboarded", "board_new", "board_add", "board_photos", "board_photo_add", "board_item_delete", "board_delete", "board_item_place", "board_item_edit", "board_item_replace_image", "board_arrange", "board_sample"}
FEATURE_EP = {"content_ops": "content_ops", "order_match": "content_ops", "order_assign": "content_ops", "discover": "influencers", "outreach": "influencers",
              "influencer_contacted": "influencers", "event_checklist": "promo_events", "team_hub": "group", "analytics": "analytics", "analytics_import": "analytics", "ai_studio": "ai", "api_ai": "ai"}


import taglines as _tg


def _asset_v():
    """Version stamp for the css links, so a redeploy is picked up straight away instead of the browser reusing its cached copy."""
    try:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        return int(max(os.path.getmtime(os.path.join(base, f)) for f in ("style.css", "polish.css", "identity.css", "pop.css", "bold.css")))
    except OSError:
        return 0


# Pages a visitor sees before signing in. Only these (and any page shown while logged out) get the line-icon set;
# inside the app the original emoji stay, because that is what the team recognises.
OUTSIDE_PAGES = {"landing", "features", "templates_gallery", "changelog", "pricing"}


_TITLE_EMOJI = re.compile(r'(<h1[^>]*>|<title>)\s*(?:[\u2190-\u2BFF\U0001F000-\U0001FAFF\uFE0F\u200d]+\s*)+')


def create_app(config=None, init=True, database_url=None):
    app = Flask(__name__)
    # The templates are split across templates/part1 and templates/part2 for one dull but real reason:
    # GitHub's web uploader takes at most 100 files at a time, and there are more than 100 of them.
    # Jinja searches both folders, so every render_template("x.html") and {% extends %} is unchanged -
    # a template can sit in either folder, and new ones can go in whichever has room.
    _tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    app.jinja_loader = ChoiceLoader([FileSystemLoader(os.path.join(_tpl, "part1")),
                                     FileSystemLoader(os.path.join(_tpl, "part2")),
                                     FileSystemLoader(_tpl)])
    app.url_map.converters["int"] = SafeInt
    app.config.update(C.FLASK)
    if config:
        app.config.update(config)
    if C.PROD and not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be set when APP_ENV=production")
    if C.PROD:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if C.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=C.SENTRY_DSN, traces_sample_rate=0.1, send_default_pii=False)
        except ImportError:
            logging.getLogger("gtm").warning("SENTRY_DSN set but sentry-sdk not installed")

    D.init_engine(database_url or C.DATABASE_URL)
    if C.PROD and ("127.0.0.1" in C.APP_URL or "localhost" in C.APP_URL):
        app.logger.warning("APP_URL is not set: links in emails and digests will use the development address. Set APP_URL to your site's https address.")
    csrf.init_app(app)
    limiter.init_app(app)
    if init:
        with app.app_context():
            D.init_schema(MODULES)
        S.start_scheduler(app)
    app.teardown_appcontext(D.close_conn)

    from auth import bp as auth_bp
    from billing import bp as billing_bp
    from workspace import bp as ws_bp
    from admin import bp as admin_bp
    from api import bp as api_bp
    from survey import bp as survey_bp
    from studio import bp as studio_bp
    from bio import bp as bio_bp
    from team import bp as team_bp
    from deb import bp as deb_bp
    from social import bp as social_bp
    for b in (auth_bp, billing_bp, ws_bp, admin_bp, api_bp, survey_bp, studio_bp, bio_bp, team_bp, deb_bp, social_bp):
        app.register_blueprint(b)
    views.register(app)

    @app.context_processor
    def _language():
        """The interface language for this workspace, and the t() every template uses."""
        import i18n
        lang = "en"
        try:
            if getattr(g, "ws", None) and "lang" in g.ws.keys():
                lang = g.ws["lang"] or "en"
        except Exception:
            lang = "en"
        return dict(LANG=lang, LANGUAGES=i18n.LANGUAGES, tr=lambda s: i18n.t(s, lang))   # "tr", not "t": views already pass a "t" of their own

    @app.context_processor
    def _publishing():
        """Lets any form ask whether Instagram posting is live for this workspace, and what is queued."""
        def reel_info(content_id, secs=30):
            """The shoot sheet, hooks, pre-publish checks and what this could become next."""
            try:
                import reels as R
                from db import q as _q
                rows = _q("SELECT * FROM content_items WHERE workspace_id=? AND id=?", (g.ws["id"], content_id))
                if not rows:
                    return None
                it = rows[0]
                import learn as L, social as SOC
                return dict(plan=R.shot_list(it["title"], it["copy"] or "", secs), hooks=R.hooks(it["title"]),
                            checks=R.checks(it), nexts=R.repurpose_plan(it),
                            is_video=(it["format"] or "") in ("Reel / Short", "Story"),
                            published=(it["status"] or "") == "Published",
                            rating=L.rating_of(g.ws["id"], content_id), ratings=L.RATINGS,
                            stats=SOC.stats_for(g.ws["id"], content_id))
            except Exception:
                return None

        def pub_info(content_id):
            try:
                import social
                if not getattr(g, "ws", None):
                    return dict(ready=False, jobs=[], when="", why="", where=[])
                when, why = social.best_time(g.ws)
                where = [(r["platform"], social.PLATFORMS.get(r["platform"], r["platform"])) for r in social.accounts(g.ws["id"])] or [("instagram", "Instagram")]
                return dict(ready=bool(social.account(g.ws["id"])), jobs=social.jobs_for(g.ws["id"], content_id), when=when, why=why, where=where)
            except Exception:
                return dict(ready=False, jobs=[], when="", why="", where=[])
        return dict(pub_info=pub_info, reel_info=reel_info)

    @app.before_request
    def guard():
        g.user = g.ws = g.role = None
        g.plan, g.plan_key, g.memberships, g.support = C.PLANS["free"], "free", [], False
        if request.endpoint == "static" or (request.endpoint or "").startswith("api."):   # the API authenticates itself with keys
            return
        uid = session.get("uid")
        if uid:
            user = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
            if user:
                g.user = user
            else:
                session.clear()
        if g.user:
            g.memberships = q("SELECT m.workspace_id AS wid, m.role, w.name FROM memberships m JOIN workspaces w ON w.id=m.workspace_id WHERE m.user_id=? ORDER BY m.id", (uid,))
            pick = next((m for m in g.memberships if m["wid"] == session.get("ws")), g.memberships[0] if g.memberships else None)
            if pick:
                g.ws = q("SELECT * FROM workspaces WHERE id=?", (pick["wid"],), one=True)
                g.role, g.plan_key = pick["role"], S.plan_key(g.ws)
                g.plan = C.PLANS[g.plan_key]
                session["ws"] = pick["wid"]
            sup = session.get("support_ws")
            if sup and S.is_platform_admin(g.user):      # platform owner's read-only support view of any workspace
                ws = q("SELECT * FROM workspaces WHERE id=?", (sup,), one=True)
                if ws:
                    g.ws, g.role, g.support = ws, "viewer", True
                    g.plan_key = S.plan_key(ws)
                    g.plan = C.PLANS[g.plan_key]
        ep = request.endpoint
        if C.MAINTENANCE and ep not in ("health", "billing.webhook", "manifest", "service_worker", "auth.login", "auth.login_2fa", "auth.login_pin", "auth.logout") and not S.is_platform_admin(g.user):
            return render_template("error.html", code=503, msg=f"{C.APP_NAME} is being updated and will be back in a few minutes. Your data is safe.", bare=True), 503
        if ep is None or ep in PUBLIC or ep == "auth.logout":
            return
        if ep.startswith("static"):
            return
        if not g.user:
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")) if request.method == "GET" else url_for("auth.login"))
        if not g.ws:
            return None if ep in ("auth.new_workspace", "auth.switch_ws") else redirect(url_for("auth.new_workspace"))
        write = request.method in ("POST", "PUT", "PATCH", "DELETE")
        key = (request.view_args or {}).get("key")
        if g.support and write and ep not in ("admin.exit_support", "admin.support", "auth.logout", "auth.switch_ws"):
            return _forbidden()
        if write and ep != "auth.logout" and (g.user["email"] or "").endswith("@demo.debut.invalid"):
            if ep == "studio.draft":
                return None                   # the draft maker is free (templates only for demo visitors) and saves nothing
            if ep == "presence":
                return ("", 204)          # silent "who is viewing" ping: not a user action, so no nudge and no demo_blocked noise
            # A fetch that expects JSON and gets an HTML page throws, and the person sees a
            # made-up "the internet ate it" error that makes a working product look broken.
            # Anything called from script gets the real reason, in JSON, in words they can act on.
            # Listing the endpoints one by one meant every new fetch had to remember to join the
            # list, and the ones that forgot showed the person a made-up error. A request that
            # sent or asked for JSON is script, whatever it is called, and gets JSON back.
            wants_json = (ep in ("api_ask", "api_ai") or (request.path or "").startswith("/api/")
                          or request.is_json or request.accept_mimetypes.best == "application/json"
                          or request.headers.get("X-Requested-With") == "fetch")
            if wants_json:
                if ep in ("api_ask", "api_ai"):
                    return jsonify(error="Deb can't chat freely in the demo — that part needs an account. "
                                         "Sign up free and ask her anything. The buttons below work right now, "
                                         "from this workspace's own calendar.", demo=True), 403
                return jsonify(error="This is a read-only demo, so that one is switched off here. "
                                     "Sign up free and it works on your own workspace.", demo=True), 403
            try:
                S.audit("demo_blocked", ep or "", wid=g.ws["id"], uid=g.user["id"])      # counted, so we can see which locked buttons people reach for
            except Exception:
                pass
            return render_template("demo_nudge.html"), 403
        if g.role == "viewer" and write and ep not in VIEWER_WRITE_OK:
            return _forbidden()
        if g.role == "creator" and (ep not in CREATOR_OK or (key and key not in CREATOR_MODULES)):
            return _forbidden()
        if g.role == "client":     # portal clients can only reach their own portal, notifications, feedback and their account
            if not g.plan["clients"]:
                return render_template("error.html", code=403, msg="The client portal isn't included in this workspace's current plan. Please contact your account team."), 403
            if ep not in CLIENT_OK:
                return _forbidden()
        if not g.support and ep not in ("auth.logout", "auth.switch_ws") and g.role not in ("owner", "client") and \
                q("SELECT COUNT(*) c FROM memberships WHERE workspace_id=? AND role!='client'", (g.ws["id"],), one=True)["c"] > g.plan["seats"]:
            return render_template("error.html", code=403, msg=f"This workspace has more members than the {g.plan['name']} plan allows. Ask the workspace owner to upgrade or remove members."), 403
        feat = FEATURE_EP.get(ep) or MODULE_FEATURE.get(key)
        if feat and feat not in g.plan["features"]:
            need_key = next((k for k in C.PLAN_ORDER if k in C.PAID_PLANS and feat in C.PLANS[k]["features"]), "")
            need = C.PLANS[need_key]["name"] if need_key else "a paid"
            return render_template("upgrade.html", feature=feat, need=need, need_key=need_key, pitch=C.FEATURE_PITCH.get(feat)), 403
        import team as _team
        _lk = _team.blocked(ep, key)
        if _lk and request.method in ("GET", "POST") and not ep.startswith("tm."):
            return render_template("locked.html", pk=_lk, label=dict(_team.lockable()).get(_lk, "This page"), asked=bool(q("SELECT 1 FROM page_access WHERE workspace_id=? AND page_key=? AND user_id=? AND status='pending'", (g.ws["id"], _lk, g.user["id"]), one=True))), 403

    def _forbidden():
        if request.path.startswith("/api/"):
            return jsonify(error="You don't have permission to do that."), 403
        return render_template("error.html", code=403, msg="You don't have permission to do that."), 403

    @app.url_defaults
    def _bust_static(endpoint, values):
        """Append ?v=<file modified time> to static files so browsers never keep an old stylesheet after an update."""
        fn = values.get("filename")
        if endpoint == "static" and fn and "v" not in values:
            try:
                values["v"] = int(os.stat(os.path.join(app.static_folder, fn)).st_mtime)
            except OSError:
                pass

    app.jinja_env.globals["TAGS"] = _tg.TAGS
    import palettes as _pl
    app.jinja_env.globals["VIBE_PALS"] = _pl.PALS
    import voice as _voice
    app.jinja_env.globals["tn"] = _voice.tn
    app.jinja_env.globals["TONES"] = _voice.TONES
    app.jinja_env.globals["tone_now"] = lambda: _voice.tone_of(g.get("user"))
    from hubs import FOCUS as _FOCUS
    app.jinja_env.globals["FOCUS"] = _FOCUS
    import palettes as _pal
    app.jinja_env.globals["PALS"] = _pal.PALS

    def _nice_day(iso):
        """'2026-11-15' -> 'tomorrow' / 'Mon 16 Nov': people read days, not ISO dates."""
        try:
            d = dt.date.fromisoformat(str(iso)[:10])
        except ValueError:
            return iso
        n = (d - S.today()).days
        return {0: "today", 1: "tomorrow", -1: "yesterday"}.get(n, d.strftime("%a %d %b").replace(" 0", " "))
    app.jinja_env.filters["nice_day"] = _nice_day

    def _inr(v, short=False):
        """₹1,20,000 (Indian grouping). short=True gives 1.2L / 3.4Cr for tight tiles."""
        try:
            n = float(v or 0)
        except (TypeError, ValueError):
            return "₹0"
        neg, n = n < 0, abs(n)
        if short and n >= 10000000:
            t = f"{n / 10000000:.1f}".rstrip("0").rstrip(".") + "Cr"
        elif short and n >= 100000:
            t = f"{n / 100000:.1f}".rstrip("0").rstrip(".") + "L"
        elif short and n >= 10000:
            t = f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k"
        else:
            s = f"{int(round(n))}"
            if len(s) > 3:
                head, tail = s[:-3], s[-3:]
                parts = []
                while len(head) > 2:
                    parts.insert(0, head[-2:])
                    head = head[:-2]
                if head:
                    parts.insert(0, head)
                s = ",".join(parts + [tail])
            t = s
        return ("-" if neg else "") + "₹" + t
    app.jinja_env.filters["inr"] = _inr
    _PLAIN = {"roas": "Ad return (ROAS)", "cac": "Cost per customer (CAC)", "aov": "Average order value (AOV)", "ltv": "Lifetime value (LTV)", "ctr": "Click rate (CTR)",
              "cpm": "Cost per 1,000 views (CPM)", "cpl": "Cost per lead (CPL)", "cpc": "Cost per click (CPC)", "mrr": "Monthly recurring revenue (MRR)", "arr": "Yearly recurring revenue (ARR)",
              "return / rto rate": "Returns rate (RTO)", "rto rate": "Returns rate (RTO)", "rto": "Returns (RTO)", "nps": "Customer happiness score (NPS)", "churn": "Customers lost (churn)",
              "churn %": "Customers lost % (churn)", "ugc": "Customer-made content (UGC)", "seo": "Search ranking (SEO)"}
    app.jinja_env.filters["plain"] = lambda s: _PLAIN.get(str(s or "").strip().lower(), s)

    @app.context_processor
    def ctx():
        d = dict(ASSET_V=_asset_v(), HINTS=M_HINTS, C=C, S_app_url=S.app_url, user=g.get("user"), ws=g.get("ws"), role=g.get("role"), plan=g.get("plan"), memberships=g.get("memberships", []), media=S.media_url, NAV=OrderedDict(), bare=False, today=S.today().isoformat(), trial_left=None, plan_key="free", on_free=False, lapsed=False, unread=0, is_admin=False, admin_needs_2fa=False, brand=None, support=g.get("support", False), TEAM_MANAGERS=C.TEAM_MANAGERS, industry=None, ESSENTIALS=[], ESS_LV={}, ESS_TEAM=[], TOOLS=[], HUBS=[], HUB_CUR=None, HUB_TABS=[], NAV_TAG={})
        if g.get("user") and g.get("ws"):
            d["trial_left"] = S.trial_days_left(g.ws)
            d["plan_key"] = g.plan_key
            d["industry"] = IND.get(g.ws["industry"])
            d["unread"] = S.unread_count(g.user["id"], g.ws["id"])
            d["chat_unread"], d["apr_n"] = 0, 0
            if g.role not in (None, "client"):
                try:
                    import team as _t
                    d["chat_unread"] = _t.unread_total()
                    if g.role in _t.APPROVERS:
                        d["apr_n"] = q("SELECT COUNT(*) c FROM idea_requests WHERE workspace_id=? AND status='pending'", (g.ws["id"],), one=True)["c"] + q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status='Review'", (g.ws["id"],), one=True)["c"]
                        if g.role in C.TEAM_MANAGERS:
                            d["apr_n"] += q("SELECT COUNT(*) c FROM page_access WHERE workspace_id=? AND status='pending'", (g.ws["id"],), one=True)["c"]
                except Exception:
                    pass
            d["brand"] = S.brand_shades(g.ws)
            if g.role == "client":                      # a client sees their own brand colours and logo in their portal
                try:
                    _cm = q("SELECT client_name FROM memberships WHERE workspace_id=? AND user_id=?", (g.ws["id"], g.user["id"]), one=True)
                    _cr = q("SELECT brand_color, logo_url FROM clients WHERE workspace_id=? AND LOWER(name)=LOWER(?)", (g.ws["id"], (_cm["client_name"] or "").strip()), one=True) if _cm else None
                    if _cr and (_cr["brand_color"] or "").startswith("#"):
                        d["brand"] = S.hex_shades(_cr["brand_color"], "")
                    if _cr and _cr["logo_url"]:
                        d["ws"] = dict(g.ws, logo_url=_cr["logo_url"])
                except Exception:
                    pass
            d["is_admin"] = S.is_platform_admin(g.user)
            d["admin_needs_2fa"] = bool(g.user["email_verified"]) and g.user["email"] in C.ADMIN_EMAILS and not d["is_admin"]
            d["on_free"] = g.plan_key == "free"
            d["lapsed"] = g.plan_key == "free" and g.ws["plan"] != "free"
            groups = OrderedDict([("Strategy", []), ("Content", []), ("Campaigns", []), ("Promotions & Events", []), ("Content Ops", []), ("Growth", []), ("Intelligence", [])])
            special = {"Strategy": [("Launch deck", "studio.launch_deck", "🎁")], "Content": [("Calendar", "calendar_view", "📅"), ("Create studio", "studio.studio", "🎬"), ("Instagram grid", "studio.grid", "🧩"), ("Get leads from Instagram", "bio.edit", "🔗"), ("Mood Boards", "moodboards", "🖼️"), ("Idea Bank", "ideas", "💡")],
                       "Campaigns": [("Discover Influencers", "discover", "🔭"), ("Trackable links (UTM)", "utm", "🏷️")],
                       "Content Ops": [("Ops Dashboard", "content_ops", "📊")], "Growth": [("Analytics", "analytics", "📈")],
                       "Intelligence": [("Live news (Market Pulse)", "pulse_page", "📡"), ("AI Studio", "ai_studio", "🤖")]}
            feat_of = {"content_ops": "content_ops", "discover": "influencers", "analytics": "analytics", "ai_studio": "ai"}
            creator = g.role == "creator"
            lock = lambda f: " 🔒" if (f and f not in g.plan["features"]) else ""
            for grp, items in special.items():
                for label, ep, icon in items:
                    if creator and ep not in ("calendar_view", "moodboards", "ideas", "studio.studio"):
                        continue
                    groups[grp].append((f"{icon} {label}{lock(feat_of.get(ep))}", url_for(ep)))
            for k, m in MODULES.items():
                if k in ("utm_links", "watchlist") or (creator and k not in CREATOR_MODULES):
                    continue
                if k in IND.MODULE_INDUSTRIES and g.ws["industry"] not in IND.MODULE_INDUSTRIES[k]:
                    continue
                groups[m["group"]].append((f"{m['icon']} {m['title']}{lock(MODULE_FEATURE.get(k))}", url_for("m_list", key=k)))
            # Calendar and Content Items belong together (one shows the other's dates), so sit them side by side
            cal_href, ci_href = url_for("calendar_view"), url_for("m_list", key="content_items")
            cal_i = next((i for i, x in enumerate(groups["Content"]) if x[1] == cal_href), None)
            ci_i = next((i for i, x in enumerate(groups["Content"]) if x[1] == ci_href), None)
            if cal_i is not None and ci_i is not None:
                groups["Content"].insert(cal_i + 1, groups["Content"].pop(ci_i))
            d["NAV"] = OrderedDict((k, v) for k, v in groups.items() if v)
            d["NAV_TAG"] = {"Strategy": "plan & position", "Content": "make & schedule", "Campaigns": "launch & reach", "Promotions & Events": "sales, drops, events", "Content Ops": "creators & invoices", "Growth": "results & reports", "Intelligence": "news & AI"}
            # a short, always-visible list of the pages people use every day; everything else is found through the search bar / "Find any tool"
            _all = {h: lbl for items in d["NAV"].values() for lbl, h in items}
            _ess = [url_for(x) for x in ("calendar_view", "moodboards")] + [url_for("m_list", key=k) for k in ("content_items", "tasks", "campaigns", "leads")] + [url_for("ai_studio")]
            d["ESSENTIALS"] = [(_all[h], h) for h in _ess if h in _all]
            # sidebar size: 1 = Basics (the four everyday pages), 2 = Daily (all seven essentials), 3 = Team (plus team and client pages)
            _lv1 = {url_for("calendar_view"), url_for("m_list", key="content_items"), url_for("m_list", key="tasks"), url_for("ai_studio")}
            d["ESS_LV"] = {h: (1 if h in _lv1 else 2) for _, h in d["ESSENTIALS"]}
            _team = []
            if g.role in C.TEAM_MANAGERS:
                _team += [("👑 Team hub", url_for("team_hub")), ("👥 Team & roles", url_for("ws.team"))]
            if g.role in ("owner", "admin", "lead", "manager"):
                _team += [("🧾 Clients", url_for("m_list", key="clients")), ("📑 Client report", url_for("report"))]
            d["ESS_TEAM"] = []  # team pages already live under Workspace
            # ---- hubs: the short sidebar. Each hub is tabs over existing pages (see hubs.py) ----
            _label_of = {h: lbl for items in d["NAV"].values() for lbl, h in items}
            _seen, _hubs, _cur, _best, _curtab = set(), [], None, -1, None
            for hb in HUBS:
                tabs = []
                for lbl, ep, kw, extra, _vis in hb["tabs"]:
                    href = url_for(ep, **kw)
                    vis = url_for("m_list", key=kw["key"]) if ep == "kanban" else href
                    if (ep, kw.get("key")) in PRO_TABS and not any((ep, kw.get("key")) in mm for _, mm in GROUPS):      # niche tools live under "More tools"
                        continue
                    if _vis == "camp":     # campaigns, promotions, events and launch plans are one list
                        vis = url_for("m_list", key="campaigns")
                        _seen.update(url_for("m_list", key=k2) for k2 in ("promotions", "events", "gtm_plans"))
                        _vis = None
                    if _vis == "hid":      # reachable from a button on another tab, so it is not shown as a tab of its own
                        _seen.add(vis)
                        continue
                    if _vis == "mgr":      # team pages: owners, admins and leads
                        if g.role not in C.TEAM_MANAGERS:
                            continue
                    elif _vis == "nc":     # everyone except portal clients
                        if g.role == "client":
                            continue
                    elif _vis == "rep":    # the client report: everyone who reports, not creators or clients
                        if g.role in ("creator", "client", None):
                            continue
                    elif vis not in _label_of:
                        continue
                    _seen.add(vis)
                    path = href.split("?")[0]
                    tabs.append(dict(ek=(ep, kw.get("key")), more=(ep, kw.get("key")) in MORE_TABS, label=lbl + (" 🔒" if (_label_of.get(vis, "").endswith("🔒") or (ep == "team_hub" and "group" not in g.plan["features"])) else ""), href=href, paths=[path] + extra, on=False))
                for glabel, members in GROUPS:      # one tab per kind of page; a small switch moves between the pages
                    have = [t for m in members for t in tabs if t["ek"] == m]
                    if len(have) > 1:
                        rep = have[0]
                        rep["subs"] = [dict(label=t["label"], href=t["href"], paths=t["paths"]) for t in have]
                        rep["paths"] = [p for t in have for p in t["paths"]]
                        rep["label"], rep["more"] = glabel, all(t["more"] for t in have)
                        tabs = [t for t in tabs if t is rep or t not in have]
                if tabs:
                    _hubs.append(dict(key=hb["key"], icon=hb["icon"], label=hb["label"], lv=hb["lv"], href=tabs[0]["href"], tabs=tabs, on=False))
            _fk, _show_more = _hubs_focus(g.user["focus"] if g.user and "focus" in g.user.keys() else "")
            d["HUBS_ALL"] = [(hb["key"], hb["icon"], hb["label"]) for hb in _hubs]
            d["MENU_SEL"] = sorted(_fk) if _fk is not None else [hb["key"] for hb in _hubs]
            d["MENU_MORE"] = _show_more
            _tucked = []
            if _fk is not None:      # the person chose which sections to see: the rest are hidden from the sidebar but stay in search and in "All tools"
                _keep = []
                for hb in _hubs:
                    (_keep if hb["key"] in _fk or any(pp == request.path or request.path.startswith(pp.rstrip("/") + "/") for t in hb["tabs"] for pp in t["paths"]) else _tucked).append(hb)
                _hubs = _keep
            _skip = {url_for("m_list", key="content_items")} | {url_for(e, **({"key": k2} if k2 else {})) for e, k2 in FOLDED}      # the raw table of posts: Posts already covers it
            _other = [(lbl, h) for h, lbl in _label_of.items() if h not in _seen and h not in _skip]
            _rest = [(s["label"], s["href"]) for hb in _tucked for t in hb["tabs"] for s in (t.get("subs") or [t])] + _other
            _card = lambda t: (t["label"], t["href"], [(s["label"], s["href"]) for s in (t.get("subs") or [])])
            d["AREAS"] = [(hb["icon"] + " " + hb["label"], [_card(t) for t in hb["tabs"]]) for hb in (_hubs + _tucked)] + ([("🧰 Other", [(lbl, h, []) for lbl, h in _other])] if _other else [])
            d["HUBS_HIDDEN"] = len(_tucked)
            _tools_url = url_for("tools_page")
            _search_hubs = list(_hubs) + list(_tucked)
            if _other:
                _search_hubs.append(dict(key="other", icon="🧰", label="Other tools", lv=3, href=_other[0][1], tabs=[dict(label=l, href=h, paths=[h.split("?")[0]], on=False) for l, h in _other], on=False))
            # Everything the person could add to the sidebar, for the list in Profile > Menu.
            _pool = _rest + [(s["label"], s["href"]) for hb in _hubs for t in hb["tabs"] for s in (t.get("subs") or [t]) if t.get("more")]
            _pool = [(l, hh) for l, hh in dict.fromkeys((l, hh) for l, hh in _pool) if hh and hh != _tools_url]
            d["MENU_TOOLS"] = sorted(_pool, key=lambda x: x[0].lower())
            d["MENU_TOOLS_SEL"] = _show_more if isinstance(_show_more, list) else []
            # "More tools" shows only the tools that were ticked. Nothing ticked, no section at all.
            # "More tools" is its own small section in the sidebar, holding exactly the tools that
            # were ticked in Profile > Menu. Nothing ticked, no section at all.
            # "More tools" is where everything you switched off goes. A section you untick in
            # Profile > Menu lands here straight away, even if it is the only one, so nothing you
            # turned off becomes unreachable.
            d["ESS_TOOLS_ALL"] = _tools_url
            d["ESS_TOOLS"] = [(hb["icon"] + " " + hb["label"], hb["tabs"][0]["href"]) for hb in _tucked]
            if _show_more:
                if isinstance(_show_more, list):
                    _known = {hh: l for l, hh in _pool}
                    _picked = [(_label_of.get(hh) or _known.get(hh) or hh, hh) for hh in _show_more
                               if hh in _label_of or hh in _known]
                else:
                    _picked = _pool                # an older save meant "show them all"
                d["ESS_TOOLS"] = d["ESS_TOOLS"] + [x for x in _picked if x[1] not in {h for _l, h in d["ESS_TOOLS"]}]
            _p = request.path
            for hb in _hubs:
                for t in hb["tabs"]:
                    for pp in t["paths"]:
                        if not (_p == pp or _p.startswith(pp.rstrip("/") + "/")):
                            continue
                        if len(pp) > _best:
                            _best, _cur, _curtab = len(pp), hb, t
            if _cur:
                _cur["on"] = True
                _curtab["on"] = True
            d["HUBS"] = _hubs
            d["HUB_CUR"] = _cur
            d["HUB_TABS"] = _cur["tabs"] if _cur and len(_cur["tabs"]) > 1 and _cur["key"] != "more" else []
            _lang = (g.ws["lang"] or "en") if ("lang" in g.ws.keys()) else "en"
            if _lang != "en":
                import i18n as _i                      # menu names are the most-read words in the app
                _tr = lambda s: _i.t(s, _lang)
                # copies, never the shared hub definitions: one workspace's language must not leak into another's
                d["HUBS"] = [dict(h, label=_tr(h["label"])) for h in _hubs]
                d["HUB_TABS"] = [dict(t, label=_tr(t["label"])) for t in (d.get("HUB_TABS") or [])]
                if d.get("HUB_CUR"):
                    d["HUB_CUR"] = dict(d["HUB_CUR"], label=_tr(d["HUB_CUR"]["label"]))
            d["HUB_NOW"] = _curtab["href"] if _cur else ""
            d["SUBTABS"] = []
            if _curtab and _curtab.get("subs"):
                _sb = max(((len(pp), s) for s in _curtab["subs"] for pp in s["paths"] if _p == pp or _p.startswith(pp.rstrip("/") + "/")), key=lambda x: x[0], default=(0, None))[1]
                d["SUBTABS"] = [dict(label=s["label"], href=s["href"], on=s is _sb) for s in _curtab["subs"]]
            d["TOOLS"] = [dict(g=hb["label"], k=hb["key"], i=hb["icon"], items=[[s["label"], s["href"]] for t in hb["tabs"] for s in (t.get("subs") or [t])]) for hb in _search_hubs] + ([dict(g="Help", i="🫠", items=[["🫠 Idk what to do", url_for("whatnow")], ["📖 Jargon buster", url_for("glossary")], ["❓ Help & guides", url_for("help_centre")]])] if g.role != "client" else [])
            for _tg in d["TOOLS"]:      # the Instagram grid lives inside Create; it still turns up when you search for it
                if _tg.get("k") == "content" and any("/studio" in x[1] for x in _tg["items"]):
                    _tg["items"].append(["🧩 Instagram grid", url_for("studio.grid")])
                    _tg["items"].append(["📲 Post to Instagram", url_for("social.publishing")])
            if g.role == "client":
                d["NAV"] = OrderedDict([("Your workspace", [("🏠 Client portal", url_for("portal"))])])
                d["ESSENTIALS"] = []
                d["TOOLS"] = []
                d["HUBS"], d["HUB_CUR"], d["HUB_TABS"], d["HUB_NOW"] = [], None, [], ""
        if request.endpoint in MARKETING and not (request.endpoint == "templates_gallery" and g.get("ws")):
            d["bare"] = True      # Templates is a real tool once you are signed in, so it keeps the app's own chrome
        return d

    @app.after_request
    def headers(r):
        r.headers.setdefault("X-Content-Type-Options", "nosniff")
        r.headers.setdefault("X-Frame-Options", "DENY")
        r.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        r.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        r.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
        if C.PROD:
            r.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if r.mimetype == "text/html" and r.status_code < 400 and not r.direct_passthrough and not request.path.startswith("/static") and (not app.testing or request.headers.get("X-Icons")) and (not g.get("user") or request.endpoint in OUTSIDE_PAGES):
            try:
                import icons as _ic
                r.set_data(_ic.swap(r.get_data(as_text=True)))
            except Exception:
                pass
        if g.get("user") and r.mimetype == "text/html" and r.status_code < 400 and not r.direct_passthrough:
            try:      # page titles are plain words; emoji stay on buttons, tabs and cards
                body = r.get_data(as_text=True)
                if 'class="app' in body[:4000]:
                    r.set_data(_TITLE_EMOJI.sub(r"\1", body))
            except Exception:
                pass
        if g.get("user") and r.mimetype == "text/html":
            r.headers["Cache-Control"] = "private, no-store"
        # Count which screens get opened, so "is this feature redundant?" has an answer. Only
        # successful GETs of real pages by a signed-in person, and only the endpoint name.
        if (request.method == "GET" and r.status_code == 200 and r.mimetype == "text/html"
                and g.get("user") and g.get("ws") and request.endpoint):
            import usage
            usage.record(g.ws["id"], g.user["id"], request.endpoint, request.view_args)
        if request.path.startswith("/static/") and r.status_code == 200:
            r.headers["Cache-Control"] = "public, max-age=604800"          # CSS, JS and images change only on a new release
        try:       # gzip text responses: the pages and stylesheets are several times smaller on a phone connection
            if (r.status_code == 200 and not r.direct_passthrough and "gzip" in request.headers.get("Accept-Encoding", "") and "Content-Encoding" not in r.headers
                    and (r.mimetype.startswith("text/") or r.mimetype in ("application/json", "application/javascript", "image/svg+xml")) and len(r.get_data()) > 800):
                import gzip
                r.set_data(gzip.compress(r.get_data(), 5))
                r.headers["Content-Encoding"] = "gzip"
                r.headers.add("Vary", "Accept-Encoding")
        except Exception:
            pass
        return r

    def _err(code, msg):
        if request.path.startswith("/api/"):
            return jsonify(error=msg), code
        return render_template("error.html", code=code, msg=msg), code

    app.register_error_handler(DataError, lambda e: _err(400, "That input contains something we can't store. Please check it and try again."))
    app.register_error_handler(StatementError, lambda e: _err(400, "That input contains something we can't store. Please check it and try again."))
    app.register_error_handler(403, lambda e: _err(403, "You don't have permission to do that."))
    app.register_error_handler(404, lambda e: _err(404, "We couldn't find that page."))
    app.register_error_handler(400, lambda e: _err(400, "That request wasn't valid. Please go back and try again."))
    app.register_error_handler(413, lambda e: _err(413, "That file is too large."))
    app.register_error_handler(429, lambda e: _err(429, "Too many requests. Please wait a moment and try again."))
    app.register_error_handler(500, lambda e: _err(500, "Something went wrong on our side. We've been notified."))
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8001, debug=not C.PROD)
