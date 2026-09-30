"""Platform-owner console (only emails listed in ADMIN_EMAILS)."""
import datetime as dt
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort, session
import config as C
import services as S
import industries as IND
from db import q, ex

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
def only_admins():
    if not S.is_platform_admin(g.get("user")):
        abort(404)


@bp.route("/")
def index():
    term = S.clean_text(request.args.get("q"), 80).lower()
    like = f"%{term}%"
    if term:
        rows = q("SELECT w.*, u.email AS owner_email, (SELECT COUNT(*) FROM memberships m WHERE m.workspace_id=w.id) AS members FROM workspaces w LEFT JOIN users u ON u.id=w.owner_id "
                 "WHERE LOWER(w.name) LIKE ? OR LOWER(w.slug) LIKE ? OR LOWER(u.email) LIKE ? ORDER BY w.id DESC LIMIT 500", (like, like, like))
        users = q("SELECT u.*, (SELECT COUNT(*) FROM memberships m WHERE m.user_id=u.id) AS n_ws FROM users u WHERE LOWER(u.email) LIKE ? OR LOWER(u.name) LIKE ? ORDER BY u.id DESC LIMIT 200", (like, like))
    else:
        rows = q("SELECT w.*, u.email AS owner_email, (SELECT COUNT(*) FROM memberships m WHERE m.workspace_id=w.id) AS members FROM workspaces w LEFT JOIN users u ON u.id=w.owner_id ORDER BY w.id DESC LIMIT 500")
        users = q("SELECT u.*, (SELECT COUNT(*) FROM memberships m WHERE m.user_id=u.id) AS n_ws FROM users u ORDER BY u.id DESC LIMIT 100")
    everything = q("SELECT plan, plan_status, period_end, trial_ends FROM workspaces")
    active = [r for r in everything if r["plan"] in C.PAID_PLANS and S.plan_key(r) == r["plan"]]
    mrr = sum(C.PLANS[r["plan"]]["price"] for r in active)
    n_trials = len([r for r in everything if S.plan_key(r) == "trial"])
    n_free = len([r for r in everything if S.plan_key(r) == "free"])
    total_users = q("SELECT COUNT(*) c FROM users", one=True)["c"]
    return render_template("admin.html", metrics=launch_metrics(), rows=rows, users=users, mrr=mrr, n_paid=len(active), n_trials=n_trials, n_free=n_free, n_users=total_users, n_ws=len(everything), plans=C.PLANS, term=term, industries=IND.INDUSTRIES)


def launch_metrics():
    """The numbers to watch during a launch: are people signing up, doing something, and paying?"""
    t = S.today()
    d7, d14, d30 = ((t - dt.timedelta(days=n)).isoformat() for n in (7, 14, 30))
    one = lambda sql, a=(): q(sql, a, one=True)["c"]
    signups = {}
    for r in q("SELECT created_at FROM users WHERE created_at>=?", (d14,)):
        signups[str(r["created_at"])[:10]] = signups.get(str(r["created_at"])[:10], 0) + 1
    ending = q("SELECT w.name, w.slug, w.trial_ends, u.email FROM workspaces w LEFT JOIN users u ON u.id=w.owner_id WHERE w.plan='trial' AND w.trial_ends BETWEEN ? AND ? ORDER BY w.trial_ends", (t.isoformat(), (t + dt.timedelta(days=3)).isoformat()))
    return dict(users_7=one("SELECT COUNT(*) c FROM users WHERE created_at>=?", (d7,)), users_30=one("SELECT COUNT(*) c FROM users WHERE created_at>=?", (d30,)),
                ws_7=one("SELECT COUNT(*) c FROM workspaces WHERE created_at>=?", (d7,)),
                active_7=one("SELECT COUNT(DISTINCT workspace_id) c FROM audit_log WHERE created_at>=? AND action IN ('create','update','delete','import','comment','api_create')", (d7,)),
                ai_today=one("SELECT COALESCE(SUM(credits),0) c FROM ai_usage WHERE created_at>=?", (t.isoformat(),)), ai_30=one("SELECT COALESCE(SUM(credits),0) c FROM ai_usage WHERE created_at>=?", (d30,)),
                subs_30=one("SELECT COUNT(*) c FROM audit_log WHERE action='subscribed' AND created_at>=?", (d30,)),
                open_feedback=one("SELECT COUNT(*) c FROM feedback WHERE resolved=0"), signups=sorted(signups.items()), ending=ending)


@bp.route("/feedback")
def feedback_inbox():
    rows = q("SELECT f.*, u.email, u.name AS uname, w.name AS wname, w.plan FROM feedback f LEFT JOIN users u ON u.id=f.user_id LEFT JOIN workspaces w ON w.id=f.workspace_id ORDER BY f.resolved, f.id DESC LIMIT 200")
    return render_template("admin_feedback.html", rows=rows)


@bp.route("/feedback/<int:fid>/resolve", methods=["POST"])
def feedback_resolve(fid):
    ex("UPDATE feedback SET resolved=1 WHERE id=?", (fid,))
    return redirect(url_for("admin.feedback_inbox"))


@bp.route("/ws/<int:wid>/support", methods=["POST"])
def support(wid):
    """Read-only look at a customer workspace, for support. Logged in the customer's activity log."""
    q("SELECT 1 FROM workspaces WHERE id=?", (wid,), one=True) or abort(404)
    session["support_ws"] = wid
    S.audit("admin_support_view", g.user["email"], wid=wid)
    return redirect(url_for("dashboard"))


@bp.route("/exit-support", methods=["POST"])
def exit_support():
    session.pop("support_ws", None)
    return redirect(url_for("admin.index"))


@bp.route("/user/<int:uid>/verify", methods=["POST"])
def verify_user(uid):
    ex("UPDATE users SET email_verified=1 WHERE id=?", (uid,))
    flash("Email marked as verified.")
    return redirect(url_for("admin.index"))


@bp.route("/ws/<int:wid>", methods=["POST"])
def act(wid):
    action = request.form.get("action")
    if action == "extend":
        ws = q("SELECT * FROM workspaces WHERE id=?", (wid,), one=True) or abort(404)
        base = max(S.today(), dt.date.fromisoformat(ws["trial_ends"] or S.today().isoformat()))
        ex("UPDATE workspaces SET trial_ends=? WHERE id=?", ((base + dt.timedelta(days=14)).isoformat(), wid))
    elif action == "set_plan" and request.form.get("plan") == "free":
        ex("UPDATE workspaces SET plan='free', plan_status='free', cancel_at_period_end=0 WHERE id=?", (wid,))
    elif action == "set_plan" and request.form.get("plan") in C.PAID_PLANS:
        ex("UPDATE workspaces SET plan=?, plan_status='active', period_end=? WHERE id=?", (request.form["plan"], (S.today() + dt.timedelta(days=3650)).isoformat(), wid))
    S.audit("admin_" + str(action), f"ws#{wid}", wid=wid)
    flash("Done.")
    return redirect(url_for("admin.index"))
