"""Post straight to Instagram, through Meta's Graph API (free to use).

How Meta publishing works, and why the code looks like this
-----------------------------------------------------------
Publishing is two calls, not one. First you create a "media container" that points at a **public
image URL**; then you publish that container. Meta's own servers fetch the picture, so the image
has to sit on an address the open internet can reach. That is why this only works once Debut is
deployed and APP_URL is a real https address - an image on your laptop can never be posted.

Three things Meta requires, none of which cost money:
  1. The Instagram account must be a **Business or Creator** account (not personal).
  2. It must be linked to a **Facebook Page**.
  3. Your Meta app needs the permissions instagram_basic, instagram_content_publish and
     pages_show_list, which means going through Meta's App Review once.

Until all three are in place, Debut falls back to "post helper" mode: at the scheduled time it
notifies you with the caption ready to copy and the image ready to download, so posting by hand
takes two taps instead of six. Nothing is lost while you wait for Meta's review.
"""
import datetime as dt
import logging

import requests
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

import config as C
import services as S
from db import ex, ins, q

log = logging.getLogger(__name__)
bp = Blueprint("social", __name__)

GRAPH = "https://graph.facebook.com/" + getattr(C, "META_API_VER", "v21.0")
TIMEOUT = 20
PLATFORMS = {"instagram": "Instagram", "facebook": "Facebook Page", "linkedin": "LinkedIn"}
LINKEDIN_API = "https://api.linkedin.com/v2"


def _stamp():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _next(default):
    n = request.values.get("next", "")
    return n if n.startswith("/") and not n.startswith("//") else default


class SocialError(Exception):
    """Something Meta refused, phrased so a shop owner can act on it."""


# ----------------------------------------------------------------- talking to Meta
def _call(method, path, **params):
    url = path if path.startswith("http") else f"{GRAPH}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, params=params if method == "GET" else None,
                             data=None if method == "GET" else params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise SocialError("Could not reach Instagram just now. Check the server's internet connection and try again.") from e
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code >= 400 or "error" in body:
        err = (body.get("error") or {})
        raise SocialError(_friendly(err, r.status_code))
    return body


def _friendly(err, status):
    """Meta's errors are written for developers. Say what the person should actually do."""
    msg = err.get("message") or f"Instagram said no (error {status})."
    code, sub = err.get("code"), err.get("error_subcode")
    if code == 190 or sub in (458, 463, 467):
        return "Instagram has signed Debut out. Open Publishing settings and connect the account again."
    if code in (10, 200, 3):
        return ("Instagram has not granted permission to post yet. The account must be a Business or Creator "
                "account linked to a Facebook Page, and your Meta app needs the instagram_content_publish permission.")
    if code == 4 or code == 17 or sub == 2207051:
        return "Instagram's hourly posting limit has been reached. Debut will try again later."
    if sub in (2207003, 2207004, 2207020, 2207053):
        return "Instagram could not download the picture. It must be a public JPG or PNG under 8 MB."
    if sub == 2207032:
        return "Instagram rejected the picture's shape. Use a square or portrait image (between 4:5 and 1.91:1)."
    return msg


# ----------------------------------------------------------------- accounts
def accounts(ws_id, platform=None):
    if platform:
        return q("SELECT * FROM social_accounts WHERE workspace_id=? AND platform=? ORDER BY id", (ws_id, platform))
    return q("SELECT * FROM social_accounts WHERE workspace_id=? ORDER BY id", (ws_id,))


def account(ws_id, platform="instagram"):
    rows = accounts(ws_id, platform)
    return rows[0] if rows else None


def connected(ws_id):
    return bool(accounts(ws_id))


def configured():
    """True when this server has a Meta app set up at all. Without it, nobody can connect."""
    return bool(getattr(C, "META_APP_ID", "") and getattr(C, "META_APP_SECRET", ""))


def connect(ws_id, user_token):
    """Swap a short-lived Facebook login token for a long-lived Page token, and save every Instagram
    account that token can post to. Returns how many were saved."""
    if not configured():
        raise SocialError("This server has no Meta app set up yet. Add META_APP_ID and META_APP_SECRET, then try again.")
    user_token = (user_token or "").strip()
    if not user_token:
        raise SocialError("Paste the access token first.")
    long = _call("GET", "oauth/access_token", grant_type="fb_exchange_token", client_id=C.META_APP_ID,
                 client_secret=C.META_APP_SECRET, fb_exchange_token=user_token).get("access_token") or user_token
    pages = _call("GET", "me/accounts", access_token=long,
                  fields="id,name,access_token,instagram_business_account{id,username}").get("data") or []
    if not pages:
        raise SocialError("That login manages no Facebook Pages. Instagram posting needs a Page linked to the account.")
    saved = 0
    for p in pages:
        igc = p.get("instagram_business_account") or {}
        tok = p.get("access_token") or long
        if igc.get("id"):
            _save(ws_id, "instagram", igc["id"], p["id"], igc.get("username") or p.get("name") or "Instagram", tok)
            saved += 1
        _save(ws_id, "facebook", p["id"], p["id"], p.get("name") or "Facebook Page", tok)
    if not saved:
        raise SocialError("No Instagram Business account is linked to those Pages. In the Instagram app: "
                          "Settings → Account type → switch to Business, then link your Facebook Page.")
    S.audit("social_connect", f"{saved} Instagram account(s)")
    return saved


def _save(ws_id, platform, account_id, page_id, name, token):
    row = q("SELECT id FROM social_accounts WHERE workspace_id=? AND platform=? AND account_id=?",
            (ws_id, platform, account_id))
    if row:
        ex("UPDATE social_accounts SET token=?, name=?, page_id=?, status='ok', last_error='' WHERE id=?",
           (token, name, page_id, row[0]["id"]))
    else:
        ins("social_accounts", dict(workspace_id=ws_id, platform=platform, account_id=account_id,
                                    page_id=page_id, name=name, token=token, status="ok"))


def disconnect(ws_id, acct_id):
    ex("DELETE FROM social_accounts WHERE workspace_id=? AND id=?", (ws_id, acct_id))
    S.audit("social_disconnect", str(acct_id))


# ----------------------------------------------------------------- publishing
def publish(acct, image_url, caption):
    """Create the container, then publish it. Returns Instagram's media id."""
    if not image_url:
        raise SocialError("This post has no picture yet. Design one in Create, or add an image link.")
    if image_url.startswith(("http://127.", "http://localhost", "https://127.", "https://localhost")):
        raise SocialError("Instagram cannot reach a picture on this computer. Deploy Debut and set APP_URL to your real web address.")
    if acct["platform"] == "linkedin":
        return _linkedin_post(acct, image_url, caption)
    if acct["platform"] == "facebook":
        out = _call("POST", f"{acct['page_id']}/photos", url=image_url, caption=caption or "",
                    access_token=acct["token"])
        return out.get("post_id") or out.get("id") or ""
    box = _call("POST", f"{acct['account_id']}/media", image_url=image_url, caption=(caption or "")[:2200],
                access_token=acct["token"])
    if not box.get("id"):
        raise SocialError("Instagram did not accept the picture.")
    out = _call("POST", f"{acct['account_id']}/media_publish", creation_id=box["id"], access_token=acct["token"])
    return out.get("id") or ""


def queue(ws_id, content_id, when, platform="instagram", user_id=None):
    """Line a content item up to go out at `when` (an ISO 'YYYY-MM-DD HH:MM' string, server time)."""
    ex("DELETE FROM publish_jobs WHERE workspace_id=? AND content_id=? AND platform=? AND status='queued'",
       (ws_id, content_id, platform))
    ins("publish_jobs", dict(workspace_id=ws_id, content_id=content_id, platform=platform,
                             publish_at=when, status="queued", created_by=user_id or 0))
    S.audit("publish_queue", f"content {content_id} → {PLATFORMS.get(platform, platform)} at {when}")


def cancel(ws_id, job_id):
    ex("UPDATE publish_jobs SET status='cancelled' WHERE workspace_id=? AND id=? AND status='queued'", (ws_id, job_id))
    S.audit("publish_cancel", str(job_id))


def jobs_for(ws_id, content_id):
    return q("SELECT * FROM publish_jobs WHERE workspace_id=? AND content_id=? ORDER BY id DESC", (ws_id, content_id))


def due_jobs(now=None):
    now = (now or dt.datetime.now()).strftime("%Y-%m-%d %H:%M")
    return q("SELECT * FROM publish_jobs WHERE status='queued' AND publish_at<=? ORDER BY id LIMIT 50", (now,))


def publish_due(now=None):
    """Called by the background job runner. Sends everything whose time has come.

    When the workspace has no connected account, the job does not fail: it becomes a 'post helper'
    notification with the caption and picture ready, so the post still goes out by hand on time."""
    sent = helped = failed = 0
    for job in due_jobs(now):
        rows = q("SELECT * FROM content_items WHERE workspace_id=? AND id=?", (job["workspace_id"], job["content_id"]))
        if not rows:
            ex("UPDATE publish_jobs SET status='cancelled', error=? WHERE id=?", ("The post was deleted.", job["id"]))
            continue
        item = rows[0]
        caption = "\n\n".join(x for x in ((item["copy"] or "").strip(), (item["hashtags"] or "").strip()) if x)
        image = S.media_url(item["asset_url"] or "")
        acct = account(job["workspace_id"], job["platform"])
        link = f"/m/content_items/{item['id']}/edit"
        if not acct:
            ex("UPDATE publish_jobs SET status='helper', sent_at=? WHERE id=?", (_stamp(), job["id"]))
            _notify(job, f"📲 Time to post “{item['title']}”. Tap to copy the caption and download the picture.", link)
            helped += 1
            continue
        try:
            mid = publish(acct, image, caption)
            ex("UPDATE publish_jobs SET status='sent', media_id=?, sent_at=?, error='' WHERE id=?",
               (mid, _stamp(), job["id"]))
            ex("UPDATE content_items SET status='Published' WHERE workspace_id=? AND id=?",
               (job["workspace_id"], item["id"]))
            _notify(job, f"✅ “{item['title']}” is live on {PLATFORMS.get(job['platform'], job['platform'])}.", link)
            sent += 1
        except SocialError as e:
            ex("UPDATE publish_jobs SET status='failed', error=? WHERE id=?", (str(e)[:400], job["id"]))
            ex("UPDATE social_accounts SET status='error', last_error=? WHERE id=?", (str(e)[:400], acct["id"]))
            _notify(job, f"⚠ “{item['title']}” could not be posted: {e}", link)
            failed += 1
        except Exception as e:                                   # never let one bad post stop the queue
            log.exception("publish failed")
            ex("UPDATE publish_jobs SET status='failed', error=? WHERE id=?", (str(e)[:400], job["id"]))
            failed += 1
    return dict(sent=sent, helper=helped, failed=failed)


def _notify(job, message, link):
    try:
        for m in q("SELECT user_id FROM memberships WHERE workspace_id=? AND role IN ('owner','admin','lead','manager')",
                   (job["workspace_id"],)):
            S.notify(job["workspace_id"], m["user_id"], "publish", message, link)
    except Exception:
        log.exception("publish notify failed")


# ----------------------------------------------------------------- pages
@bp.route("/publishing")
@S.roles("owner", "admin", "lead", "manager")
def publishing():
    ws = g.ws
    rows = accounts(ws["id"])
    upcoming = q("""SELECT p.*, c.title FROM publish_jobs p LEFT JOIN content_items c ON c.id = p.content_id
                    WHERE p.workspace_id=? ORDER BY p.id DESC LIMIT 25""", (ws["id"],))
    return render_template("publishing.html", accounts=rows, jobs=upcoming, configured=configured(),
                           top=top_posts(ws["id"]),
                           public=not any(x in S.app_url() for x in ("127.0.0.1", "localhost")),
                           app_url=S.app_url(), labels=PLATFORMS)


@bp.route("/publishing/connect", methods=["POST"])
@S.roles("owner", "admin")
def publishing_connect():
    try:
        n = connect(g.ws["id"], request.form.get("token", ""))
        flash(f"Connected. {n} Instagram account{'s' if n != 1 else ''} ready to post to. 🎉")
    except SocialError as e:
        flash(str(e))
    return redirect(url_for("social.publishing"))


@bp.route("/publishing/connect-linkedin", methods=["POST"])
@S.roles("owner", "admin")
def publishing_connect_linkedin():
    try:
        connect_linkedin(g.ws["id"], request.form.get("token", ""), request.form.get("author", ""),
                         request.form.get("org", ""))
        flash("LinkedIn connected. 🎉")
    except SocialError as e:
        flash(str(e))
    return redirect(url_for("social.publishing"))


@bp.route("/publishing/refresh", methods=["POST"])
@S.roles("owner", "admin", "lead", "manager")
def publishing_refresh():
    got = fetch_insights(g.ws["id"])
    if not got.get("ok"):
        flash(got.get("why") or "Could not get the numbers from Instagram.")
    else:
        bits = []
        if got.get("followers") is not None:
            bits.append(f"{got['followers']} followers")
        if got.get("reach") is not None:
            bits.append(f"{got['reach']} reached")
        bits.append(f"{got['posts']} post{'s' if got['posts'] != 1 else ''} updated")
        flash("Numbers brought in from Instagram: " + ", ".join(bits) + ". \U0001f4ca")
    return redirect(_next(url_for("social.publishing")))


@bp.route("/publishing/disconnect", methods=["POST"])
@S.roles("owner", "admin")
def publishing_disconnect():
    disconnect(g.ws["id"], request.form.get("id", type=int) or 0)
    flash("Account removed. Scheduled posts will fall back to the post helper.")
    return redirect(url_for("social.publishing"))


@bp.route("/publishing/schedule/<int:cid>", methods=["POST"])
@S.roles("owner", "admin", "lead", "manager")
def publishing_schedule(cid):
    when = (request.form.get("when") or "").replace("T", " ")[:16]
    platform = request.form.get("platform") or "instagram"
    if not when:
        flash("Pick a date and time first.")
    else:
        queue(g.ws["id"], cid, when, platform, g.user["id"])
        flash("Scheduled. " + ("Debut will post it for you." if account(g.ws["id"], platform)
                               else "No account is connected yet, so Debut will remind you with the caption ready to copy."))
    return redirect(_next(url_for("m_edit", key="content_items", rid=cid)))


@bp.route("/publishing/cancel", methods=["POST"])
@S.roles("owner", "admin", "lead", "manager")
def publishing_cancel():
    cancel(g.ws["id"], request.form.get("id", type=int) or 0)
    flash("Scheduled post cancelled.")
    return redirect(_next(url_for("social.publishing")))


@bp.route("/publishing/now/<int:cid>", methods=["POST"])
@S.roles("owner", "admin", "lead", "manager")
def publishing_now(cid):
    queue(g.ws["id"], cid, (dt.datetime.now() - dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"),
          request.form.get("platform") or "instagram", g.user["id"])
    out = publish_due()
    flash("Posted to Instagram. 🎉" if out["sent"] else
          ("Could not post it - see Publishing for the reason." if out["failed"] else
           "No Instagram account is connected yet, so Debut saved it as a post helper instead."))
    return redirect(_next(url_for("m_edit", key="content_items", rid=cid)))

# When to post, by industry. These are starting points for India, not laws: lunch break and the
# post-dinner scroll are when most people are actually on their phones. Once a workspace has
# published a few posts through Debut, best_time() prefers whatever has worked for them.
BEST_HOUR = {
    "hospitality": (12, "just before people decide where to eat"),
    "d2c": (20, "the evening scroll, when people shop on their phones"),
    "fmcg": (18, "on the way home, when shopping is on the mind"),
    "retail": (18, "early evening, before store-closing time"),
    "fashion": (20, "evening, when browsing turns into buying"),
    "saas": (11, "mid-morning on a working day"),
    "b2b": (10, "early in the working day, before meetings take over"),
    "agency": (11, "mid-morning, when clients are at their desks"),
    "startup": (9, "first thing, while people are catching up on news"),
    "fintech": (10, "a working-hours topic, read at a desk"),
    "realestate": (19, "evening, when families talk about moving"),
    "education": (17, "after school and college hours"),
    "healthcare": (9, "morning, when people plan appointments"),
    "personal_brand": (20, "evening, when your audience is relaxing"),
    "general": (19, "early evening, when most people are on their phones"),
}


def best_time(ws, when=None):
    """Suggest the next sensible slot to post. Returns (datetime-local string, plain-English reason)."""
    base = when or dt.datetime.now()
    hour, why = BEST_HOUR.get((ws["industry"] if "industry" in ws.keys() else "") or "general", BEST_HOUR["general"])
    learned = q("""SELECT publish_at FROM publish_jobs WHERE workspace_id=? AND status='sent'
                   ORDER BY id DESC LIMIT 10""", (ws["id"],))
    hours = [int(r["publish_at"][11:13]) for r in learned if len(r["publish_at"] or "") >= 13 and r["publish_at"][11:13].isdigit()]
    if len(hours) >= 3:
        hour = max(set(hours), key=hours.count)
        why = "the time you usually post"
    slot = base.replace(hour=hour, minute=0, second=0, microsecond=0)
    if slot <= base + dt.timedelta(minutes=5):
        slot += dt.timedelta(days=1)
    return slot.strftime("%Y-%m-%dT%H:%M"), why

def _linkedin_post(acct, image_url, caption):
    """LinkedIn posts a share that carries the picture as a link preview. One call, unlike Meta's two.
    The account is connected by pasting a token from LinkedIn's developer portal, same as Meta."""
    body = {
        "author": f"urn:li:person:{acct['account_id']}" if acct["page_id"] in ("", "person")
                  else f"urn:li:organization:{acct['page_id']}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": {
            "shareCommentary": {"text": (caption or "")[:3000]},
            "shareMediaCategory": "ARTICLE" if image_url else "NONE",
            **({"media": [{"status": "READY", "originalUrl": image_url}]} if image_url else {}),
        }},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    try:
        r = requests.post(f"{LINKEDIN_API}/ugcPosts", json=body, timeout=TIMEOUT,
                          headers={"Authorization": f"Bearer {acct['token']}", "X-Restli-Protocol-Version": "2.0.0"})
    except requests.RequestException as e:
        raise SocialError("Could not reach LinkedIn just now. Try again in a minute.") from e
    if r.status_code == 401:
        raise SocialError("LinkedIn has signed Debut out. Open Publishing settings and connect the account again.")
    if r.status_code == 403:
        raise SocialError("LinkedIn has not granted permission to post yet. Your LinkedIn app needs the w_member_social permission.")
    if r.status_code >= 400:
        raise SocialError(f"LinkedIn refused the post ({r.status_code}). Check the caption length and the picture link.")
    return r.headers.get("x-restli-id") or (r.json() or {}).get("id") or ""


def connect_linkedin(ws_id, token, author_id, org_id=""):
    """LinkedIn has no 'list my pages' step that works without extra review, so the person pastes the
    member or organisation id along with the token. Fiddly once, then never again."""
    token, author_id = (token or "").strip(), (author_id or "").strip()
    if not token or not author_id:
        raise SocialError("Paste both the LinkedIn access token and your member or organisation id.")
    _save(ws_id, "linkedin", author_id, (org_id or "").strip() or "person",
          ("LinkedIn page" if org_id else "LinkedIn profile"), token)
    S.audit("social_connect", "LinkedIn")
    return 1

# ----------------------------------------------------------------- numbers back from the platforms
# Instagram gives two kinds of number: how the account is doing (followers, reach, profile views) and
# how each post did. Debut asks for both, writes them into the Results Log so the Numbers page comes
# alive on its own, and keeps per-post rows so "what actually worked" is a real answer, not a guess.
ACCOUNT_METRICS = "reach,profile_views"
MEDIA_METRICS = {"IMAGE": "reach,likes,comments,saved,shares",
                 "CAROUSEL_ALBUM": "reach,likes,comments,saved,shares",
                 "VIDEO": "reach,likes,comments,saved,shares,views",
                 "REELS": "reach,likes,comments,saved,shares,views"}


def _metric_values(payload):
    out = {}
    for row in (payload.get("data") or []):
        name = row.get("name")
        vals = row.get("values") or []
        total = row.get("total_value") or {}
        if "value" in total:
            out[name] = total.get("value") or 0
        elif vals:
            out[name] = sum(int(v.get("value") or 0) for v in vals)
    return out


def fetch_insights(ws_id, days=7):
    """Pull the numbers back from Instagram. Returns a short summary; never raises."""
    acct = account(ws_id, "instagram")
    if not acct:
        return dict(ok=False, why="No Instagram account is connected yet.")
    got = dict(ok=True, posts=0, followers=None, reach=None, why="")
    try:
        prof = _call("GET", acct["account_id"], fields="followers_count,media_count", access_token=acct["token"])
        got["followers"] = prof.get("followers_count")
    except SocialError as e:
        return dict(ok=False, why=str(e))
    try:
        acc = _call("GET", f"{acct['account_id']}/insights", metric=ACCOUNT_METRICS,
                    period="day", access_token=acct["token"])
        got["reach"] = _metric_values(acc).get("reach")
    except SocialError:
        pass                                   # account insights need a few days of history; posts still work
    for job in q("""SELECT * FROM publish_jobs WHERE workspace_id=? AND status='sent' AND media_id<>''
                    ORDER BY id DESC LIMIT 30""", (ws_id,)):
        try:
            info = _call("GET", job["media_id"], fields="media_product_type,media_type,permalink",
                         access_token=acct["token"])
            kind = info.get("media_product_type") or info.get("media_type") or "IMAGE"
            met = _call("GET", f"{job['media_id']}/insights",
                        metric=MEDIA_METRICS.get(kind, MEDIA_METRICS["IMAGE"]), access_token=acct["token"])
        except SocialError:
            continue                           # one unreadable post must not stop the rest
        v = _metric_values(met)
        _save_stats(ws_id, job, v, info.get("permalink") or "")
        got["posts"] += 1
    _log_kpis(ws_id, got)
    ex("UPDATE social_accounts SET status='ok', last_error='' WHERE id=?", (acct["id"],))
    S.audit("insights_fetch", f"{got['posts']} posts, followers={got['followers']}")
    return got


def _save_stats(ws_id, job, v, permalink):
    row = q("SELECT id FROM post_stats WHERE workspace_id=? AND media_id=?", (ws_id, job["media_id"]))
    data = dict(reach=int(v.get("reach") or 0), likes=int(v.get("likes") or 0),
                comments=int(v.get("comments") or 0), saves=int(v.get("saved") or 0),
                shares=int(v.get("shares") or 0), views=int(v.get("views") or 0),
                permalink=permalink[:300], fetched_at=_stamp())
    if row:
        ex("""UPDATE post_stats SET reach=?, likes=?, comments=?, saves=?, shares=?, views=?,
               permalink=?, fetched_at=? WHERE id=?""",
           tuple(data.values()) + (row[0]["id"],))
    else:
        ins("post_stats", dict(workspace_id=ws_id, content_id=job["content_id"], platform=job["platform"],
                               media_id=job["media_id"], **data))


def _log_kpis(ws_id, got):
    """Write the headline numbers into the Results Log, one row per metric per day, so the charts fill in."""
    today = S.today().isoformat()
    for metric, value in (("Followers", got.get("followers")), ("Reach", got.get("reach"))):
        if value is None:
            continue
        have = q("""SELECT id FROM kpis WHERE workspace_id=? AND metric=? AND period=? AND channel='Instagram'""",
                 (ws_id, metric, today))
        if have:
            ex("UPDATE kpis SET value=? WHERE id=?", (str(value), have[0]["id"]))
        else:
            ins("kpis", dict(workspace_id=ws_id, metric=metric, channel="Instagram", period=today,
                             value=str(value), notes="Brought in from Instagram"))


def stats_for(ws_id, content_id):
    rows = q("SELECT * FROM post_stats WHERE workspace_id=? AND content_id=? ORDER BY id DESC LIMIT 1",
             (ws_id, content_id))
    return rows[0] if rows else None


def top_posts(ws_id, limit=5):
    return q("""SELECT s.*, c.title, c.format FROM post_stats s LEFT JOIN content_items c ON c.id = s.content_id
                WHERE s.workspace_id=? ORDER BY s.reach DESC, s.likes DESC LIMIT ?""", (ws_id, limit))


def refresh_all():
    """Called by the daily job: bring yesterday's numbers in for every workspace that has connected."""
    out = dict(workspaces=0, posts=0)
    for r in q("SELECT DISTINCT workspace_id FROM social_accounts WHERE platform='instagram'"):
        got = fetch_insights(r["workspace_id"])
        if got.get("ok"):
            out["workspaces"] += 1
            out["posts"] += got.get("posts") or 0
    return out
