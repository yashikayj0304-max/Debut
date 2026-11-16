"""Link in bio: a free public page for a workspace (replaces a separate link-in-bio app), with click counts and a QR code."""
import io, json, re
from urllib.parse import urlparse
import segno
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort, Response
import config as C
import services as S
from db import q, ex

bp = Blueprint("bio", __name__)
W = lambda: g.ws["id"]
MAX_LINKS = 8
SOURCE = "Link in bio"      # leads that arrive from the page's message button carry this source

# Industry flavour for the public page: what to say when the owner has not filled a box yet, and the wording of the message button.
# (emoji, tagline chip, headline pattern, one-liner, message button, suggested link labels, accent mood)
FLAVOUR = {
    "d2c": ("🛍️", "Shop direct", "{n}: made for you", "Shop our latest drop, track your order, or message us.", "💬 Ask about an order", ["Shop now", "Track my order", "WhatsApp us"], "bold"),
    "fmcg": ("🛒", "Find us near you", "{n}: everyday favourites", "Find your nearest store, see offers, or tell us what you think.", "💬 Tell us what you think", ["Find a store", "Today's offers", "Our products"], "bold"),
    "b2b": ("🤝", "Work with us", "{n}: results for your business", "See what we do, read case studies, and book a call.", "💬 Talk to our team", ["Book a call", "Case studies", "Pricing"], "clean"),
    "saas": ("🚀", "Try it free", "{n}: try it free", "Start a free trial, watch a 2-minute demo, or ask us anything.", "💬 Request a demo", ["Start free", "Watch the demo", "Pricing"], "clean"),
    "startup": ("⚡", "Early access", "{n}: we're just getting started", "Join the waitlist, follow our journey, or say hello.", "💬 Say hello", ["Join the waitlist", "Our story", "Follow the journey"], "bold"),
    "hospitality": ("🍽️", "Book your table", "{n}: come hungry", "See the menu, book a table, or ask about events.", "💬 Book or enquire", ["Book a table", "View the menu", "Find us on the map"], "warm"),
    "retail": ("🏬", "Visit the store", "{n}: new in store", "See what's new, find your nearest store, or message us.", "💬 Ask about a product", ["Shop online", "Store locations", "Offers this week"], "bold"),
    "realestate": ("🏠", "Find your home", "{n}: homes we're proud of", "Browse listings, book a site visit, or talk to an advisor.", "💬 Book a site visit", ["View listings", "Book a site visit", "WhatsApp an advisor"], "clean"),
    "education": ("🎓", "Learn with us", "{n}: learn, grow, achieve", "See courses, book a free demo class, or ask about admissions.", "💬 Ask about admissions", ["View courses", "Book a free demo class", "Fees and batches"], "warm"),
    "healthcare": ("🩺", "Care you can trust", "{n}: care that listens", "Book an appointment, see our doctors, or ask a question.", "💬 Book an appointment", ["Book an appointment", "Our doctors", "Find the clinic"], "clean"),
    "fashion": ("👗", "New collection", "{n}: the new edit", "Shop the collection, see the lookbook, or message our stylists.", "💬 Ask a stylist", ["Shop the collection", "Lookbook", "Size guide"], "bold"),
    "fintech": ("💳", "Money, simplified", "{n}: money made simple", "See how it works, get started in minutes, or talk to support.", "💬 Talk to support", ["Get started", "How it works", "Help centre"], "clean"),
    "agency": ("🎯", "Let's work together", "{n}: ideas that move people", "See our work, meet the team, or start a project.", "💬 Start a project", ["See our work", "Services", "Start a project"], "bold"),
    "personal_brand": ("✨", "Hi, I'm here", "{n}", "My latest work, collabs and the best way to reach me.", "💬 Work with me", ["Latest video", "Work with me", "Newsletter"], "warm"),
    "general": ("🔗", "All our links", "{n}", "Everything in one place.", "💬 Send us a message", ["Our website", "WhatsApp us", "Latest offer"], "clean"),
}


def flavour(ws):
    k = (ws["industry"] if "industry" in ws.keys() else "") or "general"
    f = FLAVOUR.get(k) or FLAVOUR["general"]
    return dict(zip(("emoji", "chip", "headline", "sub", "msg", "labels", "mood"), f))


def _load(ws):
    try:
        d = json.loads(ws["bio"] or "{}")
    except (ValueError, TypeError, KeyError):
        d = {}
    return dict(headline=d.get("headline", ""), sub=d.get("sub", ""), links=[l for l in d.get("links", []) if isinstance(l, dict)][:MAX_LINKS],
                offer=d.get("offer", ""), offer_url=d.get("offer_url", ""), form=bool(d.get("form", True)))


def _safe_url(u):
    u = (u or "").strip()
    if u and not re.match(r"^[a-z][a-z0-9+.-]*:", u, re.I):
        u = "https://" + u
    p = urlparse(u)
    return u[:400] if p.scheme in ("http", "https") and p.netloc else ""


def _clean(s, n):
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


@bp.route("/bio", methods=["GET", "POST"])
def edit():
    if g.role not in C.TEAM_MANAGERS and g.role != "owner":
        abort(403)
    if request.method == "POST":
        f = request.form
        links = []
        for i in range(MAX_LINKS):
            label, url = _clean(f.get(f"label{i}"), 40), _safe_url(f.get(f"url{i}"))
            if label and url:
                links.append(dict(label=label, url=url))
        data = dict(headline=_clean(f.get("headline"), 80), sub=_clean(f.get("sub"), 160), links=links, offer=_clean(f.get("offer"), 100), offer_url=_safe_url(f.get("offer_url")), form=bool(f.get("form")))
        ex("UPDATE workspaces SET bio=? WHERE id=?", (json.dumps(data), W()))
        S.audit("bio_save", f"{len(links)} links")
        flash("Saved. Your page is live.")
        return redirect(url_for("bio.edit"))
    d = _load(g.ws)
    clicks = {r["detail"]: r["c"] for r in q("SELECT detail, COUNT(*) c FROM audit_log WHERE workspace_id=? AND action='bio_click' GROUP BY detail", (W(),))}
    pub = S.app_url() + url_for("bio.public", slug=g.ws["slug"])
    import datetime as dt
    today = S.today()
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    seen = {r["day"]: r["c"] for r in q("SELECT SUBSTR(created_at,1,10) day, COUNT(*) c FROM audit_log WHERE workspace_id=? AND action='bio_view' AND SUBSTR(created_at,1,10)>=? GROUP BY SUBSTR(created_at,1,10)", (W(), days[0]))}
    views_total = (q("SELECT COUNT(*) c FROM audit_log WHERE workspace_id=? AND action='bio_view'", (W(),), one=True) or {"c": 0})["c"]
    taps_total = sum(clicks.values())
    msgs = q("SELECT id, name, email, phone, created_at FROM leads WHERE workspace_id=? AND source=? ORDER BY id DESC LIMIT 5", (W(), SOURCE))
    msgs_total = (q("SELECT COUNT(*) c FROM leads WHERE workspace_id=? AND source=?", (W(), SOURCE), one=True) or {"c": 0})["c"]
    stats = dict(days=[(d[5:], seen.get(d, 0)) for d in days], week=sum(seen.get(d, 0) for d in days), views=views_total, taps=taps_total, msgs=msgs_total,
                 rate=(round(taps_total * 100 / views_total) if views_total else 0))
    return render_template("bio_edit.html", fl=flavour(g.ws), d=d, clicks=clicks, pub=pub, slots=MAX_LINKS, slug=g.ws["slug"], stats=stats, msgs=msgs)


@bp.route("/l/<slug>")
def public(slug):
    ws = q("SELECT * FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    d = _load(ws)
    col = ws["brand_color"] if re.match(r"^#[0-9a-fA-F]{6}$", ws["brand_color"] or "") else "#6a3df0"
    sec = ws["secondary_color"] if re.match(r"^#[0-9a-fA-F]{6}$", ws["secondary_color"] or "") else "#ff4f9a"
    logo = ws["logo_url"] if (ws["logo_url"] or "").startswith(("http://", "https://", "/")) else ""
    S.audit("bio_view", "", wid=ws["id"], uid=None)
    fl = flavour(ws)
    r = Response(render_template("bio_public.html", fl=fl, ws=ws, d=d, col=col, sec=sec, logo=logo, bare=True, hide_chrome=True, name=ws["name"].replace(" (demo)", "")))
    r.headers["Cache-Control"] = "no-store"      # every visit is counted
    return r


@bp.route("/l/<slug>/go/<int:i>")
def go(slug, i):
    ws = q("SELECT * FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    links = _load(ws)["links"]
    if i < 0 or i >= len(links):
        abort(404)
    S.audit("bio_click", f"{i}:{links[i].get('label', '')}"[:80], wid=ws["id"], uid=None)
    return redirect(links[i]["url"], 302)


@bp.route("/l/<slug>/qr.svg")
def qr(slug):
    q("SELECT 1 FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    buf = io.BytesIO()
    segno.make(S.app_url() + url_for("bio.public", slug=slug), error="m").save(buf, kind="svg", scale=8, border=2, dark="#111111")
    return Response(buf.getvalue(), mimetype="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})

# ----------------------------------------------------------------- asking for reviews
# For a shop, a salon or a restaurant, Google reviews bring more people through the door than any
# post does. The pieces were already here - a short link, a QR code, click tracking - so asking for
# a review is the same machinery pointed somewhere else.
@bp.route("/reviews", methods=["GET", "POST"])
@S.roles("owner", "admin", "lead", "manager")
def reviews():
    ws = g.ws
    if request.method == "POST":
        url = (request.form.get("review_url") or "").strip()[:400]
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        ex("UPDATE workspaces SET review_url=? WHERE id=?", (url, ws["id"]))
        S.audit("review_url_set", url[:80])
        flash("Saved. Share the link or print the QR code. ⭐" if url else "Review link cleared.")
        return redirect(url_for("bio.reviews"))
    sent = (q("SELECT COUNT(*) c FROM audit_log WHERE workspace_id=? AND action='review_click'",
              (ws["id"],), one=True) or {"c": 0})["c"]
    msgs = [f"Thanks for coming to {ws['name']}! If you have 30 seconds, a review really helps a small business like ours:",
            "Hope you loved it. A quick review helps more people find us:",
            "Thank you for your order. Would you leave us a line? It takes 30 seconds:"]
    return render_template("reviews.html", messages=msgs, url=ws["review_url"] if "review_url" in ws.keys() else "",
                           short=S.app_url() + url_for("bio.review_go", slug=ws["slug"]), sent=sent,
                           public=not any(x in S.app_url() for x in ("127.0.0.1", "localhost")))


@bp.route("/review/<slug>")   # "/r/" belongs to the public client report, so reviews live here
def review_go(slug):
    """The short link that goes on a bill, a WhatsApp message or a sticker by the counter."""
    ws = q("SELECT * FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    url = (ws["review_url"] if "review_url" in ws.keys() else "") or ""
    S.audit("review_click", "", wid=ws["id"], uid=None)
    if not url:
        return render_template("reviews_missing.html", ws=ws, bare=True), 404
    return redirect(url)


@bp.route("/review/<slug>/qr.svg")
def review_qr(slug):
    q("SELECT 1 FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    buf = io.BytesIO()
    segno.make(S.app_url() + url_for("bio.review_go", slug=slug), error="m").save(
        buf, kind="svg", scale=8, border=2, dark="#111111")
    return Response(buf.getvalue(), mimetype="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})
