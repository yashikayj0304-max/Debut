"""What is switched on, and what is quietly not.

Every one of these can be missing without a single error appearing anywhere a person would look:
email just doesn't arrive, images just disappear after a redeploy, Instagram publishing just
fails on the one post that mattered. The server knows all of it. This module turns that into
rows the owner can read, and each row says the one thing that fixes it rather than naming a
setting and leaving you to work out the rest.

A check never raises. A health screen that breaks when something is broken is worse than none.
"""
import os

import config as C
from db import q

OK, WARN, BAD, OFF = "ok", "warn", "bad", "off"

# How each state reads to someone who did not build this.
WORDS = {OK: "Working", WARN: "Needs a look", BAD: "Not working", OFF: "Switched off"}


def _rows_live(wid):
    """The two checks that need the database rather than the settings."""
    try:
        igs = q("SELECT name, status, last_error, checked_at FROM social_accounts WHERE workspace_id=? AND platform='instagram'", (wid,))
    except Exception:
        igs = []
    try:
        fails = q("SELECT COUNT(*) c FROM publish_jobs WHERE workspace_id=? AND status='failed'", (wid,), one=True)
        failed = fails["c"] if fails else 0
    except Exception:
        failed = 0
    return igs, failed


def _storage():
    if C.S3_BUCKET:
        return dict(key="storage", name="Picture storage", state=OK,
                    detail=f"Saved to S3 ({C.S3_BUCKET}), so they survive a restart.", fix="")
    writable = os.path.isdir(C.UPLOAD_DIR) and os.access(C.UPLOAD_DIR, os.W_OK)
    if not writable:
        return dict(key="storage", name="Picture storage", state=BAD,
                    detail="Debut cannot write to its uploads folder, so nothing can be uploaded at all.",
                    fix="Set S3_BUCKET, S3_REGION and your AWS keys, or give the server a writable uploads folder.")
    return dict(key="storage", name="Picture storage", state=WARN,
                detail="Pictures are saved on this server's own disk. On a host that wipes the disk when you "
                       "redeploy (Render's free plan does), every uploaded picture disappears - and because "
                       "Instagram fetches the picture from your site, posting breaks too.",
                fix="Set S3_BUCKET, S3_REGION, AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY. The code is already "
                    "there; it starts using S3 the moment those exist.")


def _email():
    if not C.SMTP_HOST:
        return dict(key="email", name="Email", state=WARN,
                    detail="No mail server is set up, so Debut sends nothing. Verification and password-reset "
                           "links are shown on screen instead, so nobody gets locked out - but invitations, "
                           "digests and client notifications never arrive.",
                    fix="Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and SMTP_FROM (Amazon SES, Resend "
                        "and Postmark all work), then send yourself a test from this page.")
    if "example.com" in (C.SMTP_FROM or ""):
        return dict(key="email", name="Email", state=WARN,
                    detail=f"Mail goes out through {C.SMTP_HOST}, but the from-address is still the placeholder.",
                    fix="Set SMTP_FROM to a real address on a domain you own, or mail will be marked as spam.")
    return dict(key="email", name="Email", state=OK, detail=f"Sending through {C.SMTP_HOST}.",
                fix="Send yourself a test below if you have not yet.")


def _address():
    url = C.APP_URL or ""
    if not url or "127.0.0.1" in url or "localhost" in url:
        return dict(key="url", name="Your web address", state=BAD,
                    detail="APP_URL still points at a development address. Every link Debut puts in an email, "
                           "a QR code or a link-in-bio page points somewhere nobody else can open.",
                    fix="Set APP_URL to your real https address, with no trailing slash.")
    if not url.startswith("https://"):
        return dict(key="url", name="Your web address", state=WARN,
                    detail=f"APP_URL is {url}, which is not https.",
                    fix="Instagram will not fetch pictures over plain http. Use your https address.")
    return dict(key="url", name="Your web address", state=OK, detail=url, fix="")


def _instagram(igs, failed):
    if not igs:
        return dict(key="instagram", name="Instagram posting", state=OFF,
                    detail="No Instagram account is connected, so Debut can only schedule posts for you to "
                           "put up by hand.",
                    fix="Connect one under Account → Connected accounts. You need an Instagram Business or "
                        "Creator account linked to a Facebook page.")
    broken = [r for r in igs if (r["status"] or "ok") != "ok"]
    names = ", ".join(r["name"] or "account" for r in igs)
    if broken:
        why = (broken[0]["last_error"] or "")[:120]
        return dict(key="instagram", name="Instagram posting", state=BAD,
                    detail=f"{names} is connected but the last attempt failed. {why}".strip(),
                    fix="Reconnect the account. Instagram tokens expire, and they expire silently.")
    if failed:
        return dict(key="instagram", name="Instagram posting", state=WARN,
                    detail=f"{names} is connected, and {failed} post{'s' if failed != 1 else ''} "
                           f"failed to go out.",
                    fix="Open Publishing to see which ones and why. A failed post is usually a picture "
                        "Instagram could not download from your site.")
    when = max((r["checked_at"] or "") for r in igs)
    return dict(key="instagram", name="Instagram posting", state=OK,
                detail=f"Connected: {names}." + (f" Last confirmed working {when}." if when else
                       " Debut checks every morning that the connection still works and emails you if it stops."),
                fix="")


def _ai():
    if not C.ANTHROPIC_API_KEY:
        return dict(key="ai", name="AI writing", state=OFF,
                    detail="No AI key, so Create and Deb fall back to their built-in structure instead of "
                           "writing anything. Nothing is broken; it is just quieter.",
                    fix="Set ANTHROPIC_API_KEY if you want AI drafts.")
    return dict(key="ai", name="AI writing", state=OK,
                detail="A key is set." + (f" Daily cap: {C.AI_DAILY_CAP} credits across all workspaces." if C.AI_DAILY_CAP else ""),
                fix="")


def _billing():
    if C.BILLING_MODE == "off":
        return dict(key="billing", name="Taking payments", state=OFF,
                    detail="Billing is switched off, so nobody is charged and nobody sees plans.", fix="")
    if C.BILLING_MODE == "demo":
        return dict(key="billing", name="Taking payments", state=WARN,
                    detail="Billing is in demo mode. People can pick a plan and it is applied without any "
                           "money changing hands.",
                    fix="Set RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET and RAZORPAY_WEBHOOK_SECRET to take real payments.")
    missing = [n for n, v in (("RAZORPAY_KEY_ID", C.RAZORPAY_KEY_ID), ("RAZORPAY_KEY_SECRET", C.RAZORPAY_KEY_SECRET),
                              ("RAZORPAY_WEBHOOK_SECRET", C.RAZORPAY_WEBHOOK_SECRET)) if not v]
    if missing:
        return dict(key="billing", name="Taking payments", state=BAD,
                    detail="Razorpay is switched on but " + " and ".join(missing) + " is missing, so "
                           "subscriptions cannot be created" +
                           (" and Razorpay's confirmations cannot be trusted" if not C.RAZORPAY_WEBHOOK_SECRET else "") + ".",
                    fix="Add the missing key from your Razorpay dashboard.")
    return dict(key="billing", name="Taking payments", state=OK, detail="Razorpay is live.", fix="")


def _database():
    url = C.DATABASE_URL or ""
    if url.startswith("sqlite"):
        return dict(key="db", name="Database", state=WARN if C.PROD else OK,
                    detail="Running on SQLite, in a file on this server." + (
                        " On a host that wipes the disk when you redeploy, that takes every account, post and "
                        "client with it." if C.PROD else " Fine for development."),
                    fix="Set DATABASE_URL to a Postgres database before real customers use this." if C.PROD else "")
    return dict(key="db", name="Database", state=OK, detail="Postgres, so your data survives a redeploy.",
                fix="Check your host's plan includes backups.")


def _errors():
    if not C.SENTRY_DSN:
        return dict(key="errors", name="Error reports", state=WARN,
                    detail="Nothing is collecting errors, so if a page breaks for someone you will only "
                           "hear about it if they tell you.",
                    fix="Set SENTRY_DSN (Sentry's free tier is plenty for one app).")
    return dict(key="errors", name="Error reports", state=OK, detail="Errors are being reported to Sentry.", fix="")


def checks(wid):
    """Every check, worst first, so the thing that needs doing is at the top."""
    igs, failed = _rows_live(wid)
    out = []
    for fn, args in ((_address, ()), (_storage, ()), (_email, ()), (_database, ()), (_instagram, (igs, failed)),
                     (_billing, ()), (_ai, ()), (_errors, ())):
        try:
            out.append(fn(*args))
        except Exception as e:      # a broken check must not hide the other seven
            out.append(dict(key=getattr(fn, "__name__", "?").strip("_"), name="Check failed", state=WARN,
                            detail=f"Debut could not run this check: {e}", fix=""))
    rank = {BAD: 0, WARN: 1, OFF: 2, OK: 3}
    out.sort(key=lambda r: rank.get(r["state"], 9))
    return out


def summary(rows):
    """One line for the top of the page, and for the nudge on the dashboard."""
    bad = [r for r in rows if r["state"] == BAD]
    warn = [r for r in rows if r["state"] == WARN]
    if bad:
        return BAD, f"{len(bad)} thing{'s' if len(bad) != 1 else ''} to fix before this is ready for customers"
    if warn:
        return WARN, f"{len(warn)} thing{'s' if len(warn) != 1 else ''} worth a look"
    return OK, "Everything Debut needs is switched on"
