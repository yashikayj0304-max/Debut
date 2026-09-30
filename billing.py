"""Subscriptions via Razorpay (INR, UPI AutoPay, cards). Demo mode lets you test plan changes locally without any payment gateway."""
import os, json, hmac, hashlib, datetime as dt
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, abort
from sqlalchemy.exc import IntegrityError
import config as C
import db as D
import services as S
from db import q, ex, ins
from extensions import csrf

bp = Blueprint("billing", __name__)
API = "https://api.razorpay.com/v1"


def _rzp(method, path, **kw):
    r = requests.request(method, API + path, auth=(C.RAZORPAY_KEY_ID, C.RAZORPAY_KEY_SECRET), timeout=20, **kw)
    if r.status_code >= 400:
        raise RuntimeError(r.text[:300])
    return r.json()


def _hmac(secret, msg):
    return hmac.new(secret.encode(), msg if isinstance(msg, bytes) else msg.encode(), hashlib.sha256).hexdigest()


def _ts_date(ts):
    try:
        return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date().isoformat()
    except Exception:
        return ""


@bp.route("/billing")
@S.roles("owner", "admin")
def billing():
    ws = g.ws
    seats = S.seats_used(ws["id"])
    return render_template("billing.html", plans=C.PLANS, mode=C.BILLING_MODE, key_id=C.RAZORPAY_KEY_ID, seats=seats, clients=S.clients_used(ws["id"]),
                           used=S.credits_used(ws["id"]), records=S.record_count(ws["id"]),
                           configured={k: bool(os.environ.get(C.PLANS[k].get("rzp_env", ""), "")) for k in C.PAID_PLANS})


@bp.route("/billing/subscribe/<plan>", methods=["POST"])
@S.roles("owner")
def subscribe(plan):
    if plan not in C.PAID_PLANS:
        abort(404)
    ws, info = g.ws, C.PLANS[plan]
    seats, clients = S.seats_used(ws["id"]), S.clients_used(ws["id"])
    if seats > info["seats"]:
        return jsonify(error=f"You have {seats} team members but {info['name']} allows {info['seats']}. Remove members first."), 400
    if clients > info["clients"]:
        return jsonify(error=f"You have {clients} client-portal members but {info['name']} allows {info['clients']}. Remove some first."), 400
    if C.BILLING_MODE == "demo":
        ex("UPDATE workspaces SET plan=?, plan_status='active', period_end=?, cancel_at_period_end=0, pending_plan='' WHERE id=?",
           (plan, (S.today() + dt.timedelta(days=30)).isoformat(), ws["id"]))
        S.audit("plan_demo", plan)
        return jsonify(demo=True)
    if C.BILLING_MODE != "razorpay":
        return jsonify(error="Billing is not configured yet."), 400
    if ws["rzp_subscription_id"] and ws["plan_status"] in S.ACTIVE_STATUSES and ws["plan"] in C.PAID_PLANS:
        return jsonify(error="You already have an active subscription. Cancel it first (it stays active until the period ends) or email support to change plans."), 400
    plan_id = os.environ.get(info["rzp_env"], "")
    if not plan_id:
        return jsonify(error=f"Razorpay plan ID for {info['name']} is not set (env {info['rzp_env']})."), 400
    try:
        sub = _rzp("POST", "/subscriptions", json={"plan_id": plan_id, "total_count": 120, "customer_notify": 1,
                                                   "notes": {"workspace_id": str(ws["id"]), "plan": plan}})
    except Exception as e:
        return jsonify(error="Could not start checkout: " + str(e)), 502
    ex("UPDATE workspaces SET rzp_subscription_id=?, pending_plan=? WHERE id=?", (sub["id"], plan, ws["id"]))
    return jsonify(key_id=C.RAZORPAY_KEY_ID, subscription_id=sub["id"], name=C.APP_NAME, description=f"{info['name']} plan", email=g.user["email"])


@bp.route("/billing/verify", methods=["POST"])
@S.roles("owner")
def verify():
    d = request.get_json(silent=True) or request.form
    pid, sid, sig = d.get("razorpay_payment_id", ""), d.get("razorpay_subscription_id", ""), d.get("razorpay_signature", "")
    if not (C.RAZORPAY_KEY_SECRET and pid and sid and sig) or sid != g.ws["rzp_subscription_id"]:
        return jsonify(error="Invalid payment response."), 400
    if not hmac.compare_digest(_hmac(C.RAZORPAY_KEY_SECRET, f"{pid}|{sid}"), sig):
        return jsonify(error="Signature mismatch."), 400
    ex("UPDATE workspaces SET plan=CASE WHEN pending_plan!='' THEN pending_plan ELSE plan END, plan_status='active', period_end=?, pending_plan='', cancel_at_period_end=0 WHERE id=?",
       ((S.today() + dt.timedelta(days=31)).isoformat(), g.ws["id"]))
    S.audit("subscribed", pid)
    return jsonify(ok=True)


@bp.route("/billing/cancel", methods=["POST"])
@S.roles("owner")
def cancel():
    ws = g.ws
    if C.BILLING_MODE == "demo":
        ex("UPDATE workspaces SET plan_status='cancelled', period_end=?, cancel_at_period_end=1 WHERE id=?", ((S.today() - dt.timedelta(days=1)).isoformat(), ws["id"]))  # demo: ends immediately
    elif ws["rzp_subscription_id"]:
        try:
            _rzp("POST", f"/subscriptions/{ws['rzp_subscription_id']}/cancel", json={"cancel_at_cycle_end": 1})
        except Exception as e:
            flash("Could not cancel: " + str(e))
            return redirect(url_for("billing.billing"))
        ex("UPDATE workspaces SET cancel_at_period_end=1 WHERE id=?", (ws["id"],))
    S.audit("cancel_requested")
    flash("Cancellation scheduled. Your plan stays active until the end of the paid period.")
    return redirect(url_for("billing.billing"))


STATUS_MAP = {"subscription.activated": "active", "subscription.charged": "active", "subscription.resumed": "active", "subscription.authenticated": "authenticated",
              "subscription.pending": "pending", "subscription.halted": "halted", "subscription.cancelled": "cancelled",
              "subscription.completed": "completed", "subscription.paused": "paused"}


@bp.route("/webhooks/razorpay", methods=["POST"])
@csrf.exempt
def webhook():
    body = request.get_data()
    sig = request.headers.get("X-Razorpay-Signature", "")
    if not C.RAZORPAY_WEBHOOK_SECRET or not hmac.compare_digest(_hmac(C.RAZORPAY_WEBHOOK_SECRET, body), sig):
        return "bad signature", 400
    ev = json.loads(body or b"{}")
    typ, eid = ev.get("event", ""), request.headers.get("X-Razorpay-Event-Id", "")
    if eid:
        try:
            ins("webhook_events", dict(event_id=eid, type=typ))
        except IntegrityError:
            D.conn().rollback()
            return "duplicate", 200
    sub = ev.get("payload", {}).get("subscription", {}).get("entity", {})
    ws = q("SELECT * FROM workspaces WHERE rzp_subscription_id=?", (sub.get("id", ""),), one=True) if sub.get("id") else None
    if ws and typ in STATUS_MAP:
        status = STATUS_MAP[typ]
        end = _ts_date(sub.get("current_end")) or ws["period_end"]
        new_plan = ws["pending_plan"] if (status == "active" and ws["pending_plan"]) else ws["plan"]
        ex("UPDATE workspaces SET plan_status=?, period_end=?, plan=?, pending_plan=CASE WHEN ?='active' THEN '' ELSE pending_plan END WHERE id=?",
           (status, end, new_plan, status, ws["id"]))
        S.audit("billing_" + status, typ, wid=ws["id"], uid=0)
    return "ok", 200
