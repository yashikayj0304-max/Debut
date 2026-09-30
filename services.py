"""Shared helpers: plans & limits, audit log, email, storage, URL safety, workspace seeding."""
import functools, os, re, uuid, socket, ipaddress, hashlib, secrets, smtplib, logging, datetime as dt
from email.message import EmailMessage
from urllib.parse import urlparse, urljoin
import requests
from flask import g, request, abort
import config as C
import db as D
from db import q, ex, ins
from modules import MODULES, CHECKLIST, FEEDS, KEY_DATES, OUTREACH, SEED_TABLES
import industries as IND

log = logging.getLogger("gtm")


def today():
    return dt.date.today()


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


# ------------------------------------------------------------------ plans
ACTIVE_STATUSES = {"active", "authenticated", "pending"}


def plan_key(ws):
    """The plan a workspace is *currently* entitled to. Expired trials and lapsed subscriptions fall back to Free (nothing is deleted)."""
    t = today().isoformat()
    p = ws["plan"]
    if p == "trial":
        return "trial" if (ws["trial_ends"] or "") >= t else "free"
    if p in C.PAID_PLANS:
        st = ws["plan_status"]
        if st in ACTIVE_STATUSES or (st in ("cancelled", "completed") and (ws["period_end"] or "") >= t):
            return p
    return "free"


def plan_of(ws):
    return C.PLANS[plan_key(ws)]


def feature_ok(ws, feature):
    return feature in plan_of(ws)["features"]


def month_key():
    return today().strftime("%Y-%m")


def credits_used(wid):
    r = q("SELECT COALESCE(SUM(credits),0) c FROM ai_usage WHERE workspace_id=? AND month=?", (wid, month_key()), one=True)
    return int(r["c"] or 0)


def record_count(wid):
    return sum(q(f"SELECT COUNT(*) c FROM {k} WHERE workspace_id=?", (wid,), one=True)["c"] for k in MODULES if k not in SEED_TABLES)


def trial_days_left(ws):
    if plan_key(ws) != "trial" or not ws["trial_ends"]:
        return None
    return (dt.date.fromisoformat(ws["trial_ends"]) - today()).days


# ------------------------------------------------------------------ audit / email
def audit(action, detail="", wid=None, uid=None):
    try:
        ins("audit_log", dict(workspace_id=wid if wid is not None else (g.ws["id"] if g.get("ws") else None),
                              user_id=uid if uid is not None else (g.user["id"] if g.get("user") else None), action=action, detail=detail[:300]))
    except Exception:  # auditing must never break a request
        log.exception("audit failed")


def send_email(to, subject, body):
    """Returns True if sent. Without SMTP configured, logs the message (dev) and returns False."""
    if not C.SMTP_HOST:
        log.info("EMAIL (not sent, no SMTP configured) to=%s subject=%s\n%s", to, subject, body)
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = C.SMTP_FROM, to, subject
    msg.set_content(body)
    try:
        # Port 465 is implicit TLS from the first byte (no STARTTLS handshake); everything else
        # (587, 25, custom) is plaintext-then-upgrade, and only upgraded if the server actually
        # advertises STARTTLS - some internal/trusted relays don't, and forcing it would just
        # crash the whole send instead of degrading gracefully.
        if C.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(C.SMTP_HOST, C.SMTP_PORT, timeout=15) as s:
                if C.SMTP_USER:
                    s.login(C.SMTP_USER, C.SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(C.SMTP_HOST, C.SMTP_PORT, timeout=15) as s:
                s.ehlo()
                if s.has_extn("STARTTLS"):
                    s.starttls()
                    s.ehlo()
                if C.SMTP_USER:
                    s.login(C.SMTP_USER, C.SMTP_PASSWORD)
                s.send_message(msg)
        return True
    except Exception:
        log.exception("email failed")
        return False


# ------------------------------------------------------------------ URL safety
def clean_url(v):
    v = (v or "").strip()
    if not v:
        return ""
    if re.match(r"^https?://[^\s]+$", v, re.I):
        return v[:2000]
    if re.match(r"^[\w-]+(\.[\w-]+)+(/[^\s]*)?$", v):
        return ("https://" + v)[:2000]
    return ""


def _blocked_ip(ip):
    ip = ipaddress.ip_address(ip)
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified


def assert_public_url(url):
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("bad url")
    for info in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80)):
        if _blocked_ip(info[4][0]):
            raise ValueError("blocked address")


def safe_get(url, timeout=8, limit=2_000_000, hops=3):
    """Fetch a user-supplied URL without letting it reach internal services (SSRF guard). Follows a few redirects, re-checking each."""
    for _ in range(hops + 1):
        assert_public_url(url)
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (GTM-Studio feed reader)"}, timeout=timeout, allow_redirects=False, stream=True)
        if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
            url = urljoin(url, r.headers.get("Location", ""))
            continue
        r.raise_for_status()
        data = b""
        for chunk in r.iter_content(65536):
            data += chunk
            if len(data) > limit:
                break
        return data
    raise ValueError("too many redirects")


# ------------------------------------------------------------------ files
_S3 = None


def s3():
    global _S3
    if _S3 is None:
        import boto3  # optional dependency, only needed when S3_BUCKET is set
        _S3 = boto3.client("s3", region_name=C.S3_REGION, endpoint_url=C.S3_ENDPOINT or None)
    return _S3


IMG_SIG = [(b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg"), (b"GIF87a", "gif"), (b"GIF89a", "gif")]


def sniff_image(data):
    for sig, ext in IMG_SIG:
        if data.startswith(sig):
            return ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def store_file(wid, ext, data):
    name = f"{uuid.uuid4().hex}.{ext}"
    if C.S3_BUCKET:
        s3().put_object(Bucket=C.S3_BUCKET, Key=f"{wid}/{name}", Body=data, ContentType=f"image/{'jpeg' if ext == 'jpg' else ext}")
        return f"s3:{wid}/{name}"
    d = os.path.join(C.UPLOAD_DIR, str(wid))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f:
        f.write(data)
    return f"/media/{wid}/{name}"


def media_url(content):
    content = content or ""
    if content.startswith("s3:"):
        return s3().generate_presigned_url("get_object", Params={"Bucket": C.S3_BUCKET, "Key": content[3:]}, ExpiresIn=3600)
    return content


def delete_file(content):
    try:
        if (content or "").startswith("s3:"):
            s3().delete_object(Bucket=C.S3_BUCKET, Key=content[3:])
        elif (content or "").startswith("/media/"):
            _, _, wid, name = content.split("/", 3)
            os.remove(os.path.join(C.UPLOAD_DIR, wid, os.path.basename(name)))
    except Exception:
        pass


# ------------------------------------------------------------------ workspaces
def make_slug(name):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "workspace"
    slug = base
    while q("SELECT 1 FROM workspaces WHERE slug=?", (slug,), one=True):
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug


def to_int(v, default=None):
    """Parse a user-supplied id safely (fits a 32-bit DB integer); returns default for junk."""
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        return default
    return n if 0 < n < 2**31 else default


def jbody():
    """JSON request body that must be an object; otherwise 400."""
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        abort(400)
    return d


def clean_text(v, n=5000):
    return str(v or "").replace("\x00", "").strip()[:n]


def can_assign(actor_role, new_role, target_role=None):
    """Role hierarchy check used by invites, role changes and removals."""
    r = C.RANK
    if new_role not in r or new_role == "owner" or actor_role not in r:
        return False
    if r[actor_role] <= r[new_role]:
        return False
    return target_role is None or r[actor_role] > r.get(target_role, 99)


def is_platform_admin(user):
    """Platform-owner access needs BOTH a listed email AND a verified mailbox (otherwise anyone could register the owner's address first)."""
    return bool(user) and bool(user["email_verified"]) and user["email"] in C.ADMIN_EMAILS and (bool(user["totp_on"]) or not C.REQUIRE_ADMIN_2FA)


def team_names(wid):
    return [m["name"] or m["email"] for m in q("SELECT u.name, u.email FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=? AND m.role!='client' ORDER BY m.id", (wid,))]


def seats_used(wid):
    """Seats are staff and freelancers. Client-portal members have their own, separate allowance."""
    return q("SELECT COUNT(*) c FROM memberships WHERE workspace_id=? AND role!='client'", (wid,), one=True)["c"]


def clients_used(wid):
    return q("SELECT COUNT(*) c FROM memberships WHERE workspace_id=? AND role='client'", (wid,), one=True)["c"]


def client_members(wid, client_name):
    """Portal users belonging to one client (matched case-insensitively on the client name)."""
    n = (client_name or "").strip().lower()
    if not n:
        return []
    return [m for m in q("SELECT m.client_name, u.id AS uid, u.name, u.email FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=? AND m.role='client'", (wid,))
            if (m["client_name"] or "").strip().lower() == n]


def apply_industry(wid, industry, personas=False):
    """Add an industry's checklist items, key dates and news feeds (skipping ones already present). Optionally personas. Returns counts."""
    ind = IND.get(industry)
    n = dict(checklist=0, dates=0, feeds=0, personas=0)
    have = {r["item"] for r in q("SELECT item FROM launch_checklist WHERE workspace_id=?", (wid,))}
    for ph, items in ind["checklist"].items():
        for it in items:
            if it not in have:
                ins("launch_checklist", dict(workspace_id=wid, item=it, phase=ph, status="To do"))
                n["checklist"] += 1
    y = today().year
    have = {(r["name"], r["date"]) for r in q("SELECT name, date FROM key_dates WHERE workspace_id=?", (wid,))}
    for name, md, kind in ind["key_dates"]:
        for yy in (y, y + 1):
            if (name, f"{yy}-{md}") not in have:
                ins("key_dates", dict(workspace_id=wid, name=name, date=f"{yy}-{md}", kind=kind))
                n["dates"] += 1
    have = {r["url"] for r in q("SELECT url FROM feeds WHERE workspace_id=?", (wid,))}
    for name, url, cat in ind["feeds"]:
        if url not in have:
            ins("feeds", dict(workspace_id=wid, name=name, url=url, category=cat))
            n["feeds"] += 1
    if personas:
        have = {r["name"] for r in q("SELECT name FROM personas WHERE workspace_id=?", (wid,))}
        for p in ind["personas"]:
            if p["name"] not in have:
                ins("personas", dict(p, workspace_id=wid))
                n["personas"] += 1
    return n


def seed_watch(wid, industry):
    """Starter Market Pulse watchlist for the industry (skips terms already present)."""
    have = {r["term"].lower() for r in q("SELECT term FROM watchlist WHERE workspace_id=?", (wid,))}
    n = 0
    for term, typ, reg in IND.WATCH.get(industry, IND.WATCH["general"]):
        if term.lower() not in have:
            ins("watchlist", dict(workspace_id=wid, term=term, type=typ, region=reg))
            n += 1
    return n


def seed_workspace(wid, industry="general", kit=False):
    for ph, items in CHECKLIST.items():
        for it in items:
            ins("launch_checklist", dict(workspace_id=wid, item=it, phase=ph, status="To do"))
    for n, u, c in FEEDS:
        ins("feeds", dict(workspace_id=wid, name=n, url=u, category=c))
    y = today().year
    for name, md, kind in KEY_DATES:
        for yy in (y, y + 1):
            ins("key_dates", dict(workspace_id=wid, name=name, date=f"{yy}-{md}", kind=kind))
    for n, ch, au, su, bo in OUTREACH:
        ins("outreach_templates", dict(workspace_id=wid, name=n, channel=ch, audience=au, subject=su, body=bo))
    for sv, un in [("Blog article (SEO)", "per word"), ("Website copy", "per project"), ("Social media pack (12 posts)", "per month"), ("Video script", "per piece"),
                   ("Email newsletter", "per piece"), ("Case study", "per piece"), ("Press release", "per piece"), ("Product descriptions", "per piece"), ("Short video edit", "per video")]:
        ins("rate_card", dict(workspace_id=wid, service=sv, unit=un))
    seed_watch(wid, industry)
    if industry != "general":
        apply_industry(wid, industry, personas=kit)


def create_workspace(user_id, name, industry="general", kit=False):
    industry = industry if industry in IND.INDUSTRIES else "general"
    wid = ins("workspaces", dict(name=name[:80], slug=make_slug(name), plan="trial", plan_status="trialing", industry=industry, ics_key=secrets.token_hex(6), hook_key=secrets.token_hex(12),
                                 trial_ends=(today() + dt.timedelta(days=C.TRIAL_DAYS)).isoformat(), owner_id=user_id))
    ins("memberships", dict(workspace_id=wid, user_id=user_id, role="owner"))
    seed_workspace(wid, industry, kit)
    return wid


def delete_workspace_data(wid):
    for it in q("SELECT content FROM board_items WHERE workspace_id=? AND kind='image'", (wid,)):
        delete_file(it["content"])
    for t in list(MODULES) + ["boards", "board_items", "memberships", "invites", "ai_usage", "comments", "notifications", "api_keys", "feedback", "pulse_runs"]:
        ex(f"DELETE FROM {t} WHERE workspace_id=?", (wid,))
    ex("DELETE FROM audit_log WHERE workspace_id=?", (wid,))
    ex("DELETE FROM workspaces WHERE id=?", (wid,))


# ------------------------------------------------------------------ access control


def roles(*allowed):
    def deco(f):
        @functools.wraps(f)
        def w(*a, **k):
            if g.get("role") not in allowed:
                abort(403)
            return f(*a, **k)
        return w
    return deco


# ------------------------------------------------------------------ collaboration: members, mentions, notifications, digests
def members(wid, clients=False):
    """Workspace members for assignment, @mentions and approvals. Portal clients are excluded unless asked for."""
    return q("SELECT m.role, u.id AS uid, u.name, u.email FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=?" + ("" if clients else " AND m.role!='client'") + " ORDER BY m.id", (wid,))


def find_member(wid, text):
    """Match free text typed in an assignee/owner field to a workspace member (full name or email, case-insensitive)."""
    t = (text or "").strip().lower()
    if not t:
        return None
    for m in members(wid):
        if t in ((m["name"] or "").strip().lower(), (m["email"] or "").lower()):
            return m
    return None


def mentioned_ids(wid, text):
    """User ids @mentioned in a comment: '@Full Name' or '@FirstName' (first names only when unique)."""
    low = (text or "").lower()
    ms = members(wid)
    firsts = [((m["name"] or "").split() or [""])[0].lower() for m in ms]
    out = set()
    for m, first in zip(ms, firsts):
        full = (m["name"] or "").strip().lower()
        if (full and "@" + full in low) or (first and firsts.count(first) == 1 and re.search(r"@" + re.escape(first) + r"\b", low)):
            out.add(m["uid"])
    return out


def notify(wid, uid, kind, message, link=""):
    if uid:
        try:
            ins("notifications", dict(workspace_id=wid, user_id=uid, kind=kind, message=message[:300], link=link[:300]))
        except Exception:
            log.exception("notify failed")


def unread_count(uid, wid):
    return q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND workspace_id=? AND is_read=0", (uid, wid), one=True)["c"]


def digest_text(user):
    """Plain-text daily digest for one user across their workspaces; None when there is nothing to say."""
    t = today()
    t0, t3 = t.isoformat(), (t + dt.timedelta(days=3)).isoformat()
    keys = {(user["name"] or "").strip().lower(), (user["email"] or "").lower()} - {""}
    blocks = []
    for m in q("SELECT m.role, w.id AS wid, w.name FROM memberships m JOIN workspaces w ON w.id=m.workspace_id WHERE m.user_id=? AND m.role!='client'", (user["id"],)):
        w, lines = m["wid"], []
        mine = [x for x in q("SELECT * FROM tasks WHERE workspace_id=? AND status!='Done' AND due_date!='' AND due_date<=? ORDER BY due_date LIMIT 200", (w, t3)) if (x["assignee"] or "").strip().lower() in keys]
        lines += [f"  - {'OVERDUE ' if x['due_date'] < t0 else 'due ' + x['due_date'] + ': '}{x['title']}" for x in mine[:10]]
        pub = [x for x in q("SELECT * FROM content_items WHERE workspace_id=? AND status!='Published' AND publish_date BETWEEN ? AND ? ORDER BY publish_date LIMIT 200", (w, t0, t3)) if (x["owner"] or "").strip().lower() in keys]
        lines += [f"  - publishing {x['publish_date']}: {x['title']} [{x['status']}]" for x in pub[:10]]
        if m["role"] in C.TEAM_MANAGERS:
            n = q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status='Review'", (w,), one=True)["c"] + q("SELECT COUNT(*) c FROM content_orders WHERE workspace_id=? AND status IN ('Editing / QA','Client review')", (w,), one=True)["c"]
            if n:
                lines.append(f"  - {n} item(s) waiting for your approval")
        if lines:
            blocks.append(f"{m['name']}\n" + "\n".join(lines))
    if not blocks:
        return None
    from itsdangerous import URLSafeSerializer
    unsub = C.APP_URL + "/unsubscribe/" + URLSafeSerializer(C.SECRET_KEY, salt="unsub").dumps(user["id"])
    return f"Hi {user['name'] or ''},\n\nHere is what needs you:\n\n" + "\n\n".join(blocks) + f"\n\nOpen {C.APP_NAME}: {C.APP_URL}/app\n\nStop these emails: {unsub}\n"


def send_digests():
    """Run daily from cron: `python manage.py send-digests`. Only verified users who haven't opted out; only when there is something to report."""
    sent = 0
    for u in q("SELECT * FROM users WHERE digest=1 AND email_verified=1"):
        body = digest_text(u)
        if body and send_email(u["email"], f"Your {C.APP_NAME} digest", body):
            sent += 1
    return sent


# ------------------------------------------------------------------ Market Pulse storage
import json


def pulse_watch(wid, cap):
    """What to track: the workspace's watchlist plus its Competitors (auto-added), trimmed to the plan's limit."""
    watch = [dict(term=(r["term"] or "").strip()[:80], type=r["type"] or "Keyword", region=r["region"] or "Both") for r in q("SELECT term, type, region FROM watchlist WHERE workspace_id=? ORDER BY id", (wid,))]
    seen = {w["term"].lower() for w in watch}
    for c in q("SELECT name FROM competitors WHERE workspace_id=? ORDER BY id LIMIT 30", (wid,)):
        n = (c["name"] or "").strip()[:80]
        if n and n.lower() not in seen:
            seen.add(n.lower())
            watch.append(dict(term=n, type="Competitor", region="Both"))
    watch = [w for w in watch if w["term"] and w["type"] in ("Keyword", "Competitor", "Brand", "Subreddit") and w["region"] in ("India", "Global", "Both")]
    return watch[:cap]


def latest_pulse(wid):
    r = q("SELECT payload FROM pulse_runs WHERE workspace_id=? ORDER BY id DESC LIMIT 1", (wid,), one=True)
    if not r:
        return None
    try:
        return json.loads(r["payload"])
    except ValueError:
        return None


def pulse_age_minutes(data):
    try:
        return (dt.datetime.now() - dt.datetime.fromisoformat(data["generated"])).total_seconds() / 60
    except Exception:
        return 10 ** 6


def run_pulse(wid, industry, plan):
    """Fetch live data for the workspace and store it. Marks terms that were not in the previous run as new."""
    import pulse
    prev = latest_pulse(wid)
    data = pulse.collect(pulse_watch(wid, plan["watch"]), industry)
    before = {row[0] for row in (prev or {}).get("terms", [])}
    data["terms"] = [(t, c, t not in before and bool(prev)) for t, c in data["terms"]]
    ins("pulse_runs", dict(workspace_id=wid, payload=json.dumps(data)))
    old = [r["id"] for r in q("SELECT id FROM pulse_runs WHERE workspace_id=? ORDER BY id DESC", (wid,))][8:]
    for i in old:
        ex("DELETE FROM pulse_runs WHERE id=?", (i,))
    return data


# ------------------------------------------------------------------ brand theming (business workspaces only; personal_brand always stays lavender)
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _mix(hexcolor, target, amt):
    """Blend hexcolor toward target (0,0,0)=black or (255,255,255)=white by amt (0-1)."""
    r, g, b = int(hexcolor[1:3], 16), int(hexcolor[3:5], 16), int(hexcolor[5:7], 16)
    tr, tg, tb = target
    mix = lambda c, t: round(c + (t - c) * amt)
    return "#%02x%02x%02x" % (mix(r, tr), mix(g, tg), mix(b, tb))


def hex_shades(hexcolor):
    """A small palette derived from one brand colour: a darker shade for text/hover, and two light tints for backgrounds."""
    if not hexcolor or not HEX_RE.match(hexcolor):
        return None
    return dict(pri=hexcolor, pri_d=_mix(hexcolor, (0, 0, 0), 0.22), pri2=_mix(hexcolor, (255, 255, 255), 0.92),
                pri3=_mix(hexcolor, (255, 255, 255), 0.82), accent=_mix(hexcolor, (255, 255, 255), 0.35))


def brand_shades(ws):
    """None for personal-brand workspaces (they always keep the lavender theme) or when no colour is set."""
    if not ws or ws["industry"] == "personal_brand" or not ws["brand_color"]:
        return None
    return hex_shades(ws["brand_color"])
