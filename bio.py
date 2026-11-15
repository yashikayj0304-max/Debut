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
    return render_template("bio_edit.html", d=d, clicks=clicks, pub=pub, slots=MAX_LINKS, slug=g.ws["slug"])


@bp.route("/l/<slug>")
def public(slug):
    ws = q("SELECT * FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    d = _load(ws)
    col = ws["brand_color"] if re.match(r"^#[0-9a-fA-F]{6}$", ws["brand_color"] or "") else "#6a3df0"
    sec = ws["secondary_color"] if re.match(r"^#[0-9a-fA-F]{6}$", ws["secondary_color"] or "") else "#ff4f9a"
    logo = ws["logo_url"] if (ws["logo_url"] or "").startswith(("http://", "https://", "/")) else ""
    r = Response(render_template("bio_public.html", ws=ws, d=d, col=col, sec=sec, logo=logo, bare=True, hide_chrome=True, name=ws["name"].replace(" (demo)", "")))
    r.headers["Cache-Control"] = "public, max-age=60"
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
