"""Accounts: signup (creates a workspace + 14-day trial), login, password reset, email verification, invites."""
import re, datetime as dt
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, abort
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
import config as C
import services as S
import industries as IND
import totp
import json, time
import db as D
from sqlalchemy.exc import IntegrityError
from db import q, ex, ins
from extensions import limiter

bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
WEAK = {"password", "password1", "12345678", "123456789", "qwertyuiop", "iloveyou", "11111111"}


def ser(salt):
    return URLSafeTimedSerializer(C.SECRET_KEY, salt=salt)


def safe_next(default="/app"):
    n = request.values.get("next", "")
    return n if n.startswith("/") and not n.startswith("//") else default


def start_session(uid, ws_id=None):
    session.clear()
    session["uid"] = uid
    session.permanent = True
    if ws_id:
        session["ws"] = ws_id
    ex("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (uid,))


def check_password(pw, email=""):
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if len(pw) > 200:
        return "Password is too long (max 200 characters)."
    if pw.lower() in WEAK or pw.lower() == email.lower():
        return "That password is too easy to guess."
    return None


def dev_link(sent, link):
    if not sent and not C.PROD:
        flash("DEV (email not configured): " + C.APP_URL + link)


def send_verify(user):
    link = url_for("auth.verify", token=ser("verify").dumps(user["id"]))
    sent = S.send_email(user["email"], f"Verify your email for {C.APP_NAME}", f"Hi {user['name'] or ''},\n\nConfirm your email: {C.APP_URL}{link}\n\nThanks,\n{C.APP_NAME}")
    dev_link(sent, link)


def accept_invite(token, user):
    inv = q("SELECT * FROM invites WHERE token_hash=? AND accepted=0", (S.sha(token or ""),), one=True)
    if not inv or (inv["expires"] or "") < S.today().isoformat() or inv["email"] != user["email"]:
        return None
    if not q("SELECT 1 FROM memberships WHERE workspace_id=? AND user_id=?", (inv["workspace_id"], user["id"]), one=True):
        ins("memberships", dict(workspace_id=inv["workspace_id"], user_id=user["id"], role=inv["role"], client_name=inv["client_name"] or ""))
    ex("UPDATE invites SET accepted=1 WHERE id=?", (inv["id"],))
    S.audit("invite_accepted", user["email"], wid=inv["workspace_id"], uid=user["id"])
    return inv["workspace_id"]


def find_invite(token):
    if not token:
        return None
    inv = q("SELECT * FROM invites WHERE token_hash=? AND accepted=0", (S.sha(token),), one=True)
    if inv and (inv["expires"] or "") >= S.today().isoformat():
        return inv
    return None


@bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def signup():
    if g.user:
        return redirect(url_for("dashboard"))
    token = request.values.get("invite", "")
    inv = find_invite(token)
    if request.method == "POST":
        f = request.form
        email = (inv["email"] if inv else S.clean_text(f.get("email"), 254)).lower()
        name, pw = S.clean_text(f.get("name"), 80), f.get("password", "")
        wsname = S.clean_text(f.get("workspace"), 80) or (name + "'s workspace" if name else "My workspace")
        industry = f.get("industry", "general")
        industry = industry if industry in IND.INDUSTRIES else "general"
        err = None
        if not EMAIL_RE.match(email):
            err = "Enter a valid email."
        elif not name:
            err = "Enter your name."
        elif check_password(pw, email):
            err = check_password(pw, email)
        elif not f.get("agree"):
            err = "Please accept the Terms and Privacy Policy."
        elif q("SELECT 1 FROM users WHERE email=?", (email,), one=True):
            err = "That email is already registered. Log in or reset your password."
        if err:
            flash(err)
            return render_template("signup.html", inv=inv, token=token, form=f, industries=IND.CHOICES), 400
        try:
            uid = ins("users", dict(email=email, name=name, password_hash=generate_password_hash(pw)))
        except IntegrityError:   # two signups with the same email at the same moment
            D.conn().rollback()
            flash("That email is already registered. Log in or reset your password.")
            return render_template("signup.html", inv=inv, token=token, form=f, industries=IND.CHOICES), 400
        user = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
        wid = accept_invite(token, user) if inv else S.create_workspace(uid, wsname, industry, kit=bool(f.get("kit")))
        start_session(uid, wid)
        S.audit("signup", email, wid=wid, uid=uid)
        send_verify(user)
        flash("Welcome! Your workspace is ready.")
        return redirect(url_for("dashboard"))
    return render_template("signup.html", inv=inv, token=token, form={}, industries=IND.CHOICES)


def finish_login(user, token="", nxt=None):
    wid = accept_invite(token, user) if token else None
    start_session(user["id"], wid)
    S.audit("login", "", wid=wid, uid=user["id"])
    return redirect(nxt if (nxt or "").startswith("/") and not (nxt or "").startswith("//") else url_for("dashboard"))


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per 15 minutes", methods=["POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    token = request.values.get("invite", "")
    if request.method == "POST":
        email, pw = S.clean_text(request.form.get("email"), 254).lower(), request.form.get("password", "")[:201]
        user = q("SELECT * FROM users WHERE email=?", (email,), one=True)
        if not user or len(pw) > 200 or not check_password_hash(user["password_hash"], pw):
            flash("Incorrect email or password.")
            return render_template("login.html", token=token, email=email), 401
        if user["totp_on"]:                    # password ok; second factor still required
            session.clear()
            session["pending_2fa"] = dict(uid=user["id"], invite=token, nxt=safe_next(""), ts=int(time.time()))
            return redirect(url_for("auth.login_2fa"))
        return finish_login(user, token, safe_next(url_for("dashboard")))
    return render_template("login.html", token=token, email="")


@bp.route("/login/2fa", methods=["GET", "POST"])
@limiter.limit("10 per 15 minutes", methods=["POST"])
def login_2fa():
    p = session.get("pending_2fa")
    if not p or time.time() - p.get("ts", 0) > 600:
        session.pop("pending_2fa", None)
        flash("Please log in again.")
        return redirect(url_for("auth.login"))
    user = q("SELECT * FROM users WHERE id=?", (S.to_int(p.get("uid")) or 0,), one=True)
    if not user or not user["totp_on"]:
        session.pop("pending_2fa", None)
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        code = S.clean_text(request.form.get("code"), 40)
        step = totp.verify(user["totp_secret"], code, user["totp_last"] or 0)
        used_recovery = False
        if step is None:                      # maybe a one-time recovery code
            norm = code.lower().replace("-", "").replace(" ", "")
            hashes = json.loads(user["recovery"] or "[]")
            if norm and S.sha(norm) in hashes:
                hashes.remove(S.sha(norm))
                ex("UPDATE users SET recovery=? WHERE id=?", (json.dumps(hashes), user["id"]))
                used_recovery = True
        if step is None and not used_recovery:
            flash("That code didn't work. Try the newest code from your authenticator app.")
            return render_template("login_2fa.html"), 401
        if step is not None:
            ex("UPDATE users SET totp_last=? WHERE id=?", (step, user["id"]))
        session.pop("pending_2fa", None)
        if used_recovery:
            flash("Recovery code used. Set up two-factor again from Account if you lost your device.")
        return finish_login(user, p.get("invite", ""), p.get("nxt"))
    return render_template("login_2fa.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("landing"))


@bp.route("/invite/<token>")
def invite(token):
    inv = find_invite(token)
    if not inv:
        flash("This invite link is invalid or has expired.")
        return redirect(url_for("auth.login"))
    if g.user:
        wid = accept_invite(token, g.user)
        if wid:
            session["ws"] = wid
            flash("You've joined the workspace.")
            return redirect(url_for("dashboard"))
        flash(f"This invite was sent to {inv['email']}. Log in with that email.")
        return redirect(url_for("dashboard"))
    exists = q("SELECT 1 FROM users WHERE email=?", (inv["email"],), one=True)
    return redirect(url_for("auth.login" if exists else "auth.signup", invite=token))


@bp.route("/forgot", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def forgot():
    if request.method == "POST":
        user = q("SELECT * FROM users WHERE email=?", (S.clean_text(request.form.get("email"), 254).lower(),), one=True)
        if user:
            tok = ser("reset").dumps({"u": user["id"], "h": S.sha(user["password_hash"])[:16]})
            link = url_for("auth.reset", token=tok)
            sent = S.send_email(user["email"], f"Reset your {C.APP_NAME} password", f"Reset your password (valid 2 hours): {C.APP_URL}{link}\n\nIf you didn't ask for this, ignore this email.")
            dev_link(sent, link)
        flash("If that email is registered, a reset link is on its way.")
        return redirect(url_for("auth.login"))
    return render_template("forgot.html")


@bp.route("/reset/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def reset(token):
    try:
        d = ser("reset").loads(token, max_age=7200)
        user = q("SELECT * FROM users WHERE id=?", (d["u"],), one=True)
        if not user or S.sha(user["password_hash"])[:16] != d["h"]:
            raise BadSignature("used")
    except (BadSignature, SignatureExpired):
        flash("That reset link is invalid or has expired.")
        return redirect(url_for("auth.forgot"))
    if request.method == "POST":
        pw = request.form.get("password", "")
        err = check_password(pw, user["email"])
        if err:
            flash(err)
            return render_template("reset.html"), 400
        ex("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(pw), user["id"]))
        S.audit("password_reset", "", uid=user["id"], wid=None)
        flash("Password updated. Please log in.")
        return redirect(url_for("auth.login"))
    return render_template("reset.html")


@bp.route("/verify/<token>")
def verify(token):
    try:
        uid = ser("verify").loads(token, max_age=7 * 86400)
        ex("UPDATE users SET email_verified=1 WHERE id=?", (uid,))
        flash("Email verified. Thank you!")
    except (BadSignature, SignatureExpired):
        flash("That verification link is invalid or expired. Request a new one from your Account page.")
    return redirect(url_for("dashboard") if g.user else url_for("auth.login"))


@bp.route("/workspace/new", methods=["GET", "POST"])
def new_workspace():
    """For users who were removed from every workspace: start a fresh one."""
    if g.ws:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        wid = S.create_workspace(g.user["id"], S.clean_text(request.form.get("name"), 80) or "My workspace")
        session["ws"] = wid
        return redirect(url_for("dashboard"))
    return render_template("new_workspace.html")


@bp.route("/switch/<int:wid>", methods=["POST"])
def switch_ws(wid):
    if q("SELECT 1 FROM memberships WHERE workspace_id=? AND user_id=?", (wid, g.user["id"]), one=True):
        session["ws"] = wid
    session.pop("support_ws", None)
    return redirect(url_for("dashboard"))
