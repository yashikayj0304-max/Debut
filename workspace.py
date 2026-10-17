"""Team management, activity log, account settings, data export and workspace deletion."""
import io, csv, json, re, secrets, zipfile, datetime as dt
import segno
import totp
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session, abort, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import config as C
import services as S
import industries as IND
from db import q, ex, ins
from modules import MODULES
from auth import EMAIL_RE, check_password, send_verify, dev_link
from werkzeug.security import check_password_hash
from views import _csv_safe

bp = Blueprint("ws", __name__)


def _safe_back(url, default_endpoint="ws.account"):
    """Redirect back to wherever the request came from, kept to our own app (no open redirects)."""
    from urllib.parse import urlparse
    if url:
        p = urlparse(url)
        if not p.netloc or p.netloc == request.host:
            return p.path + (("?" + p.query) if p.query else "")
    return url_for(default_endpoint)


def _members(wid):
    return q("SELECT m.id AS mid, m.role, m.client_name, u.id AS uid, u.name, u.email FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=? ORDER BY m.id", (wid,))


@bp.route("/team")
@S.roles(*C.TEAM_MANAGERS)
def team():
    wid = g.ws["id"]
    invites = q("SELECT * FROM invites WHERE workspace_id=? AND accepted=0 AND expires>=? ORDER BY id DESC", (wid, S.today().isoformat()))
    members = [dict(m, editable=C.RANK[g.role] > C.RANK[m["role"]]) for m in _members(wid)]
    return render_template("team.html", members=members, invites=invites, roles=[r for r in C.ROLES if S.can_assign(g.role, r)], seats=g.plan["seats"],
                           seats_used=S.seats_used(wid), clients_used=S.clients_used(wid), clients_allowed=g.plan["clients"])


@bp.route("/team/invite", methods=["POST"])
@S.roles(*C.TEAM_MANAGERS)
def invite():
    wid, email, role = g.ws["id"], S.clean_text(request.form.get("email"), 254).lower(), request.form.get("role", "manager")
    if not EMAIL_RE.match(email) or not S.can_assign(g.role, role):
        flash("Enter a valid email and a role you are allowed to assign.")
        return redirect(url_for("ws.team"))
    members = _members(wid)
    client_name = S.clean_text(request.form.get("client_name"), 120)
    live = "workspace_id=? AND accepted=0 AND expires>=?"
    if role == "client":
        if not client_name:
            flash("Enter the client's name. It must match the “Client” field on their content, so they only see their own work.")
            return redirect(url_for("ws.team"))
        used = S.clients_used(wid) + q(f"SELECT COUNT(*) c FROM invites WHERE {live} AND role='client'", (wid, S.today().isoformat()), one=True)["c"]
        if used >= g.plan["clients"]:
            flash(f"Your {g.plan['name']} plan includes {g.plan['clients']} client-portal seat(s). Upgrade to invite more clients." if g.plan["clients"] else "The client portal is part of the Team and Agency plans.")
            return redirect(url_for("ws.team"))
    else:
        used = S.seats_used(wid) + q(f"SELECT COUNT(*) c FROM invites WHERE {live} AND role!='client'", (wid, S.today().isoformat()), one=True)["c"]
        if used >= g.plan["seats"]:
            flash(f"Your {g.plan['name']} plan includes {g.plan['seats']} seat(s). Upgrade to invite more people.")
            return redirect(url_for("ws.team"))
    if any(m["email"] == email for m in members):
        flash("That person is already in this workspace.")
        return redirect(url_for("ws.team"))
    token = secrets.token_urlsafe(24)
    ins("invites", dict(workspace_id=wid, email=email, role=role, client_name=client_name if role == "client" else "", token_hash=S.sha(token), expires=(S.today() + dt.timedelta(days=7)).isoformat()))
    link = url_for("auth.invite", token=token)
    sent = S.send_email(email, f"{g.user['name']} invited you to {g.ws['name']} on {C.APP_NAME}", (f"You've been invited to the {C.APP_NAME} client portal for {client_name}, where you can review and approve your work.\n\nOpen it: {C.APP_URL}{link}\n\nThe link expires in 7 days." if role == "client" else f"You've been invited as {role}.\n\nJoin: {C.APP_URL}{link}\n\nThe link expires in 7 days."))
    dev_link(sent, link)
    S.audit("invite", f"{email} as {role}")
    flash(f"Invite sent to {email}." if sent else f"Invite created for {email}.")
    return redirect(url_for("ws.team"))


@bp.route("/team/role", methods=["POST"])
@S.roles(*C.TEAM_MANAGERS)
def change_role():
    m = q("SELECT * FROM memberships WHERE id=? AND workspace_id=?", (S.to_int(request.form.get("mid"), 0), g.ws["id"]), one=True) or abort(404)
    role = request.form.get("role", "")
    if not S.can_assign(g.role, role, m["role"]):
        abort(403)
    if role == "client" or m["role"] == "client":
        flash("Client access is set when you invite someone. Remove and re-invite to change it.")
        return redirect(url_for("ws.team"))
    ex("UPDATE memberships SET role=? WHERE id=?", (role, m["id"]))
    S.audit("role_change", f"user#{m['user_id']} -> {role}")
    return redirect(url_for("ws.team"))


@bp.route("/team/remove", methods=["POST"])
@S.roles(*C.TEAM_MANAGERS)
def remove_member():
    m = q("SELECT * FROM memberships WHERE id=? AND workspace_id=?", (S.to_int(request.form.get("mid"), 0), g.ws["id"]), one=True) or abort(404)
    if C.RANK[g.role] <= C.RANK[m["role"]]:
        abort(403)
    ex("DELETE FROM memberships WHERE id=?", (m["id"],))
    S.audit("member_removed", f"user#{m['user_id']}")
    flash("Member removed.")
    return redirect(url_for("ws.team"))


@bp.route("/team/revoke/<int:iid>", methods=["POST"])
@S.roles(*C.TEAM_MANAGERS)
def revoke_invite(iid):
    ex("DELETE FROM invites WHERE id=? AND workspace_id=?", (iid, g.ws["id"]))
    return redirect(url_for("ws.team"))


@bp.route("/activity")
@S.roles(*C.TEAM_MANAGERS)
def activity():
    rows = q("SELECT a.*, u.name AS uname FROM audit_log a LEFT JOIN users u ON u.id=a.user_id WHERE a.workspace_id=? ORDER BY a.id DESC LIMIT 150", (g.ws["id"],))
    return render_template("activity.html", rows=rows)


@bp.route("/account")
def account():
    cands = [m for m in _members(g.ws["id"]) if m["uid"] != g.user["id"] and m["role"] in ("admin", "lead", "manager")] if g.role == "owner" else []
    return render_template("account.html", industries=IND.CHOICES, candidates=cands)


@bp.route("/account/profile", methods=["POST"])
def account_profile():
    ex("UPDATE users SET name=? WHERE id=?", (S.clean_text(request.form.get("name"), 80), g.user["id"]))
    flash("Profile updated.")
    return redirect(url_for("ws.account"))


@bp.route("/account/password", methods=["POST"])
def account_password():
    f = request.form
    if not check_password_hash(g.user["password_hash"], f.get("current", "")):
        flash("Current password is incorrect.")
    elif check_password(f.get("new", ""), g.user["email"]):
        flash(check_password(f.get("new", ""), g.user["email"]))
    else:
        ex("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(f["new"]), g.user["id"]))
        S.audit("password_change")
        flash("Password changed.")
    return redirect(url_for("ws.account"))


@bp.route("/account/verify", methods=["POST"])
def account_verify():
    if not g.user["email_verified"]:
        send_verify(g.user)
        flash("Verification email sent.")
    # Stay on whatever page the "Resend link" button was clicked from (the banner shows on every
    # page) instead of forcing a jump to the Account page - the click should just confirm it was sent.
    return redirect(_safe_back(request.referrer, "dashboard"))


@bp.route("/account/pin", methods=["POST"])
def account_pin():
    f = request.form
    if f.get("remove"):
        ex("UPDATE users SET pin_hash='' WHERE id=?", (g.user["id"],))
        flash("PIN sign-in removed.")
        return redirect(url_for("ws.account"))
    if not check_password_hash(g.user["password_hash"], f.get("current", "")):
        flash("Current password is incorrect.")
        return redirect(url_for("ws.account"))
    pin = S.clean_text(f.get("pin"), 6)
    if not re.fullmatch(r"\d{4,6}", pin or ""):
        flash("PIN must be 4-6 digits.")
        return redirect(url_for("ws.account"))
    ex("UPDATE users SET pin_hash=? WHERE id=?", (generate_password_hash(pin), g.user["id"]))
    S.audit("pin_set")
    flash("PIN sign-in is on. You'll be asked for it at your next login.")
    return redirect(url_for("ws.account"))


@bp.route("/account/logo", methods=["POST"])
@S.roles("owner", "admin")
def account_logo():
    f = request.files.get("file")
    data = f.read(5 * 1024 * 1024 + 1) if f else b""
    ext = S.sniff_image(data) if data and len(data) <= 5 * 1024 * 1024 else None
    if not ext:
        flash("Choose a PNG, JPG, GIF or WebP logo up to 5 MB.")
        return redirect(url_for("ws.account"))
    old = g.ws["logo_url"]
    ex("UPDATE workspaces SET logo_url=? WHERE id=?", (S.store_file(g.ws["id"], ext, data), g.ws["id"]))
    if old:
        S.delete_file(old)
    S.audit("logo_set")
    flash("Logo updated.")
    return redirect(url_for("ws.account"))


@bp.route("/account/logo/remove", methods=["POST"])
@S.roles("owner", "admin")
def account_logo_remove():
    if g.ws["logo_url"]:
        S.delete_file(g.ws["logo_url"])
        ex("UPDATE workspaces SET logo_url='' WHERE id=?", (g.ws["id"],))
    return redirect(url_for("ws.account"))


@bp.route("/workspace/rename", methods=["POST"])
@S.roles("owner", "admin")
def rename():
    name = S.clean_text(request.form.get("name"), 80)
    if not name:
        flash("Enter a workspace name.")
    else:
        ex("UPDATE workspaces SET name=? WHERE id=?", (name, g.ws["id"]))
    return redirect(url_for("ws.account"))


@bp.route("/industry", methods=["POST"])
@S.roles("owner", "admin")
def industry_update():
    key = request.form.get("industry", "")
    if key not in IND.INDUSTRIES:
        abort(400)
    ex("UPDATE workspaces SET industry=? WHERE id=?", (key, g.ws["id"]))
    S.audit("industry", key)
    if request.form.get("kit"):
        n = S.apply_industry(g.ws["id"], key, personas=True)
        flash(f"Starter kit loaded: {n['checklist']} checklist items, {n['dates']} key dates, {n['feeds']} news feeds, {n['personas']} personas.")
    else:
        flash("Industry updated. The Idea Bank and AI Studio now use it. Use “Save & load starter kit” to add its checklist, key dates, feeds and personas.")
    return redirect(url_for("ideas") if request.form.get("kit") else url_for("ws.account"))


@bp.route("/export.zip")
@S.roles("owner", "admin", "lead", "manager")
def export_zip():
    """Full workspace export (data portability)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for key, m in MODULES.items():
            names = [f[0] for f in m["fields"]]
            s = io.StringIO()
            w = csv.writer(s)
            w.writerow(names)
            for r in q(f"SELECT * FROM {key} WHERE workspace_id=? ORDER BY id", (g.ws["id"],)):
                w.writerow([_csv_safe(r[n]) for n in names])
            z.writestr(f"{key}.csv", s.getvalue())
        s = io.StringIO()
        w = csv.writer(s)
        w.writerow(["board", "kind", "content", "caption"])
        for r in q("SELECT b.name AS board, i.kind, i.content, i.caption FROM board_items i JOIN boards b ON b.id=i.board_id WHERE i.workspace_id=?", (g.ws["id"],)):
            w.writerow([_csv_safe(r["board"]), r["kind"], _csv_safe(r["content"]), _csv_safe(r["caption"])])
        z.writestr("moodboards.csv", s.getvalue())
    S.audit("export")
    return Response(buf.getvalue(), mimetype="application/zip", headers={"Content-Disposition": f"attachment; filename={g.ws['slug']}-export.zip"})


@bp.route("/workspace/delete", methods=["POST"])
@S.roles("owner")
def delete_workspace():
    if request.form.get("confirm", "").strip() != g.ws["slug"]:
        flash("Type the workspace URL name exactly to confirm.")
        return redirect(url_for("ws.account"))
    S.delete_workspace_data(g.ws["id"])
    session.pop("ws", None)
    flash("Workspace and all its data were permanently deleted.")
    return redirect(url_for("dashboard"))


# ----------------------------------------------------------------- two-factor login, digest preference
@bp.route("/account/2fa")
def twofa():
    if g.user["totp_on"]:
        return render_template("twofa.html", on=True)
    secret = session.get("totp_setup") or totp.new_secret()
    session["totp_setup"] = secret
    uri = totp.uri(secret, g.user["email"], C.APP_NAME)
    return render_template("twofa.html", on=False, secret=secret, qr=segno.make(uri, error="m").svg_inline(scale=5, dark="#3b2a78", border=2))


@bp.route("/account/2fa/enable", methods=["POST"])
def twofa_enable():
    secret = session.get("totp_setup")
    step = totp.verify(secret, request.form.get("code", "")) if secret else None
    if step is None:
        flash("That code didn't match. Check the time on your phone and try the newest code.")
        return redirect(url_for("ws.twofa"))
    codes = totp.new_recovery_codes()
    ex("UPDATE users SET totp_secret=?, totp_on=1, totp_last=?, recovery=? WHERE id=?", (secret, step, json.dumps([S.sha(c) for c in codes]), g.user["id"]))
    session.pop("totp_setup", None)
    S.audit("2fa_enabled")
    return render_template("recovery_codes.html", codes=codes)


@bp.route("/account/2fa/disable", methods=["POST"])
def twofa_disable():
    u = g.user
    ok = check_password_hash(u["password_hash"], request.form.get("password", "")[:200]) and totp.verify(u["totp_secret"], request.form.get("code", ""), u["totp_last"] or 0) is not None
    if not ok:
        flash("Password or code incorrect. Two-factor is still on.")
        return redirect(url_for("ws.twofa"))
    ex("UPDATE users SET totp_on=0, totp_secret='', recovery='', totp_last=0 WHERE id=?", (u["id"],))
    S.audit("2fa_disabled")
    flash("Two-factor login turned off.")
    return redirect(url_for("ws.account"))


@bp.route("/account/digest", methods=["POST"])
def account_digest():
    ex("UPDATE users SET digest=? WHERE id=?", (1 if request.form.get("on") == "1" else 0, g.user["id"]))
    flash("Daily digest " + ("on." if request.form.get("on") == "1" else "off."))
    return redirect(url_for("ws.account"))


# ----------------------------------------------------------------- integrations: lead capture, report/calendar links, API keys
@bp.route("/integrations")
@S.roles("owner", "admin", "lead", "manager")
def integrations():
    ws = g.ws
    keys = q("SELECT * FROM api_keys WHERE workspace_id=? ORDER BY id DESC", (ws["id"],))
    hook = ws["hook_key"]
    if not hook:
        hook = secrets.token_hex(12)
        ex("UPDATE workspaces SET hook_key=? WHERE id=?", (hook, ws["id"]))
    return render_template("integrations.html", keys=keys, has_api="api" in g.plan["features"], form_url=C.APP_URL + url_for("lead_form", slug=ws["slug"]),
                           hook_url=C.APP_URL + url_for("lead_hook", key=hook), base=C.APP_URL)


@bp.route("/integrations/hook-reset", methods=["POST"])
@S.roles("owner", "admin", "lead", "manager")
def hook_reset():
    ex("UPDATE workspaces SET hook_key=? WHERE id=?", (secrets.token_hex(12), g.ws["id"]))
    S.audit("hook_key_reset")
    flash("Webhook URL reset. Update it in any form or automation that used the old one.")
    return redirect(url_for("ws.integrations"))


@bp.route("/integrations/api-keys", methods=["POST"])
@S.roles("owner", "admin")
def api_key_create():
    if "api" not in g.plan["features"]:
        flash("API access is included in the Team and Agency plans.")
        return redirect(url_for("ws.integrations"))
    if q("SELECT COUNT(*) c FROM api_keys WHERE workspace_id=?", (g.ws["id"],), one=True)["c"] >= 10:
        flash("You already have 10 API keys. Revoke one first.")
        return redirect(url_for("ws.integrations"))
    key = "gtm_" + secrets.token_urlsafe(32)
    scope = "write" if request.form.get("scope") == "write" else "read"
    ins("api_keys", dict(workspace_id=g.ws["id"], user_id=g.user["id"], name=S.clean_text(request.form.get("name"), 60) or "API key", prefix=key[:8], key_hash=S.sha(key), scope=scope))
    S.audit("api_key_created", scope)
    return render_template("api_key_created.html", key=key, scope=scope, base=C.APP_URL)     # shown once; only a hash is stored


@bp.route("/integrations/api-keys/<int:kid>/revoke", methods=["POST"])
@S.roles("owner", "admin")
def api_key_revoke(kid):
    ex("DELETE FROM api_keys WHERE id=? AND workspace_id=?", (kid, g.ws["id"]))
    S.audit("api_key_revoked")
    flash("API key revoked.")
    return redirect(url_for("ws.integrations"))


# ----------------------------------------------------------------- ownership transfer
@bp.route("/workspace/transfer", methods=["POST"])
@S.roles("owner")
def transfer_ownership():
    """Hand the workspace (and its billing) to another member. The old owner becomes an Admin."""
    f, u = request.form, g.user
    target = q("SELECT m.id AS mid, m.role, u.id AS uid, u.name, u.email FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.id=? AND m.workspace_id=?",
               (S.to_int(f.get("mid"), 0), g.ws["id"]), one=True)
    ok = target and target["role"] in ("admin", "lead", "manager") and target["uid"] != u["id"] and f.get("confirm", "").strip() == "TRANSFER" \
        and check_password_hash(u["password_hash"], f.get("password", "")[:200])
    if ok and u["totp_on"]:
        ok = totp.verify(u["totp_secret"], f.get("code", ""), u["totp_last"] or 0) is not None
    if not ok:
        flash("Ownership was not transferred. Choose a teammate (Admin, Lead or Manager), type TRANSFER, and enter your password" + (" and a current two-factor code." if u["totp_on"] else "."))
        return redirect(url_for("ws.account"))
    me = q("SELECT id FROM memberships WHERE workspace_id=? AND user_id=?", (g.ws["id"], u["id"]), one=True)
    ex("UPDATE memberships SET role='admin' WHERE id=?", (me["id"],))
    ex("UPDATE memberships SET role='owner' WHERE id=?", (target["mid"],))
    ex("UPDATE workspaces SET owner_id=? WHERE id=?", (target["uid"], g.ws["id"]))
    S.audit("ownership_transferred", f"{u['email']} -> {target['email']}")
    S.send_email(target["email"], f"You are now the owner of {g.ws['name']} on {C.APP_NAME}", f"{u['name'] or u['email']} transferred ownership of the workspace \"{g.ws['name']}\" to you.\nYou can now manage billing and settings under Plan and Account.\n{C.APP_URL}/app")
    flash(f"Ownership transferred to {target['name'] or target['email']}. You are now an Admin.")
    return redirect(url_for("dashboard"))


# ----------------------------------------------------------------- brand theming (business workspaces; not for personal-brand industry)
@bp.route("/account/theme", methods=["POST"])
@S.roles("owner", "admin")
def account_theme():
    if g.ws["industry"] == "personal_brand":
        abort(403)
    color = S.clean_text(request.form.get("color"), 10)
    if not S.HEX_RE.match(color):
        flash("Enter a primary colour as a 6-digit hex code, e.g. #1E88E5.")
        return redirect(url_for("ws.account"))
    secondary = S.clean_text(request.form.get("secondary"), 10)
    if secondary and not S.HEX_RE.match(secondary):
        flash("Enter a secondary colour as a 6-digit hex code, e.g. #1E88E5, or leave it blank to pick one automatically.")
        return redirect(url_for("ws.account"))
    ex("UPDATE workspaces SET brand_color=?, secondary_color=? WHERE id=?", (color, secondary, g.ws["id"]))
    S.audit("brand_color_set", f"{color} / {secondary or 'auto'}")
    flash("Brand colours applied across your workspace.")
    return redirect(url_for("ws.account"))


@bp.route("/account/theme/reset", methods=["POST"])
@S.roles("owner", "admin")
def account_theme_reset():
    ex("UPDATE workspaces SET brand_color='', secondary_color='' WHERE id=?", (g.ws["id"],))
    S.audit("brand_color_reset")
    flash("Back to the default Debut theme.")
    return redirect(url_for("ws.account"))


# ----------------------------------------------------------------- first-time onboarding tour
@bp.route("/account/onboarded", methods=["POST"])
def onboarded():
    ex("UPDATE users SET onboarded=1 WHERE id=?", (g.user["id"],))
    return jsonify(ok=True)
