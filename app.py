"""Debut: go-to-market and marketing workspace (multi-tenant SaaS). Run locally: python app.py   Production: gunicorn wsgi:app"""
import logging
from flask import Flask, g, request, session, render_template, redirect, url_for, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import config as C
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

PUBLIC = {"landing", "pricing", "terms", "privacy", "health", "robots", "static", "auth.login", "auth.login_2fa", "auth.login_pin", "auth.signup", "auth.forgot", "auth.reset",
          "auth.verify", "auth.invite", "apply_form", "billing.webhook", "ics_feed", "lead_form", "lead_hook", "report_public", "manifest", "service_worker", "offline", "unsubscribe", "contact", "refunds", "sitemap"}
VIEWER_WRITE_OK = {"auth.logout", "auth.switch_ws", "admin.exit_support", "admin.support", "ws.account_profile", "ws.account_password", "ws.account_verify",
                   "ws.twofa_enable", "ws.twofa_disable", "ws.account_digest", "comment_add", "comment_delete", "notifications_read", "feedback", "ws.onboarded"}
CLIENT_OK = {"dashboard", "portal", "portal_item", "portal_decide", "portal_comment", "notifications", "notifications_recent", "notifications_read", "notification_open", "feedback", "help_centre", "auth.logout", "auth.switch_ws",
             "ws.account", "ws.account_profile", "ws.account_password", "ws.account_verify", "ws.twofa", "ws.twofa_enable", "ws.twofa_disable", "ws.onboarded"}
CREATOR_OK = {"dashboard", "m_list", "m_new", "m_edit", "m_save", "kanban", "m_status", "calendar_view", "search", "moodboards", "board_view", "media", "ideas",
              "auth.logout", "auth.switch_ws", "ws.account", "ws.account_profile", "ws.account_password", "ws.account_verify",
              "ws.twofa", "ws.twofa_enable", "ws.twofa_disable", "ws.account_digest", "comment_add", "comment_delete", "notifications", "notifications_read", "notification_open", "feedback", "help_centre", "ws.onboarded", "board_new", "board_add", "board_item_delete", "board_delete", "board_item_place", "board_item_edit", "board_item_replace_image", "board_arrange", "board_sample"}
FEATURE_EP = {"content_ops": "content_ops", "order_match": "content_ops", "order_assign": "content_ops", "discover": "influencers", "outreach": "influencers",
              "influencer_contacted": "influencers", "event_checklist": "promo_events", "team_hub": "group", "analytics": "analytics", "ai_studio": "ai", "api_ai": "ai"}


def create_app(config=None, init=True, database_url=None):
    app = Flask(__name__)
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
    csrf.init_app(app)
    limiter.init_app(app)
    if init:
        with app.app_context():
            D.init_schema(MODULES)
    app.teardown_appcontext(D.close_conn)

    from auth import bp as auth_bp
    from billing import bp as billing_bp
    from workspace import bp as ws_bp
    from admin import bp as admin_bp
    from api import bp as api_bp
    for b in (auth_bp, billing_bp, ws_bp, admin_bp, api_bp):
        app.register_blueprint(b)
    views.register(app)

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
            need = next((p["name"] for k, p in C.PLANS.items() if k in C.PAID_PLANS and feat in p["features"]), "a paid")
            return render_template("upgrade.html", feature=feat, need=need), 403

    def _forbidden():
        if request.path.startswith("/api/"):
            return jsonify(error="You don't have permission to do that."), 403
        return render_template("error.html", code=403, msg="You don't have permission to do that."), 403

    @app.context_processor
    def ctx():
        d = dict(C=C, user=g.get("user"), ws=g.get("ws"), role=g.get("role"), plan=g.get("plan"), memberships=g.get("memberships", []), media=S.media_url, NAV=OrderedDict(), bare=False, today=S.today().isoformat(), trial_left=None, plan_key="free", on_free=False, lapsed=False, unread=0, is_admin=False, admin_needs_2fa=False, brand=None, support=g.get("support", False), TEAM_MANAGERS=C.TEAM_MANAGERS, industry=None)
        if g.get("user") and g.get("ws"):
            d["trial_left"] = S.trial_days_left(g.ws)
            d["plan_key"] = g.plan_key
            d["industry"] = IND.get(g.ws["industry"])
            d["unread"] = S.unread_count(g.user["id"], g.ws["id"])
            d["brand"] = S.brand_shades(g.ws)
            d["is_admin"] = S.is_platform_admin(g.user)
            d["admin_needs_2fa"] = bool(g.user["email_verified"]) and g.user["email"] in C.ADMIN_EMAILS and not d["is_admin"]
            d["on_free"] = g.plan_key == "free"
            d["lapsed"] = g.plan_key == "free" and g.ws["plan"] != "free"
            groups = OrderedDict([("Strategy", []), ("Content", []), ("Campaigns", []), ("Promotions & Events", []), ("Content Ops", []), ("Growth", []), ("Intelligence", [])])
            special = {"Content": [("Calendar", "calendar_view", "📅"), ("Mood Boards", "moodboards", "🖼️"), ("Idea Bank", "ideas", "💡")],
                       "Campaigns": [("Discover Influencers", "discover", "🔭"), ("UTM Builder", "utm", "🏷️")],
                       "Content Ops": [("Ops Dashboard", "content_ops", "📊")], "Growth": [("Analytics", "analytics", "📈")],
                       "Intelligence": [("Market Pulse", "pulse_page", "📡"), ("Latest Updates", "updates", "⚡"), ("AI Studio", "ai_studio", "🤖")]}
            feat_of = {"content_ops": "content_ops", "discover": "influencers", "analytics": "analytics", "ai_studio": "ai"}
            creator = g.role == "creator"
            lock = lambda f: " 🔒" if (f and f not in g.plan["features"]) else ""
            for grp, items in special.items():
                for label, ep, icon in items:
                    if creator and ep not in ("calendar_view", "moodboards", "ideas"):
                        continue
                    groups[grp].append((f"{icon} {label}{lock(feat_of.get(ep))}", url_for(ep)))
            for k, m in MODULES.items():
                if k in ("utm_links", "watchlist") or (creator and k not in CREATOR_MODULES):
                    continue
                if k in IND.MODULE_INDUSTRIES and g.ws["industry"] not in IND.MODULE_INDUSTRIES[k]:
                    continue
                groups[m["group"]].append((f"{m['icon']} {m['title']}{lock(MODULE_FEATURE.get(k))}", url_for("m_list", key=k)))
            d["NAV"] = OrderedDict((k, v) for k, v in groups.items() if v)
            if g.role == "client":
                d["NAV"] = OrderedDict([("Your workspace", [("🏠 Client portal", url_for("portal"))])])
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
        if g.get("user") and r.mimetype == "text/html":
            r.headers["Cache-Control"] = "private, no-store"
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
