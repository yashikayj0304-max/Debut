"""Product views. Every query is scoped by workspace_id; see tests/test_app.py for tenant-isolation checks."""
import os, re, io, csv, json, base64, hashlib, calendar as pycal, datetime as dt
from collections import OrderedDict, Counter
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from urllib.parse import quote, quote_plus
from xml.etree import ElementTree as ET
import requests
from flask import g, render_template, request, redirect, url_for, flash, jsonify, abort, Response, send_from_directory
import secrets
from itsdangerous import URLSafeSerializer, BadSignature
import config as C
import services as S
import industries as IND
from db import q, ex, ins, qi
from extensions import csrf, limiter
from modules import *  # noqa: F401,F403

ROUTES = []


def route(rule, **opts):
    def deco(f):
        ROUTES.append((rule, f, opts))
        return f
    return deco


def register(app):
    for rule, f, opts in ROUTES:
        app.add_url_rule(rule, endpoint=f.__name__, view_func=f, **opts)
    csrf.exempt(app.view_functions["lead_hook"])      # called cross-site by visitors' browsers / Zapier; protected by its secret URL key instead


def W():
    return g.ws["id"]


def num(s):
    try:
        return float(re.sub(r"[^\d.\-]", "", str(s or "")) or 0)
    except ValueError:
        return 0.0


def safe_next(default):
    n = request.values.get("next", "")
    return n if n.startswith("/") and not n.startswith("//") else default


def mod(key):
    if key not in MODULES:
        abort(404)
    return MODULES[key]


def row_or_404(key, rid):
    return q(f"SELECT * FROM {key} WHERE id=? AND workspace_id=?", (rid, W()), one=True) or abort(404)


def locked(key):
    f = MODULE_FEATURE.get(key)
    return bool(f and f not in g.plan["features"])


# ----------------------------------------------------------------- public pages
@route("/")
def landing():
    if g.user:
        return redirect(url_for("dashboard"))
    return render_template("landing.html", plans=C.PLANS, mods=MODULES, inds=[IND.INDUSTRIES[k] for k in IND.ORDER if k != "general"])


@route("/pricing")
def pricing():
    return render_template("pricing.html", plans=C.PLANS)


@route("/terms")
def terms():
    return render_template("terms.html")


@route("/privacy")
def privacy():
    return render_template("privacy.html")


@route("/health")
def health():
    try:
        q("SELECT 1 AS ok", one=True)
        return jsonify(status="ok")
    except Exception:
        return jsonify(status="db_error"), 503


@route("/help")
def help_centre():
    return render_template("help.html")


@route("/contact")
def contact():
    return render_template("contact.html")


@route("/refunds")
def refunds():
    return render_template("refunds.html")


@route("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\nDisallow: /app\nDisallow: /m/\nDisallow: /api/\nDisallow: /hooks/\nDisallow: /r/\nDisallow: /lead/\nDisallow: /apply/\nDisallow: /calendar/\n"
                    f"Sitemap: {C.APP_URL}/sitemap.xml\n", mimetype="text/plain")


@route("/sitemap.xml")
def sitemap():
    urls = ["/", "/pricing", "/terms", "/privacy", "/refunds", "/contact"]
    body = "".join(f"<url><loc>{C.APP_URL}{u}</loc><changefreq>monthly</changefreq></url>" for u in urls)
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + body + "</urlset>", mimetype="application/xml")


# ----------------------------------------------------------------- dashboard
@route("/app")
def dashboard():
    if g.role == "client":
        return redirect(url_for("portal"))
    w, today = W(), S.today()
    t, wk = today.isoformat(), (today + dt.timedelta(days=7)).isoformat()
    upcoming = q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ? ORDER BY publish_date", (w, t, wk))
    overdue = q("SELECT * FROM tasks WHERE workspace_id=? AND status!='Done' AND due_date!='' AND due_date<? ORDER BY due_date", (w, t))
    due_soon = q("SELECT * FROM tasks WHERE workspace_id=? AND status!='Done' AND due_date BETWEEN ? AND ? ORDER BY due_date", (w, t, wk))
    camps = q("SELECT * FROM campaigns WHERE workspace_id=?", (w,))
    budget, spent = sum(num(c["budget"]) for c in camps), sum(num(c["spent"]) for c in camps)
    live = len([c for c in camps if c["status"] == "Live"])
    total = q("SELECT COUNT(*) c FROM launch_checklist WHERE workspace_id=?", (w,), one=True)["c"]
    done = q("SELECT COUNT(*) c FROM launch_checklist WHERE workspace_id=? AND status='Done'", (w,), one=True)["c"]
    pipeline = q("SELECT status, COUNT(*) c FROM content_items WHERE workspace_id=? GROUP BY status", (w,))
    leads = q("SELECT stage, COUNT(*) c FROM leads WHERE workspace_id=? GROUP BY stage", (w,))
    refs = q("SELECT * FROM reference_links WHERE workspace_id=? ORDER BY id DESC LIMIT 5", (w,))
    promos = q("SELECT * FROM promotions WHERE workspace_id=? AND (status='Live' OR start_date BETWEEN ? AND ?) ORDER BY start_date", (w, t, (today + dt.timedelta(days=14)).isoformat()))
    events = q("SELECT * FROM events WHERE workspace_id=? AND date BETWEEN ? AND ? AND status!='Cancelled' ORDER BY date", (w, t, (today + dt.timedelta(days=30)).isoformat()))
    followups = q("SELECT * FROM influencers WHERE workspace_id=? AND next_followup!='' AND next_followup<=? AND status NOT IN ('Booked','Delivered','Rejected') ORDER BY next_followup", (w, t))
    # "Today": one short, auto-built list for a founder running marketing solo - what's overdue from
    # before (the rollover from yesterday and earlier) plus what's actually due today, so there's one
    # place to look each morning instead of checking every module by hand.
    content_catchup = q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date!='' AND publish_date<=? AND status NOT IN ('Published','On hold') ORDER BY publish_date", (w, t))
    due_today_tasks = [r for r in due_soon if r["due_date"] == t]
    today_items = (
        [dict(icon="⏰", text=f"Overdue: {r['title']}", href=url_for("m_edit", key="tasks", rid=r["id"])) for r in overdue] +
        [dict(icon="📝", text=f"{'Publish today' if r['publish_date'] == t else 'Overdue to publish'}: {r['title']}", href=url_for("m_edit", key="content_items", rid=r["id"])) for r in content_catchup] +
        [dict(icon="🗂️", text=f"Due today: {r['title']}", href=url_for("m_edit", key="tasks", rid=r["id"])) for r in due_today_tasks] +
        [dict(icon="🤳", text=f"Follow up: {r['name']}", href=url_for("outreach", iid=r["id"])) for r in followups]
    )
    today_more = max(0, len(today_items) - 8)
    today_items = today_items[:8]
    tiles = []
    for k in ("content_items", "campaigns", "promotions", "events", "content_orders", "creators", "tasks", "leads", "reference_links", "influencers"):
        if locked(k) or (g.role == "creator" and k not in CREATOR_MODULES):
            continue
        m = MODULES[k]
        tiles.append((m["icon"], m["title"], q(f"SELECT COUNT(*) c FROM {k} WHERE workspace_id=?", (w,), one=True)["c"], url_for("m_list", key=k)))
    tiles.append(("🖼️", "Mood Boards", q("SELECT COUNT(*) c FROM boards WHERE workspace_id=?", (w,), one=True)["c"], url_for("moodboards")))
    cnt = lambda tbl: q(f"SELECT COUNT(*) c FROM {tbl} WHERE workspace_id=?", (w,), one=True)["c"]
    industry = g.ws["industry"]
    # the "audience" step changes with the kind of business: opportunities for personal brands, accounts for B2B, audits for FMCG/retail
    if industry in ("personal_brand",):
        third = ("Add a speaking or podcast opportunity", cnt("pitches") > 0, url_for("m_new", key="pitches"))
    elif industry in ("b2b", "saas", "agency", "fintech", "startup"):
        third = ("Add your first target account", cnt("accounts") > 0, url_for("m_new", key="accounts"))
    elif industry in ("fmcg", "retail"):
        third = ("Log your first retail audit", cnt("retail_audits") > 0, url_for("m_new", key="retail_audits"))
    else:
        third = ("Add influencer prospects", cnt("influencers") > 0, url_for("discover"))
    steps = [("Write your first GTM plan", cnt("gtm_plans") > 0, url_for("m_new", key="gtm_plans")),
             ("Add content to the calendar", cnt("content_items") > 0, url_for("m_new", key="content_items")),
             ("Create a mood board", cnt("boards") > 0, url_for("moodboards")),
             third,
             ("Capture your first lead", cnt("leads") > 0, url_for("ws.integrations") if g.role in ("owner", "admin", "lead", "manager") else url_for("m_new", key="leads")),
             ("Invite a teammate", cnt("memberships") > 1, url_for("ws.team")),
             ("Verify your email", bool(g.user["email_verified"]), url_for("ws.account"))]
    return render_template("dashboard.html", upcoming=upcoming, overdue=overdue, due_soon=due_soon, budget=budget, spent=spent, live=live, total=total, done=done,
                           pipeline=pipeline, leads=leads, refs=refs, tiles=tiles, promos=promos, events=events, followups=followups,
                           today_items=today_items, today_more=today_more,
                           steps=steps, steps_done=all(s[1] for s in steps),
                           ind=IND.get(g.ws["industry"]), pulse=S.latest_pulse(w),
                           usage=dict(records=S.record_count(w), boards=cnt("boards"), credits=S.credits_used(w)) if g.plan_key == "free" else None)


# ----------------------------------------------------------------- generic CRUD
GAP_BANNER_KEYS = {"brand_kit": {"brand_kit"}, "campaigns": {"campaigns"}, "content_items": {"content_items", "content_overdue"},
                    "tasks": {"tasks"}, "leads": {"leads"}}


@route("/m/<key>")
def m_list(key):
    m = mod(key)
    hidden = HIDDEN_FOR_CREATOR.get(key, set()) if g.role == "creator" else set()
    gap_banner = None
    if key in GAP_BANNER_KEYS:
        cnt = sum(gp["count"] for gp in _marketing_gaps() if gp["key"] in GAP_BANNER_KEYS[key])
        gap_banner = cnt or None
    qs, f = request.args.get("q", "").strip(), request.args.get("f", "")
    sql, args, where = f"SELECT * FROM {key} WHERE workspace_id=?", [W()], []
    if qs:
        searchable = [x for x in m["fields"] if x[0] not in hidden]
        where.append("(" + " OR ".join(f"LOWER({qi(x[0])}) LIKE ?" for x in searchable) + ")")
        args += [f"%{qs.lower()}%"] * len(searchable)
    ffield = next((x for x in m["fields"] if x[0] == m.get("filter")), None)
    if f and ffield:
        where.append(f"{qi(ffield[0])}=?")
        args.append(f)
    if where:
        sql += " AND " + " AND ".join(where)
    order = "publish_date DESC, id DESC" if key == "content_items" else "id DESC"
    page = min(max(1, S.to_int(request.args.get("page"), 1)), 10000)
    per = 100
    rows = q(sql + f" ORDER BY {order} LIMIT {per + 1} OFFSET {(page - 1) * per}", args)
    types = {x[0]: (x[1], x[2]) for x in m["fields"]}
    cols = [(c, types[c][0], types[c][1]) for c in m["cols"] if c not in hidden]
    return render_template("crud_list.html", key=key, m=m, rows=rows[:per], more=len(rows) > per, page=page, cols=cols, q=qs, f=f, ffield=ffield, gap_banner=gap_banner)


def _hidden(key):
    return HIDDEN_FOR_CREATOR.get(key, set()) if g.role == "creator" else set()


@route("/m/<key>/new")
def m_new(key):
    modal = request.args.get("modal") == "1"
    tpl = "crud_form_frag.html" if modal else "crud_form.html"
    return render_template(tpl, key=key, m=mod(key), row=None, defaults=request.args, nxt=safe_next(""), team_names=S.team_names(W()), hidden=_hidden(key), required=REQUIRED.get(key, set()), modal=modal)


@route("/m/<key>/<int:rid>/edit")
def m_edit(key, rid):
    row = row_or_404(key, rid)
    modal = request.args.get("modal") == "1"
    tpl = "crud_form_frag.html" if modal else "crud_form.html"
    comments = q("SELECT c.*, u.name AS uname FROM comments c LEFT JOIN users u ON u.id=c.user_id WHERE c.workspace_id=? AND c.module=? AND c.record_id=? ORDER BY c.id", (W(), key, rid))
    return render_template(tpl, key=key, m=mod(key), row=row, defaults={}, nxt=safe_next(""), team_names=S.team_names(W()), comments=comments, hidden=_hidden(key), required=REQUIRED.get(key, set()), modal=modal)


def clean_fields(m, source, quiet=False, partial=False):
    """Validate/normalise submitted field values. quiet: no flash messages (API use). partial: only fields present in source."""
    data = {}
    for n, label, typ, opts in m["fields"]:
        if partial and n not in source:
            continue
        v = S.clean_text(source.get(n, ""))
        if typ == "url":
            cv = S.clean_url(v)
            if v and not cv and not quiet:
                flash(f"“{label}” must be a valid http(s) link and was cleared.")
            v = cv
        elif typ == "select" and v and opts and v not in opts:
            v = opts[0]
        elif typ == "number" and v and not re.match(r"^-?\d+(\.\d+)?$", v):
            v = re.sub(r"[^\d.\-]", "", v)
        data[n] = v
    return data


RESTRICTED = {"content_items": {"Approved", "Scheduled", "Published"}, "content_orders": {"Approved", "Delivered", "Invoiced"}}
FALLBACK = {"content_items": "Review", "content_orders": "Editing / QA"}


def gate_status(key, new, old):
    """Approvals belong to leads and managers: creators can move work to review but cannot approve or publish it themselves."""
    if g.role == "creator" and new in RESTRICTED.get(key, ()) and new != old:
        flash("Only a lead or manager can approve or publish. This was sent for review instead.")
        return old if old and old not in RESTRICTED[key] else FALLBACK[key]
    return new


def _title(m, d):
    return str(d.get(m["fields"][0][0]) or "")[:80]


def changed_hooks(key, rid, m, new, old):
    """Notifications when work is assigned, sent for approval, or approved."""
    wid, me = W(), g.user["id"]
    who, title, link = (g.user["name"] or g.user["email"]), _title(m, {**(dict(old) if old else {}), **new}), url_for("m_edit", key=key, rid=rid)
    for f in ("assignee", "owner"):
        if f in new:
            if new[f] and (old is None or old[f] != new[f]):
                mem = S.find_member(wid, new[f])
                if mem and mem["uid"] != me:
                    S.notify(wid, mem["uid"], "assigned", f"{who} assigned you: {title}", link)
            break
    if key in RESTRICTED and "status" in new and (old is None or old["status"] != new["status"]):
        st = new["status"]
        if st in ("Review", "Editing / QA", "Client review"):
            for mem in S.members(wid):
                if mem["role"] in ("owner", "admin", "lead", "manager") and mem["uid"] != me:
                    S.notify(wid, mem["uid"], "approval", f"{who} sent for approval: {title}", link)
            if key == "content_items" and st == "Review":
                for cm in S.client_members(wid, ({**(dict(old) if old else {}), **new}).get("client")):
                    S.notify(wid, cm["uid"], "client_review", f"Ready for your review: {title}", url_for("portal_item", iid=rid))
        elif st == "Approved":
            src = {**(dict(old) if old else {}), **new}
            mem = S.find_member(wid, src.get("owner") or src.get("assignee") or "")
            if mem and mem["uid"] != me:
                S.notify(wid, mem["uid"], "approved", f"{who} approved: {title}", link)


@route("/m/<key>/save", methods=["POST"])
def m_save(key):
    m = mod(key)
    raw_id = request.form.get("id")
    rid = S.to_int(raw_id)
    if raw_id and not rid:
        abort(400)
    old = row_or_404(key, rid) if rid else None
    modal = request.form.get("modal") == "1"
    tpl = "crud_form_frag.html" if modal else "crud_form.html"
    data = clean_fields(m, request.form)
    for f in _hidden(key):          # freelancers can neither see nor change the agency's money fields
        data.pop(f, None)
    missing = [label for n, label, typ, opts in m["fields"] if n in REQUIRED.get(key, set()) and not (data.get(n) or "").strip()]
    if missing:
        flash("Please fill in: " + ", ".join(missing) + ".")
        if rid:
            row = dict(old) if old else {}
            row.update(data)
            row["id"] = rid
            comments = q("SELECT c.*, u.name AS uname FROM comments c LEFT JOIN users u ON u.id=c.user_id WHERE c.workspace_id=? AND c.module=? AND c.record_id=? ORDER BY c.id", (W(), key, rid))
            return render_template(tpl, key=key, m=m, row=row, defaults={}, nxt=safe_next(url_for("m_list", key=key)), team_names=S.team_names(W()), comments=comments, hidden=_hidden(key), required=REQUIRED.get(key, set()), modal=modal), 400
        return render_template(tpl, key=key, m=m, row=None, defaults=data, nxt=safe_next(url_for("m_list", key=key)), team_names=S.team_names(W()), hidden=_hidden(key), required=REQUIRED.get(key, set()), modal=modal), 400
    if key in RESTRICTED and "status" in data:
        data["status"] = gate_status(key, data["status"], old["status"] if old else "")
    if rid:
        ex(f"UPDATE {key} SET " + ",".join(f"{qi(n)}=?" for n in data) + " WHERE id=? AND workspace_id=?", list(data.values()) + [rid, W()])
        S.audit("update", f"{key}#{rid}")
    else:
        if S.record_count(W()) >= g.plan["records"]:
            flash(f"You've reached the {g.plan['name']} plan limit of {g.plan['records']} records. Upgrade to add more (you can still edit, delete or export).")
            return redirect(url_for("billing.billing") if g.role in ("owner", "admin") else url_for("dashboard"))
        if key == "watchlist" and q("SELECT COUNT(*) c FROM watchlist WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["watch"]:
            flash(f"Your {g.plan['name']} plan can track {g.plan['watch']} items in Market Pulse. Remove one or upgrade for more.")
            return redirect(url_for("m_list", key="watchlist"))
        data["workspace_id"] = W()
        rid = ins(key, data)
        S.audit("create", f"{key}#{rid}")
    changed_hooks(key, rid, m, data, old)
    flash("Saved.")
    return redirect(safe_next(url_for("m_list", key=key)))


@route("/m/<key>/<int:rid>/delete", methods=["POST"])
def m_delete(key, rid):
    mod(key)
    row_or_404(key, rid)
    ex(f"DELETE FROM {key} WHERE id=? AND workspace_id=?", (rid, W()))
    S.audit("delete", f"{key}#{rid}")
    flash("Deleted.")
    return redirect(safe_next(url_for("m_list", key=key)))


def _csv_safe(v):
    v = "" if v is None else str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


@route("/m/<key>/export")
def m_export(key):
    m = mod(key)
    names = [x[0] for x in m["fields"]]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(names)
    for r in q(f"SELECT * FROM {key} WHERE workspace_id=? ORDER BY id", (W(),)):
        w.writerow([_csv_safe(r[n]) for n in names])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={key}.csv"})


@route("/m/<key>/template")
def m_template(key):
    """A blank, header-only CSV so people can see the exact column format before importing."""
    m = mod(key)
    names = [x[0] for x in m["fields"]]
    labels = [x[1] for x in m["fields"]]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(names)
    w.writerow([f"(e.g. {l})" for l in labels])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={key}-template.csv"})


_XLSX_SHEET_BAD_CHARS = re.compile(r"[\\/*\[\]:?]")


def _xlsx_sheet_title(raw, fallback):
    """Excel sheet names can't contain \\ / * [ ] : or ? and can't be blank or over 31 chars — strip/replace
    anything invalid (e.g. module titles like "Personas / ICP") so the workbook always saves successfully."""
    cleaned = _XLSX_SHEET_BAD_CHARS.sub("-", (raw or fallback)).strip()
    return (cleaned or fallback)[:31]


def _mock_value(label, typ, opts):
    """A plausible example value for one field, used to fill in the downloadable Excel mock."""
    if typ == "select" and opts:
        return opts[0]
    if typ == "number":
        return 1000
    if typ == "date":
        return S.today().isoformat()
    if typ == "url":
        return "https://example.com"
    return f"Example {label.lower()}"


@route("/m/<key>/template.xlsx")
def m_template_xlsx(key):
    """A downloadable Excel (.xlsx) mock of this module: real headers plus one filled-in example row, so the
    expected format is obvious before you build your own data and import it back with CSV import."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    m = mod(key)
    wb = Workbook()
    ws = wb.active
    ws.title = _xlsx_sheet_title(m["title"], key)
    names = [x[0] for x in m["fields"]]
    labels = [x[1] for x in m["fields"]]
    ws.append(labels)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="7C5CD6")
    ws.append([_mock_value(l, t, o) for n, l, t, o in m["fields"]])
    for i, l in enumerate(labels, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = max(14, min(32, len(l) + 4))
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     headers={"Content-Disposition": f"attachment; filename={key}-mock-template.xlsx"})


@route("/m/<key>/import", methods=["POST"])
def m_import(key):
    m = mod(key)
    if "import" not in g.plan["features"]:
        flash("CSV import is available on paid plans.")
        return redirect(url_for("m_list", key=key))
    f = request.files.get("file")
    if not f:
        flash("Choose a CSV file.")
        return redirect(url_for("m_list", key=key))
    try:
        rd = csv.DictReader(io.StringIO(f.read(2_000_000).decode("utf-8-sig")))
    except UnicodeDecodeError:
        flash("Could not read that file. Save it as CSV (UTF-8).")
        return redirect(url_for("m_list", key=key))
    lookup = {}
    for n, label, typ, opts in m["fields"]:
        lookup[n.lower()] = n
        lookup[label.lower()] = n
    room = g.plan["records"] - S.record_count(W())
    added = 0
    for i, raw in enumerate(rd):
        if i >= 2000 or added >= room:
            break
        src = {lookup[k.strip().lower()]: v for k, v in raw.items() if k and k.strip().lower() in lookup and v is not None}
        if not any(src.values()):
            continue
        data = clean_fields(m, src)
        data["workspace_id"] = W()
        ins(key, data)
        added += 1
    S.audit("import", f"{key} x{added}")
    flash(f"Imported {added} row(s)." + (" Plan record limit reached." if added >= room else ""))
    return redirect(url_for("m_list", key=key))


@route("/kanban/<key>")
def kanban(key):
    m = mod(key)
    field = m.get("kanban") or abort(404)
    opts = next(x for x in m["fields"] if x[0] == field)[3]
    has_due = any(n == "due_date" for n, *_ in m["fields"])
    sort_due = has_due and request.args.get("sort") == "due"
    # default order is each card's manual drag position within its column (sort_order), falling back to
    # newest-first for cards nobody has ever dragged (they all share sort_order=0)
    order = "due_date ASC, id DESC" if sort_due else "sort_order ASC, id DESC"
    rows = q(f"SELECT * FROM {key} WHERE workspace_id=? ORDER BY {order} LIMIT 500", (W(),))
    return render_template("kanban.html", key=key, m=m, field=field, opts=opts, rows=rows, title_f=m["fields"][0][0],
                           sub_f=m["cols"][1] if len(m["cols"]) > 1 else m["fields"][0][0], has_due=has_due, sort_due=sort_due)


@route("/m/<key>/<int:rid>/status", methods=["POST"])
def m_status(key, rid):
    m = mod(key)
    field = m.get("kanban") or abort(400)
    opts = next(x for x in m["fields"] if x[0] == field)[3]
    v = request.form.get("value", "")
    if v not in opts:
        abort(400)
    row = row_or_404(key, rid)
    if field == "status":
        v = gate_status(key, v, row["status"])
    ex(f"UPDATE {key} SET {qi(field)}=? WHERE id=? AND workspace_id=?", (v, rid, W()))
    if field == "status":
        changed_hooks(key, rid, m, {"status": v}, row)
    return redirect(safe_next(url_for("kanban", key=key)))


@route("/m/<key>/<int:rid>/reorder", methods=["POST"])
def m_reorder(key, rid):
    """Drag a kanban card to a new spot - possibly a new column (same as m_status) and/or a new position
    within that column. before_id is the card it was dropped in front of, or blank to drop at the end."""
    m = mod(key)
    field = m.get("kanban") or abort(400)
    opts = next(x for x in m["fields"] if x[0] == field)[3]
    status = request.form.get("status", "")
    if status not in opts:
        abort(400)
    row = row_or_404(key, rid)
    new_val = gate_status(key, status, row["status"]) if field == "status" else status
    if new_val != row[field]:
        ex(f"UPDATE {key} SET {qi(field)}=? WHERE id=? AND workspace_id=?", (new_val, rid, W()))
        if field == "status":
            changed_hooks(key, rid, m, {"status": new_val}, row)
    before_id = request.form.get("before_id", "").strip()
    siblings = [r["id"] for r in q(f"SELECT id FROM {key} WHERE workspace_id=? AND {qi(field)}=? ORDER BY sort_order ASC, id DESC", (W(), new_val))]
    if rid in siblings:
        siblings.remove(rid)
    if before_id.isdigit() and int(before_id) in siblings:
        siblings.insert(siblings.index(int(before_id)), rid)
    else:
        siblings.append(rid)
    for i, sid in enumerate(siblings):
        ex(f"UPDATE {key} SET sort_order=? WHERE id=? AND workspace_id=?", (i * 10, sid, W()))
    return redirect(safe_next(url_for("kanban", key=key)))


# ----------------------------------------------------------------- search
@route("/search")
def search():
    term, results = request.args.get("q", "").strip(), []
    if len(term) >= 2:
        for key, m in MODULES.items():
            if locked(key) or (g.role == "creator" and key not in CREATOR_MODULES):
                continue
            fields = [f[0] for f in m["fields"] if f[2] in ("text", "textarea", "url")][:6]
            where = " OR ".join(f"LOWER({qi(f)}) LIKE ?" for f in fields)
            rows = q(f"SELECT * FROM {key} WHERE workspace_id=? AND ({where}) ORDER BY id DESC LIMIT 5", [W()] + [f"%{term.lower()}%"] * len(fields))
            if rows:
                results.append((key, m, rows, m["fields"][0][0]))
    return render_template("search.html", term=term, results=results, has_key=bool(C.ANTHROPIC_API_KEY))


# ----------------------------------------------------------------- calendar
@route("/calendar")
def calendar_view():
    w, today = W(), S.today()
    try:
        y, mth = int(request.args.get("y", today.year)), int(request.args.get("m", today.month))
        weeks = pycal.Calendar(0).monthdatescalendar(y, mth)
    except (ValueError, pycal.IllegalMonthError):
        abort(400)
    ch = request.args.get("channel", "")
    start, end = weeks[0][0].isoformat(), weeks[-1][-1].isoformat()
    sql, args = "SELECT * FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ?", [w, start, end]
    if ch:
        sql += " AND channel=?"
        args.append(ch)
    by = {}
    for r in q(sql + " ORDER BY id", args):
        by.setdefault(r["publish_date"], []).append(r)
    kd = {}
    for r in q("SELECT * FROM key_dates WHERE workspace_id=? AND date BETWEEN ? AND ?", (w, start, end)):
        kd.setdefault(r["date"], []).append(r["name"])
    for r in q("SELECT * FROM promotions WHERE workspace_id=? AND (start_date BETWEEN ? AND ? OR end_date BETWEEN ? AND ?)", (w, start, end, start, end)):
        if start <= (r["start_date"] or "") <= end:
            kd.setdefault(r["start_date"], []).append("🏷 " + r["name"] + " starts")
        if start <= (r["end_date"] or "") <= end:
            kd.setdefault(r["end_date"], []).append("🏁 " + r["name"] + " ends")
    for r in q("SELECT * FROM events WHERE workspace_id=? AND date BETWEEN ? AND ?", (w, start, end)):
        kd.setdefault(r["date"], []).append("🎪 " + r["name"] + " (" + r["mode"] + ")")
    py, pm = (y, mth - 1) if mth > 1 else (y - 1, 12)
    ny, nm = (y, mth + 1) if mth < 12 else (y + 1, 1)
    unscheduled = q("SELECT * FROM content_items WHERE workspace_id=? AND (publish_date='' OR publish_date IS NULL) ORDER BY id DESC LIMIT 50", (w,))
    key_ = g.ws["ics_key"] or secrets.token_hex(6)
    if not g.ws["ics_key"]:
        ex("UPDATE workspaces SET ics_key=? WHERE id=?", (key_, w))
    ics = C.APP_URL + url_for("ics_feed", token=URLSafeSerializer(C.SECRET_KEY, salt="ics").dumps([w, key_]))
    return render_template("calendar.html", weeks=weeks, by=by, kd=kd, y=y, mth=mth, month_name=pycal.month_name[mth], ch=ch, channels=CHANNELS,
                           py=py, pm=pm, ny=ny, nm=nm, unscheduled=unscheduled, ics=ics)


@route("/calendar/<token>.ics")
def ics_feed(token):
    try:
        w, key_ = URLSafeSerializer(C.SECRET_KEY, salt="ics").loads(token)
    except (BadSignature, ValueError, TypeError):
        abort(404)
    if not q("SELECT 1 FROM workspaces WHERE id=? AND ics_key=? AND ics_key!=''", (S.to_int(w) or 0, str(key_)), one=True):
        abort(404)
    esc = lambda s: (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{C.APP_NAME}//EN", "CALSCALE:GREGORIAN"]
    for r in q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date!='' ORDER BY publish_date LIMIT 2000", (w,)):
        try:
            d = dt.date.fromisoformat(r["publish_date"])
        except ValueError:
            continue
        lines += ["BEGIN:VEVENT", f"UID:content-{r['id']}@{C.APP_NAME.replace(' ', '').lower()}", f"DTSTAMP:{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}",
                  f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + dt.timedelta(days=1):%Y%m%d}",
                  f"SUMMARY:{esc((r['channel'] or '') + ' - ' + (r['title'] or ''))}", f"DESCRIPTION:{esc((r['status'] or '') + ' | ' + (r['copy'] or '')[:300])}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return Response("\r\n".join(lines), mimetype="text/calendar")


@route("/calendar/reset-link", methods=["POST"])
@S.roles("owner", "admin", "lead", "manager")
def ics_reset():
    ex("UPDATE workspaces SET ics_key=? WHERE id=?", (secrets.token_hex(6), W()))
    S.audit("ics_link_reset")
    flash("Calendar link reset. Anyone using the old link is now cut off; re-subscribe with the new one.")
    return redirect(url_for("calendar_view"))


@route("/api/reschedule", methods=["POST"])
def api_reschedule():
    d = S.jbody()
    try:
        date = dt.date.fromisoformat(str(d.get("date", ""))).isoformat()
    except ValueError:
        return jsonify(error="bad date"), 400
    rid = S.to_int(d.get("id")) or abort(400)
    row_or_404("content_items", rid)
    ex("UPDATE content_items SET publish_date=? WHERE id=? AND workspace_id=?", (date, rid, W()))
    return jsonify(ok=True)


# ----------------------------------------------------------------- mood boards
def board_or_404(bid):
    return q("SELECT * FROM boards WHERE id=? AND workspace_id=?", (bid, W()), one=True) or abort(404)


@route("/moodboards")
def moodboards():
    boards = q("SELECT b.*, (SELECT COUNT(*) FROM board_items i WHERE i.board_id=b.id) AS n FROM boards b WHERE b.workspace_id=? ORDER BY b.id DESC", (W(),))
    covers = {b["id"]: q("SELECT * FROM board_items WHERE board_id=? AND workspace_id=? AND kind='image' LIMIT 1", (b["id"], W()), one=True) for b in boards}
    return render_template("moodboards.html", boards=boards, covers=covers)


@route("/moodboards/new", methods=["POST"])
def board_new():
    if q("SELECT COUNT(*) c FROM boards WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["boards"]:
        flash(f"The {g.plan['name']} plan includes {g.plan['boards']} mood boards. Upgrade for more.")
        return redirect(url_for("moodboards"))
    bid = ins("boards", dict(workspace_id=W(), name=S.clean_text(request.form.get("name"), 120) or "Untitled board", description=S.clean_text(request.form.get("description"), 300)))
    S.audit("create", f"board#{bid}")
    return redirect(url_for("board_view", bid=bid))


def _svg_placeholder(label, bg="#7c5cd6", fg="#ffffff"):
    """A self-contained placeholder picture (no external image host involved) so the sample board always
    renders, even offline — a real upload or image URL replaces it in seconds via the 🔄 button."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
           f'<rect width="100%" height="100%" fill="{bg}"/>'
           f'<text x="50%" y="46%" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="{fg}" text-anchor="middle">{label}</text>'
           f'<text x="50%" y="58%" font-family="Arial, sans-serif" font-size="14" fill="{fg}" text-anchor="middle" opacity=".85">tap 🔄 on the card to replace it</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


SAMPLE_BOARD_ITEMS = [
    ("image", _svg_placeholder("Reference shot"), "Reference shot — swap for your own"),
    ("color", "#7c5cd6", "Primary brand colour"), ("color", "#f1ecff", "Light background tint"),
    ("note", "Mood: warm, festive, a little playful. Think golden-hour light, not studio-flat.", "Overall mood"),
    ("note", "Hero shot idea: product on a textured surface, soft natural light, one prop max.", "Hero shot"),
    ("link", "https://www.pinterest.com/search/pins/?q=festive%20product%20photography", "Inspiration search"),
    ("note", "Caption tone: short, warm, one emoji max. Avoid hard-sell language.", "Caption style"),
    ("image", _svg_placeholder("Palette / texture", bg="#2b2442"), "Palette / texture reference"),
]


@route("/moodboards/sample", methods=["POST"])
def board_sample():
    """A ready-made example board so a first-time user sees the format before building their own."""
    if q("SELECT COUNT(*) c FROM boards WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["boards"]:
        flash(f"The {g.plan['name']} plan includes {g.plan['boards']} mood boards. Upgrade for more.")
        return redirect(url_for("moodboards"))
    bid = ins("boards", dict(workspace_id=W(), name="Sample board (edit or delete me)", description="A worked example — drag things around, then make your own."))
    for kind, content, caption in SAMPLE_BOARD_ITEMS:
        ins("board_items", dict(workspace_id=W(), board_id=bid, kind=kind, content=content, caption=caption, **_next_slot(bid)))
    S.audit("create", f"board#{bid} (sample)")
    return redirect(url_for("board_view", bid=bid))


@route("/moodboards/<int:bid>")
def board_view(bid):
    b = board_or_404(bid)
    unplaced = q("SELECT id FROM board_items WHERE board_id=? AND workspace_id=? AND x<0 ORDER BY id", (bid, W()))
    if unplaced:  # boards created before drag-and-drop existed: give their items a tidy starting position, once
        base = q("SELECT COUNT(*) c FROM board_items WHERE board_id=? AND x>=0", (bid,), one=True)["c"]
        topz = q("SELECT COALESCE(MAX(z),0) z FROM board_items WHERE board_id=?", (bid,), one=True)["z"]
        for i, r in enumerate(unplaced):
            col, row = (base + i) % ITEM_COLS, (base + i) // ITEM_COLS
            ex("UPDATE board_items SET x=?, y=?, w=?, h=?, z=? WHERE id=?",
               (ITEM_GAP + col * (ITEM_W + ITEM_GAP), ITEM_GAP + row * (ITEM_H + ITEM_GAP), ITEM_W, ITEM_H, topz + i + 1, r["id"]))
    return render_template("moodboard.html", b=b, items=q("SELECT * FROM board_items WHERE board_id=? AND workspace_id=? ORDER BY z, id", (bid, W())))


ITEM_W, ITEM_H, ITEM_GAP, ITEM_COLS = 240, 170, 24, 4


def _next_slot(bid):
    """Where a freshly added item lands on the canvas: a tidy cascading grid, so a beginner never has to place the first item themselves."""
    n = q("SELECT COUNT(*) c FROM board_items WHERE board_id=?", (bid,), one=True)["c"]
    col, row = n % ITEM_COLS, n // ITEM_COLS
    top = q("SELECT COALESCE(MAX(z),0) z FROM board_items WHERE board_id=?", (bid,), one=True)["z"]
    return dict(x=ITEM_GAP + col * (ITEM_W + ITEM_GAP), y=ITEM_GAP + row * (ITEM_H + ITEM_GAP), w=ITEM_W, h=ITEM_H, z=top + 1)


@route("/moodboards/<int:bid>/add", methods=["POST"])
def board_add(bid):
    board_or_404(bid)
    kind, cap = request.form.get("kind"), S.clean_text(request.form.get("caption"), 200)
    if q("SELECT COUNT(*) c FROM board_items WHERE board_id=? AND workspace_id=?", (bid, W()), one=True)["c"] >= 300:
        flash("Board is full (300 items).")
        return redirect(url_for("board_view", bid=bid))
    if kind == "upload":
        n = 0
        for f in request.files.getlist("file")[:20]:
            data = f.read(10 * 1024 * 1024 + 1)
            ext = S.sniff_image(data) if data and len(data) <= 10 * 1024 * 1024 else None
            if ext:
                ins("board_items", dict(workspace_id=W(), board_id=bid, kind="image", content=S.store_file(W(), ext, data), caption=cap, **_next_slot(bid)))
                n += 1
        flash(f"Added {n} image(s)." if n else "No valid image (PNG, JPG, GIF or WebP up to 10 MB).")
    else:
        content = S.clean_text(request.form.get("content"), 2000)
        if kind in ("image", "link"):
            content = S.clean_url(content)
        elif kind == "color":
            content = content if re.match(r"^#[0-9a-fA-F]{6}$", content) else ""
        elif kind == "note":
            content = content[:2000]
        else:
            abort(400)
        if content:
            ins("board_items", dict(workspace_id=W(), board_id=bid, kind=kind, content=content, caption=cap, **_next_slot(bid)))
        else:
            flash("That value isn't valid.")
    return redirect(url_for("board_view", bid=bid))


@route("/moodboards/item/<int:iid>/place", methods=["POST"])
def board_item_place(iid):
    """Drag/resize/bring-to-front, saved instantly from the canvas (no page reload)."""
    it = q("SELECT id FROM board_items WHERE id=? AND workspace_id=?", (iid, W()), one=True) or abort(404)
    d = S.jbody()
    try:
        x, y = max(0, min(20000, int(d.get("x")))), max(0, min(20000, int(d.get("y"))))
        w, h = max(80, min(1000, int(d.get("w")))), max(60, min(1000, int(d.get("h"))))
        z = max(0, min(100000, int(d.get("z"))))
    except (TypeError, ValueError):
        abort(400)
    ex("UPDATE board_items SET x=?, y=?, w=?, h=?, z=? WHERE id=? AND workspace_id=?", (x, y, w, h, z, iid, W()))
    return jsonify(ok=True)


@route("/moodboards/item/<int:iid>/edit", methods=["POST"])
def board_item_edit(iid):
    """Edit a note/colour/link card's text in place on the canvas (no page reload) — images keep their file but can get a new caption."""
    it = q("SELECT * FROM board_items WHERE id=? AND workspace_id=?", (iid, W()), one=True) or abort(404)
    d = S.jbody()
    caption = S.clean_text(d.get("caption", ""), 200)
    if it["kind"] == "note":
        content = S.clean_text(d.get("content", ""), 2000)
        if not content:
            return jsonify(error="Note can't be empty."), 400
        ex("UPDATE board_items SET content=?, caption=? WHERE id=?", (content, caption, iid))
    elif it["kind"] == "color":
        content = d.get("content", "")
        if not re.match(r"^#[0-9a-fA-F]{6}$", content or ""):
            return jsonify(error="Enter a valid hex colour, e.g. #7c5cd6."), 400
        ex("UPDATE board_items SET content=?, caption=? WHERE id=?", (content, caption, iid))
    elif it["kind"] == "link":
        content = S.clean_url(d.get("content", ""))
        if not content:
            return jsonify(error="Enter a valid http(s) link."), 400
        ex("UPDATE board_items SET content=?, caption=? WHERE id=?", (content, caption, iid))
    else:  # image: caption always changes here; the picture can be swapped either by pasting a new URL or by uploading a file (board_item_replace_image below)
        new_url = S.clean_url(d.get("content", ""))
        if new_url:
            old_content = it["content"]
            ex("UPDATE board_items SET content=?, caption=? WHERE id=?", (new_url, caption, iid))
            if old_content and not old_content.startswith("http") and not old_content.startswith("data:"):
                S.delete_file(old_content)
        else:
            ex("UPDATE board_items SET caption=? WHERE id=?", (caption, iid))
    return jsonify(ok=True)


@route("/moodboards/item/<int:iid>/replace-image", methods=["POST"])
def board_item_replace_image(iid):
    """Swap the picture on an existing image card in place — position, size and z-order stay put, so a card never has to be deleted and re-added just to change the photo."""
    it = q("SELECT * FROM board_items WHERE id=? AND workspace_id=? AND kind='image'", (iid, W()), one=True) or abort(404)
    f = request.files.get("file")
    data = f.read(10 * 1024 * 1024 + 1) if f else b""
    ext = S.sniff_image(data) if data and len(data) <= 10 * 1024 * 1024 else None
    if not ext:
        return jsonify(error="Choose a PNG, JPG, GIF or WebP image up to 10 MB."), 400
    new_content = S.store_file(W(), ext, data)
    old_content = it["content"]
    ex("UPDATE board_items SET content=? WHERE id=?", (new_content, iid))
    if old_content and not old_content.startswith("http"):
        S.delete_file(old_content)
    return jsonify(ok=True, url=S.media_url(new_content))


@route("/moodboards/<int:bid>/arrange", methods=["POST"])
def board_arrange(bid):
    """One-click tidy-up: snap every item on this board back into a neat grid."""
    board_or_404(bid)
    rows = q("SELECT id FROM board_items WHERE board_id=? AND workspace_id=? ORDER BY z, id", (bid, W()))
    for i, r in enumerate(rows):
        col, row = i % ITEM_COLS, i // ITEM_COLS
        ex("UPDATE board_items SET x=?, y=?, w=?, h=?, z=? WHERE id=?",
           (ITEM_GAP + col * (ITEM_W + ITEM_GAP), ITEM_GAP + row * (ITEM_H + ITEM_GAP), ITEM_W, ITEM_H, i + 1, r["id"]))
    flash("Tidied up.")
    return redirect(url_for("board_view", bid=bid))


@route("/moodboards/item/<int:iid>/delete", methods=["POST"])
def board_item_delete(iid):
    it = q("SELECT * FROM board_items WHERE id=? AND workspace_id=?", (iid, W()), one=True) or abort(404)
    if it["kind"] == "image":
        S.delete_file(it["content"])
    ex("DELETE FROM board_items WHERE id=? AND workspace_id=?", (iid, W()))
    return redirect(url_for("board_view", bid=it["board_id"]))


@route("/moodboards/<int:bid>/delete", methods=["POST"])
def board_delete(bid):
    board_or_404(bid)
    for it in q("SELECT * FROM board_items WHERE board_id=? AND workspace_id=? AND kind='image'", (bid, W())):
        S.delete_file(it["content"])
    ex("DELETE FROM board_items WHERE board_id=? AND workspace_id=?", (bid, W()))
    ex("DELETE FROM boards WHERE id=? AND workspace_id=?", (bid, W()))
    S.audit("delete", f"board#{bid}")
    return redirect(url_for("moodboards"))


@route("/media/<int:wid>/<name>")
def media(wid, name):
    if wid != W():
        abort(404)
    return send_from_directory(os.path.join(C.UPLOAD_DIR, str(wid)), os.path.basename(name))


# ----------------------------------------------------------------- latest updates (RSS/Atom)
_cache = {}


def _txt(d, *names):
    for n in names:
        e = d.get(n)
        if e is not None and (e.text or "").strip():
            return e.text.strip()
    return ""


def parse_feed(xml, source, cat):
    out = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return out
    for it in root.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"):
            continue
        d = {c.tag.split("}")[-1]: c for c in it}
        link = ""
        if d.get("link") is not None:
            link = d["link"].get("href") or (d["link"].text or "")
        link = S.clean_url(link.strip())
        raw, ts = _txt(d, "pubDate", "published", "updated", "date"), 0.0
        try:
            ts = parsedate_to_datetime(raw).timestamp()
        except Exception:
            try:
                ts = dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
            except Exception:
                pass
        desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", _txt(d, "description", "summary", "content"))).strip()[:280]
        out.append(dict(title=_txt(d, "title")[:200], url=link, source=source, category=cat, ts=ts,
                        date=dt.datetime.fromtimestamp(ts).strftime("%d %b %Y") if ts else "", summary=desc))
    return out[:15]


def fetch_all(wid, force=False):
    c = _cache.get(wid)
    if c and not force and dt.datetime.now().timestamp() - c["t"] < 900:
        return c
    feeds = [dict(r) for r in q("SELECT * FROM feeds WHERE workspace_id=? ORDER BY id LIMIT 25", (wid,))]
    items, errors = [], []

    def one(fd):
        try:
            return parse_feed(S.safe_get(fd["url"]), fd["name"], fd["category"]), None
        except Exception as e:
            return [], f"{fd['name']}: {type(e).__name__}"

    with ThreadPoolExecutor(8) as pool:
        for res, err in pool.map(one, feeds):
            items += res
            if err:
                errors.append(err)
    items.sort(key=lambda i: i["ts"], reverse=True)
    c = _cache[wid] = dict(t=dt.datetime.now().timestamp(), items=items, errors=errors)
    return c


@route("/updates")
def updates():
    c = fetch_all(W(), force=bool(request.args.get("refresh")))
    cat = request.args.get("cat", "")
    return render_template("updates.html", items=[i for i in c["items"] if not cat or i["category"] == cat][:120], cats=sorted({i["category"] for i in c["items"]}), cat=cat, errors=c["errors"])


@route("/updates/save", methods=["POST"])
def updates_save():
    url = S.clean_url(request.form.get("url", ""))
    if url:
        ins("reference_links", dict(workspace_id=W(), title=S.clean_text(request.form.get("title"), 200), url=url, category="Article", tags=S.clean_text(request.form.get("source"), 100), notes="Saved from Latest Updates", favorite="No"))
        flash("Saved to Reference Links.")
    return redirect(url_for("updates"))


# ----------------------------------------------------------------- analytics & UTM
@route("/analytics")
def analytics():
    w, series = W(), {}
    for r in q("SELECT * FROM kpis WHERE workspace_id=? AND period!='' ORDER BY period LIMIT 3000", (w,)):
        series.setdefault(r["metric"], []).append(dict(d=r["period"], v=num(r["value"]), t=num(r["target"]) if r["target"] else None))
    camps = [dict(n=c["name"], b=num(c["budget"]), s=num(c["spent"])) for c in q("SELECT * FROM campaigns WHERE workspace_id=?", (w,))]
    funnel = [dict(s=r["stage"], c=r["c"]) for r in q("SELECT stage, COUNT(*) c FROM leads WHERE workspace_id=? GROUP BY stage", (w,))]
    return render_template("analytics.html", series=dict(list(series.items())[:12]), camps=camps, funnel=funnel)


# ----------------------------------------------------------------- Marketing Health (KPIs + a single gap checklist, for a one-person marketing team)
def _brand_checks():
    kinds = {r["kind"] for r in q("SELECT kind FROM brand_kit WHERE workspace_id=?", (W(),))}
    return [("Primary colour", bool(g.ws["brand_color"]) or "Colour" in kinds),
            ("Logo", bool(g.ws["logo_url"])),
            ("Font", "Font" in kinds),
            ("Voice & tone", "Voice & tone" in kinds)]


def _marketing_gaps():
    w, t = W(), S.today().isoformat()
    missing_brand = len([c for c in _brand_checks() if not c[1]])
    return [
        dict(key="brand_kit", label="Brand Kit categories not filled in yet (colour, logo, font, voice & tone)",
             count=missing_brand, href=url_for("m_list", key="brand_kit")),
        dict(key="campaigns", label="Live or planned campaigns with no KPI target set",
             count=q("SELECT COUNT(*) c FROM campaigns WHERE workspace_id=? AND status IN ('Planning','Live') AND (kpi_target IS NULL OR kpi_target='')", (w,), one=True)["c"],
             href=url_for("m_list", key="campaigns")),
        dict(key="content_items", label="Content items with no publish date (won't show on the calendar)",
             count=q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND (publish_date IS NULL OR publish_date='') AND status NOT IN ('Published','On hold')", (w,), one=True)["c"],
             href=url_for("m_list", key="content_items")),
        dict(key="content_overdue", label="Content items past their publish date but not marked Published",
             count=q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND publish_date!='' AND publish_date<? AND status NOT IN ('Published','On hold')", (w, t), one=True)["c"],
             href=url_for("calendar_view")),
        dict(key="tasks", label="Overdue tasks",
             count=q("SELECT COUNT(*) c FROM tasks WHERE workspace_id=? AND status!='Done' AND due_date!='' AND due_date<?", (w, t), one=True)["c"],
             href=url_for("m_list", key="tasks")),
        dict(key="leads", label="Leads in progress with no next step planned",
             count=q("SELECT COUNT(*) c FROM leads WHERE workspace_id=? AND stage NOT IN ('Won','Lost') AND (next_step IS NULL OR next_step='')", (w,), one=True)["c"],
             href=url_for("m_list", key="leads")),
    ]


@route("/marketing-health")
def marketing_health():
    w, t = W(), S.today().isoformat()
    brand_checks = _brand_checks()
    brand_score = round(100 * sum(1 for _, ok in brand_checks if ok) / len(brand_checks))
    due = q("SELECT status FROM content_items WHERE workspace_id=? AND publish_date!='' AND publish_date<=?", (w, t))
    n_due, n_published = len(due), len([r for r in due if r["status"] == "Published"])
    posting_pct = round(100 * n_published / n_due) if n_due else None
    camps = q("SELECT * FROM campaigns WHERE workspace_id=?", (w,))
    budgeted = [c for c in camps if c["status"] in ("Live", "Completed") and num(c["budget"]) > 0]
    util_pct = round(100 * sum(num(c["spent"]) for c in budgeted) / sum(num(c["budget"]) for c in budgeted)) if budgeted else None
    over_budget = len([c for c in budgeted if num(c["spent"]) > num(c["budget"])])
    leads = q("SELECT stage, value FROM leads WHERE workspace_id=?", (w,))
    won = [r for r in leads if r["stage"] == "Won"]
    conv_pct = round(100 * len(won) / len(leads)) if leads else None
    gaps = _marketing_gaps()
    return render_template("marketing_health.html", brand_checks=brand_checks, brand_score=brand_score,
                           n_due=n_due, n_published=n_published, posting_pct=posting_pct,
                           n_campaigns=len(camps), util_pct=util_pct, over_budget=over_budget,
                           n_leads=len(leads), n_won=len(won), conv_pct=conv_pct, won_value=sum(num(r["value"]) for r in won),
                           gaps=gaps, smtp_on=bool(C.SMTP_HOST))


@route("/utm")
def utm():
    return render_template("utm.html", rows=q("SELECT * FROM utm_links WHERE workspace_id=? ORDER BY id DESC LIMIT 50", (W(),)),
                           camps=[r["name"] for r in q("SELECT name FROM campaigns WHERE workspace_id=?", (W(),))])


# ----------------------------------------------------------------- AI studio (metered)
@route("/ai")
def ai_studio():
    industry = g.ws["industry"]
    mine = [(k, v[0], C.AI_COST.get(k, 1) + (C.AI_RESEARCH_EXTRA if k in FORCE_RESEARCH else 0)) for k, v in AI_TASKS.items() if industry in AI_TASK_FOR.get(k, ())]
    live = [(k, AI_TASKS[k][0], C.AI_COST.get(k, 1) + C.AI_RESEARCH_EXTRA) for k in AI_TASKS if k in FORCE_RESEARCH] if C.AI_WEB_SEARCH else []
    rest = [(k, v[0], C.AI_COST.get(k, 1)) for k, v in AI_TASKS.items() if k not in AI_TASK_FOR and k not in FORCE_RESEARCH and k not in HIDDEN_TASKS]
    return render_template("ai.html", tasks=mine + live + rest, n_mine=len(mine), n_live=len(live), ind=IND.get(industry), has_key=bool(C.ANTHROPIC_API_KEY),
                           used=S.credits_used(W()), limit=g.plan["ai_credits"], web=C.AI_WEB_SEARCH, extra=C.AI_RESEARCH_EXTRA, force=sorted(FORCE_RESEARCH))


class ClaudeError(Exception):
    pass


def claude_call(system, prompt, max_tokens, research=False):
    """One Claude request (optionally with live web search). Returns (text, sources). Sources are the pages Claude actually used."""
    body = {"model": C.GTM_MODEL, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": prompt}]}
    if research:
        body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 4, "user_location": {"type": "approximate", "country": "IN", "timezone": "Asia/Kolkata"}}]
    headers = {"x-api-key": C.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    texts, sources, first = [], {}, list(body["messages"])
    for _ in range(3):                                   # a long search can pause the turn; continue up to twice
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=180)
        data = r.json()
        if r.status_code != 200:
            msg = (data.get("error", {}).get("message", "") if isinstance(data, dict) else "") or ""
            raise ClaudeError("web" if research and ("web_search" in msg.lower() or "web search" in msg.lower()) else "")
        for blk in data.get("content", []):
            if blk.get("type") == "text":
                texts.append(blk.get("text", ""))
                for c in blk.get("citations") or []:
                    u = S.clean_url(c.get("url"))
                    if u:
                        sources.setdefault(u, S.clean_text(c.get("title"), 140) or u)
            elif blk.get("type") == "web_search_tool_result" and isinstance(blk.get("content"), list):
                for c in blk["content"]:
                    u = S.clean_url(c.get("url")) if isinstance(c, dict) else ""
                    if u:
                        sources.setdefault(u, S.clean_text(c.get("title"), 140) or u)
        if data.get("stop_reason") != "pause_turn":
            break
        body["messages"] = first + [{"role": "assistant", "content": data["content"]}]
    return "".join(texts), list(sources.items())[:12]


def ai_guard(cost):
    """Shared checks before any AI call: configured, verified email, platform daily cap, monthly credits. Returns (error_response, used, limit)."""
    if not C.ANTHROPIC_API_KEY:
        return (jsonify(error="AI is not configured on this server yet."), 400), 0, 0
    if not g.user["email_verified"]:
        return (jsonify(error="Please verify your email to use AI Studio (use the link in the yellow banner, or press Resend link)."), 403), 0, 0
    used, limit = S.credits_used(W()), g.plan["ai_credits"]
    if C.AI_DAILY_CAP and q("SELECT COALESCE(SUM(credits),0) c FROM ai_usage WHERE created_at>=?", (S.today().isoformat(),), one=True)["c"] + cost > C.AI_DAILY_CAP:
        S.audit("ai_daily_cap_hit")
        return (jsonify(error="AI Studio is very busy today and has reached its daily limit. Please try again tomorrow."), 503), used, limit
    if used + cost > limit:
        return (jsonify(error=f"You've used {used} of {limit} AI credits this month. Upgrade your plan or wait for the monthly reset."), 402), used, limit
    return None, used, limit


def workspace_context():
    """Plan, personas and brand kit, for prompts that should sound like this business."""
    parts = []
    p = q("SELECT * FROM gtm_plans WHERE workspace_id=? ORDER BY id DESC LIMIT 1", (W(),), one=True)
    if p:
        parts.append("LATEST GTM PLAN:\n" + "\n".join(f"{k}: {p[k]}" for k in p.keys() if p[k] and k not in ("id", "created_at", "workspace_id")))
    pers = q("SELECT * FROM personas WHERE workspace_id=? ORDER BY id DESC LIMIT 3", (W(),))
    if pers:
        parts.append("PERSONAS:\n" + "\n".join(f"{p['name']} ({p['role']}): pains {p['pain_points']}; goals {p['goals']}; objections {p['objections']}" for p in pers))
    brand = q("SELECT * FROM brand_kit WHERE workspace_id=? LIMIT 40", (W(),))
    if brand:
        parts.append("BRAND KIT:\n" + "\n".join(f"{b['kind']} - {b['name']}: {b['value']} {b['notes']}" for b in brand))
    return parts


def ai_fail(e):
    if isinstance(e, ClaudeError) and str(e) == "web":
        return jsonify(error="Live web research isn't enabled for this server's AI account yet. Ask the administrator to enable web search in the Anthropic console, or untick live research."), 502
    return jsonify(error="The AI service returned an error. Please try again." if isinstance(e, ClaudeError) else "Could not reach the AI service. Please try again."), 502


@route("/api/ai", methods=["POST"])
@limiter.limit("5 per minute;60 per hour")
def api_ai():
    d = S.jbody()
    if not C.ANTHROPIC_API_KEY:
        return jsonify(error="AI is not configured on this server yet."), 400
    task = d.get("task")
    if task not in AI_TASKS or task in HIDDEN_TASKS:
        return jsonify(error="Unknown task"), 400
    research = bool(d.get("research")) or task in FORCE_RESEARCH
    if research and not C.AI_WEB_SEARCH:
        return jsonify(error="Live web research is switched off on this server."), 400
    cost = C.AI_COST.get(task, 1) + (C.AI_RESEARCH_EXTRA if research else 0)
    err, used, limit = ai_guard(cost)
    if err:
        return err
    t = lambda k, n=1000: S.clean_text(d.get(k, ""), n)
    ind = IND.get(g.ws["industry"])
    parts = [f"TASK: {AI_TASKS[task][1]}", f"Business industry: {ind['label']}", f"Product/brand: {t('product')}", f"Target audience: {t('audience')}", f"Tone: {t('tone')}", f"Extra instructions: {t('extra', 8000)}"]
    if d.get("use_plan"):
        parts += workspace_context()
    if task == "report":
        parts.append("KPI LOG (latest 80):\n" + "\n".join(f"{r['period']} {r['metric']} ({r['channel']}): actual {r['value']} vs target {r['target']}" for r in q("SELECT * FROM kpis WHERE workspace_id=? ORDER BY period DESC LIMIT 80", (W(),))))
        parts.append("CAMPAIGNS:\n" + "\n".join(f"{c['name']} [{c['status']}] budget {c['budget']} spent {c['spent']} KPI {c['kpi_target']}" for c in q("SELECT * FROM campaigns WHERE workspace_id=?", (W(),))))
    if research:
        parts.append("Use the web search tool for current facts. Prefer recent, reputable sources (Indian and global). Do not present anything you did not find as fact.")
    try:
        text, sources = claude_call(SYSTEM + "\nINDUSTRY CONTEXT: " + ind["ai_context"], "\n".join(parts), 6000 if task == "calendar" else 4000, research)
    except Exception as e:
        return ai_fail(e)
    ins("ai_usage", dict(workspace_id=W(), user_id=g.user["id"], task=task, credits=cost, month=S.month_key()))
    return jsonify(text=text, sources=[dict(url=u, title=tl) for u, tl in sources], used=used + cost, limit=limit)


@route("/api/ask", methods=["POST"])
@limiter.limit("10 per minute;60 per hour")
def api_ask():
    """Ask Debut: a free-form question answered using this workspace's own data as context."""
    d = S.jbody()
    question = S.clean_text(d.get("q", ""), 500)
    if not question:
        return jsonify(error="Type a question first."), 400
    if not C.ANTHROPIC_API_KEY:
        return jsonify(error="AI is not configured on this server yet."), 400
    if not g.user["email_verified"]:
        return jsonify(error="Please verify your email to use Ask Debut."), 403
    cost = C.AI_COST.get("ask_debut", 1)
    err, used, limit = ai_guard(cost)
    if err:
        return err
    parts = ["The user is asking a question inside their own marketing workspace. Answer directly and specifically using the context below where relevant. "
             "If the answer depends on their own data and nothing below covers it, say so plainly instead of guessing. Keep it concise — a few sentences or a short list, not an essay.",
             f"QUESTION: {question}"]
    parts += workspace_context()
    counts = {m["title"]: q(f"SELECT COUNT(*) c FROM {key} WHERE workspace_id=?", (W(),), one=True)["c"] for key, m in list(MODULES.items())[:12] if not locked(key)}
    parts.append("WHAT THEY HAVE IN THE APP RIGHT NOW: " + ", ".join(f"{k}: {v}" for k, v in counts.items() if v))
    try:
        text, _ = claude_call(SYSTEM + "\nYou are 'Ask Debut', a built-in assistant inside the Debut marketing app. You can also point the user to the right page in the app by name (e.g. 'see GTM Plans' or 'check Market Pulse') when that's the real answer.",
                               "\n".join(parts), 900, research=False)
    except Exception as e:
        return ai_fail(e)
    ins("ai_usage", dict(workspace_id=W(), user_id=g.user["id"], task="ask_debut", credits=cost, month=S.month_key()))
    return jsonify(text=text, used=used + cost, limit=limit)


@route("/api/save_asset", methods=["POST"])
def api_save_asset():
    d = S.jbody()
    ins("assets", dict(workspace_id=W(), title=S.clean_text(d.get("title", "AI output"), 200), type=S.clean_text(d.get("type", "AI"), 50), channel="Other", status="Draft", campaign="", body=S.clean_text(d.get("body", ""), 50000)))
    return jsonify(ok=True)


@route("/api/import_calendar", methods=["POST"])
def api_import_calendar():
    txt = str(S.jbody().get("text", ""))
    a, b = txt.find("["), txt.rfind("]")
    try:
        arr = json.loads(txt[a:b + 1])
    except Exception:
        return jsonify(error="Could not parse JSON from the AI output. Try generating again."), 400
    n = 0
    room = g.plan["records"] - S.record_count(W())
    for it in arr[:120]:
        if not isinstance(it, dict) or n >= room:
            continue
        ch, fm = it.get("channel", "Other"), it.get("format", "Post")
        try:
            date = dt.date.fromisoformat(str(it.get("publish_date", ""))[:10]).isoformat()
        except ValueError:
            date = ""
        ins("content_items", dict(workspace_id=W(), title=S.clean_text(it.get("title", ""), 200), channel=ch if ch in CHANNELS else "Other", format=fm if fm in FORMATS else "Post", status="Planned",
                                  publish_date=date, copy=S.clean_text(it.get("copy", "")), cta=S.clean_text(it.get("cta", ""), 300), hashtags=S.clean_text(it.get("hashtags", ""), 500)))
        n += 1
    return jsonify(ok=True, n=n)


# ----------------------------------------------------------------- content ops
@route("/content-ops")
def content_ops():
    w, today = W(), S.today().isoformat()
    orders = q("SELECT * FROM content_orders WHERE workspace_id=?", (w,))
    done = [o for o in orders if o["status"] in DONE_ORDER]
    rev, cost = sum(num(o["price_client"]) for o in done), sum(num(o["cost_creator"]) for o in done)
    open_orders = [o for o in orders if o["status"] not in DONE_ORDER + ("Cancelled",)]
    pipe = sum(num(o["price_client"]) for o in open_orders)
    by = {}
    for o in orders:
        if o["creator"]:
            d = by.setdefault(o["creator"], dict(n=0, done=0, qs=[], rev=0))
            d["n"] += 1
            if o["status"] in DONE_ORDER:
                d["done"] += 1
                d["rev"] += num(o["price_client"]) - num(o["cost_creator"])
            if o["quality_score"]:
                d["qs"].append(num(o["quality_score"]))
    creators = sorted([(k, v["n"], v["done"], round(sum(v["qs"]) / len(v["qs"]), 1) if v["qs"] else "-", v["rev"]) for k, v in by.items()], key=lambda x: -x[2])
    pays = q("SELECT * FROM payments WHERE workspace_id=? AND status!='Paid'", (w,))
    slug = g.ws["slug"]
    return render_template("content_ops.html", rev=rev, cost=cost, pipe=pipe, overdue=[o for o in open_orders if o["due_date"] and o["due_date"] < today],
                           unassigned=[o for o in open_orders if not o["creator"]], stat=Counter(o["status"] for o in orders), creators=creators,
                           money_in=sum(num(p["amount"]) for p in pays if p["direction"].endswith("(in)")), money_out=sum(num(p["amount"]) for p in pays if p["direction"].endswith("(out)")),
                           pc=Counter(c["status"] for c in q("SELECT status FROM creators WHERE workspace_id=?", (w,))), n_orders=len(orders), statuses=ORDER_STATUS,
                           apply_url=C.APP_URL + url_for("apply_form", slug=slug))


@route("/orders/<int:oid>/match")
def order_match(oid):
    o = row_or_404("content_orders", oid)
    skill, lang = ORDER_SKILL.get(o["type"], ""), request.args.get("lang", "").strip().lower()
    cs = [c for c in q("SELECT * FROM creators WHERE workspace_id=? AND status IN ('Vetted','Active')", (W(),))
          if (not skill or skill.lower() in (c["skills"] or "").lower()) and (not lang or lang in (c["languages"] or "").lower())]
    cs.sort(key=lambda c: (-num(c["rating"]), -num(c["test_score"])))
    return render_template("match.html", o=o, skill=skill, cs=cs, lang=lang)


@route("/orders/<int:oid>/assign/<int:cid>", methods=["POST"])
def order_assign(oid, cid):
    row_or_404("content_orders", oid)
    c = row_or_404("creators", cid)
    ex("UPDATE content_orders SET creator=?, status=CASE WHEN status='Brief received' THEN 'Assigned' ELSE status END WHERE id=? AND workspace_id=?", (c["name"], oid, W()))
    flash(f"Assigned to {c['name']}.")
    return redirect(url_for("m_edit", key="content_orders", rid=oid))


@route("/apply/<slug>", methods=["GET", "POST"])
@limiter.limit("6 per hour", methods=["POST"])
def apply_form(slug):
    """Public creator application form. Each workspace has its own link."""
    ws = q("SELECT * FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    if not S.feature_ok(ws, "content_ops"):
        abort(404)
    if request.method == "POST":
        f = request.form
        if not f.get("website"):  # honeypot: bots fill hidden fields
            if q("SELECT COUNT(*) c FROM creators WHERE workspace_id=?", (ws["id"],), one=True)["c"] < 5000:
                t = S.clean_text
                ins("creators", dict(workspace_id=ws["id"], name=t(f.get("name"), 100), email=t(f.get("email"), 150), phone=t(f.get("phone"), 40), skills=t(f.get("skills"), 300),
                                     niches=t(f.get("niches"), 300), languages=t(f.get("languages"), 200), city=t(f.get("city"), 80), portfolio_url=S.clean_url(f.get("portfolio_url", "")),
                                     rate=t(f.get("rate"), 80), status="Applied", notes=t(f.get("notes"), 1000)))
        return render_template("apply.html", done=True, skills_hint=SKILLS_HINT, ws=ws, bare=True)
    return render_template("apply.html", done=False, skills_hint=SKILLS_HINT, ws=ws, bare=True)


# ----------------------------------------------------------------- influencer discovery & outreach
def discover_links(kw, city, lang):
    query = " ".join(x for x in [kw, city, lang] if x).strip()
    tag = re.sub(r"[^a-z0-9]", "", kw.lower())
    gg = lambda s: "https://www.google.com/search?q=" + quote_plus(s)
    Q = quote_plus(query)
    out = OrderedDict()
    out["Instagram"] = ([("Hashtag: #" + tag, f"https://www.instagram.com/explore/tags/{tag}/")] if tag else []) + [
        ("Google: profiles", gg(f'site:instagram.com "{query}"')), ("Google: with contact / collab info", gg(f'site:instagram.com "{query}" ("collab" OR "email" OR "DM for" OR "business")'))]
    out["YouTube"] = [("Channels search", f"https://www.youtube.com/results?search_query={Q}&sp=EgIQAg%253D%253D"), ("Videos search", f"https://www.youtube.com/results?search_query={Q}")]
    out["LinkedIn"] = [("People", f"https://www.linkedin.com/search/results/people/?keywords={Q}"), ("Posts", f"https://www.linkedin.com/search/results/content/?keywords={Q}")]
    out["X / Twitter"] = [("Accounts", f"https://x.com/search?q={Q}&f=user"), ("Posts", f"https://x.com/search?q={Q}")]
    out["Facebook"] = [("Pages", f"https://www.facebook.com/search/pages?q={Q}"), ("Groups", f"https://www.facebook.com/search/groups?q={Q}")]
    out["Threads"] = [("Search", f"https://www.threads.net/search?q={Q}")]
    out["Pinterest"] = [("Creators", f"https://www.pinterest.com/search/users/?q={Q}")]
    out["Reddit"] = [("Communities & posts", f"https://www.reddit.com/search/?q={Q}")]
    out["ShareChat / Moj"] = [("Google: profiles", gg(f'site:sharechat.com "{query}"'))]
    out["Podcasts"] = [("Apple Podcasts via Google", gg(f'site:podcasts.apple.com "{query}"'))]
    out["Blogs & newsletters"] = [("Blogs open to collabs", gg(f'"{query}" blog ("collaborate" OR "work with brands" OR "write for us")')), ("Substack", gg(f'site:substack.com "{query}"'))]
    out["Any platform"] = [("Influencer lists / rate cards", gg(f'"{query}" influencers list India')), ("Contact emails (public)", gg(f'"{query}" influencer "business enquiries" OR "collab" email'))]
    return out


DISCOVERY_TOOLS = [("Modash", "https://www.modash.io"), ("Qoruz", "https://www.qoruz.com"), ("Winkl", "https://www.winkl.co"),
                   ("Kofluence", "https://www.kofluence.com"), ("Plixxo", "https://www.plixxo.com"), ("Upfluence", "https://www.upfluence.com")]


@route("/discover")
def discover():
    kw, city, lang = request.args.get("kw", "").strip()[:100], request.args.get("city", "").strip()[:60], request.args.get("lang", "").strip()[:40]
    return render_template("discover.html", kw=kw, city=city, lang=lang, links=discover_links(kw, city, lang) if kw else None, tools=DISCOVERY_TOOLS, platforms=PLATFORMS)


@route("/influencers/<int:iid>/outreach")
def outreach(iid):
    inf = row_or_404("influencers", iid)
    tpls = q("SELECT * FROM outreach_templates WHERE workspace_id=? ORDER BY id", (W(),))
    tid = request.args.get("t") or (tpls[0]["id"] if tpls else None)
    brand, campaign, sender = request.args.get("brand", "our brand")[:80], request.args.get("campaign", "our upcoming campaign")[:120], request.args.get("sender", "")[:80]
    tpl = next((t for t in tpls if str(t["id"]) == str(tid)), None)
    subject = body = ""
    if tpl:
        def fill(t):
            for k, v in dict(name=(inf["name"] or "there").split(" ")[0], brand=brand, platform=inf["platform"], campaign=campaign, sender=sender).items():
                t = t.replace("{" + k + "}", v or "")
            return t
        subject, body = fill(tpl["subject"]), fill(tpl["body"])
    mailto = f"mailto:{quote(inf['email'])}?subject={quote(subject)}&body={quote(body)}" if inf["email"] else ""
    return render_template("outreach.html", inf=inf, tpls=tpls, tid=str(tid), brand=brand, campaign=campaign, sender=sender, subject=subject, body=body, mailto=mailto)


@route("/influencers/<int:iid>/contacted", methods=["POST"])
def influencer_contacted(iid):
    row_or_404("influencers", iid)
    t = S.today()
    ex("UPDATE influencers SET last_contacted=?, next_followup=?, status=CASE WHEN status IN ('Prospect','Shortlisted') THEN 'Contacted' ELSE status END WHERE id=? AND workspace_id=?",
       (t.isoformat(), (t + dt.timedelta(days=4)).isoformat(), iid, W()))
    flash("Marked as contacted; follow-up set for 4 days from now.")
    return redirect(url_for("m_list", key="influencers"))


@route("/events/<int:eid>/checklist", methods=["POST"])
def event_checklist(eid):
    e = row_or_404("events", eid)
    items = ONLINE_CHECK if request.form.get("mode") == "online" else OFFLINE_CHECK
    try:
        base = dt.date.fromisoformat(e["date"])
    except (ValueError, TypeError):
        base = None
    for title, off in items:
        ins("tasks", dict(workspace_id=W(), title=title, description="", assignee=e["owner"], due_date=(base + dt.timedelta(days=off)).isoformat() if base else "", priority="Medium", status="To do", related=e["name"]))
    flash(f"Added {len(items)} checklist tasks to Tasks" + ("" if base else " (set an event date to auto-fill due dates)") + ".")
    return redirect(url_for("m_list", key="tasks", q=e["name"]))


# ----------------------------------------------------------------- group mode: team hub (lead / admin / owner) and idea bank
@route("/team-hub")
@S.roles(*C.TEAM_MANAGERS)
def team_hub():
    """One screen for a team lead: who is doing what, what is overdue, what needs approval, what publishes soon."""
    w, today = W(), S.today()
    t, wk, ago = today.isoformat(), (today + dt.timedelta(days=7)).isoformat(), (today - dt.timedelta(days=7)).isoformat()
    members = q("SELECT m.role, u.id AS uid, u.name, u.email, u.last_login FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=? AND m.role!='client' ORDER BY m.id", (w,))
    tasks = q("SELECT * FROM tasks WHERE workspace_id=? AND status!='Done' ORDER BY due_date LIMIT 3000", (w,))
    items = q("SELECT owner, status FROM content_items WHERE workspace_id=? AND status NOT IN ('Published') LIMIT 5000", (w,))
    acts = {r["user_id"]: r["c"] for r in q("SELECT user_id, COUNT(*) c FROM audit_log WHERE workspace_id=? AND created_at>=? GROUP BY user_id", (w, ago))}
    rows = []
    for m in members:
        keys = {(m["name"] or "").strip().lower(), (m["email"] or "").lower()} - {""}
        mine = [x for x in tasks if (x["assignee"] or "").strip().lower() in keys]
        rows.append(dict(m=m, open=len(mine), overdue=len([x for x in mine if x["due_date"] and x["due_date"] < t]),
                         content=len([x for x in items if (x["owner"] or "").strip().lower() in keys]), actions=acts.get(m["uid"], 0)))
    overdue = [x for x in tasks if x["due_date"] and x["due_date"] < t]
    unassigned = [x for x in tasks if not (x["assignee"] or "").strip()]
    review = q("SELECT * FROM content_items WHERE workspace_id=? AND status='Review' ORDER BY publish_date LIMIT 30", (w,))
    orders = q("SELECT * FROM content_orders WHERE workspace_id=? AND status IN ('Editing / QA','Client review') ORDER BY due_date LIMIT 30", (w,))
    soon = q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ? AND status!='Published' ORDER BY publish_date LIMIT 30", (w, t, wk))
    feed = q("SELECT a.*, u.name AS uname FROM audit_log a LEFT JOIN users u ON u.id=a.user_id WHERE a.workspace_id=? ORDER BY a.id DESC LIMIT 15", (w,))
    return render_template("team_hub.html", rows=rows, overdue=overdue[:10], unassigned=unassigned[:10], n_overdue=len(overdue), n_open=len(tasks), review=review, orders=orders, soon=soon, feed=feed, today=t)


@route("/ideas")
def ideas():
    ind = IND.get(g.ws["industry"])
    have = {r["name"] for r in q("SELECT name FROM personas WHERE workspace_id=?", (W(),))}
    return render_template("ideas.html", ind=ind, can_kpi="analytics" in g.plan["features"], have_personas=have)


@route("/ideas/picker")
def ideas_picker():
    """A handful of content ideas only - just the part of Idea Bank someone drafting a content item actually
    needs - shown as a small overlay (pop-up, with a close/cross) instead of leaving the page for the full
    Idea Bank. There's no separate 'idea bank for this' destination: it's the same ideas, in a smaller box."""
    ind = IND.get(g.ws["industry"])
    return render_template("ideas_picker.html", ind=ind)


# ----------------------------------------------------------------- comments, notifications
@route("/m/<key>/<int:rid>/comment", methods=["POST"])
def comment_add(key, rid):
    m = mod(key)
    row = row_or_404(key, rid)
    body = S.clean_text(request.form.get("body"), 2000)
    back = url_for("m_edit", key=key, rid=rid) + "#comments"
    if not body:
        flash("Write a comment first.")
        return redirect(back)
    shared = bool(request.form.get("client_visible")) and key == "content_items" and g.role in ("owner", "admin", "lead", "manager") and bool((row["client"] or "").strip())
    ins("comments", dict(workspace_id=W(), module=key, record_id=rid, user_id=g.user["id"], body=body, client_visible=1 if shared else 0))
    S.audit("comment", f"{key}#{rid}" + (" (shared with client)" if shared else ""))
    if shared:
        for cm in S.client_members(W(), row["client"]):
            S.notify(W(), cm["uid"], "client_comment", f"{g.user['name'] or g.user['email']} replied on {_title(m, row)}: {body[:80]}", url_for("portal_item", iid=rid))
    targets = set(S.mentioned_ids(W(), body))
    for f in ("assignee", "owner"):
        if f in row.keys():
            mem = S.find_member(W(), row[f])
            if mem:
                targets.add(mem["uid"])
            break
    targets.discard(g.user["id"])
    for uid in targets:
        S.notify(W(), uid, "comment", f"{g.user['name'] or g.user['email']} commented on {_title(m, row)}: {body[:80]}", back)
    return redirect(back)


@route("/comments/<int:cid>/delete", methods=["POST"])
def comment_delete(cid):
    c = q("SELECT * FROM comments WHERE id=? AND workspace_id=?", (cid, W()), one=True) or abort(404)
    if c["user_id"] != g.user["id"] and g.role not in C.TEAM_MANAGERS:
        abort(403)
    ex("DELETE FROM comments WHERE id=? AND workspace_id=?", (cid, W()))
    return redirect(url_for("m_edit", key=c["module"], rid=c["record_id"]) + "#comments")


@route("/notifications")
def notifications():
    rows = q("SELECT * FROM notifications WHERE user_id=? AND workspace_id=? ORDER BY id DESC LIMIT 60", (g.user["id"], W()))
    return render_template("notifications.html", rows=rows)


@route("/notifications/recent")
def notifications_recent():
    """Powers the bell's corner pop-up (the full Notifications page stays as its own tab)."""
    rows = q("SELECT id, message, link, is_read, created_at FROM notifications WHERE user_id=? AND workspace_id=? ORDER BY id DESC LIMIT 8", (g.user["id"], W()))
    return jsonify(items=[dict(id=r["id"], message=r["message"], link=url_for("notification_open", nid=r["id"]), is_read=bool(r["is_read"]),
                               created_at=str(r["created_at"])[:16]) for r in rows])


@route("/notifications/read", methods=["POST"])
def notifications_read():
    ex("UPDATE notifications SET is_read=1 WHERE user_id=? AND workspace_id=?", (g.user["id"], W()))
    return redirect(url_for("notifications"))


@route("/notifications/<int:nid>/open")
def notification_open(nid):
    n = q("SELECT * FROM notifications WHERE id=? AND user_id=? AND workspace_id=?", (nid, g.user["id"], W()), one=True) or abort(404)
    ex("UPDATE notifications SET is_read=1 WHERE id=?", (nid,))
    return redirect(n["link"] if (n["link"] or "").startswith("/") and not n["link"].startswith("//") else url_for("notifications"))


@route("/unsubscribe/<token>")
def unsubscribe(token):
    try:
        uid = URLSafeSerializer(C.SECRET_KEY, salt="unsub").loads(token)
    except BadSignature:
        abort(404)
    ex("UPDATE users SET digest=0 WHERE id=?", (S.to_int(uid) or 0,))
    return render_template("error.html", code="✓", msg="You're unsubscribed from the daily digest. You can turn it back on in Account.", bare=True)


# ----------------------------------------------------------------- client report (printable) + public share link
def build_report(wid, month):
    y, mo = int(month[:4]), int(month[5:7])
    first = dt.date(y, mo, 1)
    nxt = (first + dt.timedelta(days=32)).replace(day=1)
    start, end, nxt_s = first.isoformat(), (nxt - dt.timedelta(days=1)).isoformat(), nxt.isoformat()
    kp = {}
    for r in q("SELECT * FROM kpis WHERE workspace_id=? AND period BETWEEN ? AND ? ORDER BY period", (wid, start, end)):
        kp.setdefault(r["metric"], []).append(r)
    kpis = []
    for name, rows in kp.items():
        last = rows[-1]
        v, t = num(last["value"]), num(last["target"]) if last["target"] else None
        kpis.append(dict(metric=name, channel=last["channel"], value=last["value"], target=last["target"], pct=round(v / t * 100) if t else None, points=len(rows)))
    camps = [c for c in q("SELECT * FROM campaigns WHERE workspace_id=? ORDER BY id DESC LIMIT 200", (wid,))
             if c["status"] == "Live" or ((c["start_date"] or "") <= end and ((c["end_date"] or "9999") >= start))]
    content = q("SELECT * FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ? ORDER BY publish_date", (wid, start, end))
    by_channel = Counter(c["channel"] for c in content)
    published = len([c for c in content if c["status"] == "Published"])
    leads = q("SELECT * FROM leads WHERE workspace_id=? AND created_at>=? AND created_at<? ORDER BY id DESC LIMIT 500", (wid, start, nxt_s))
    promos = q("SELECT * FROM promotions WHERE workspace_id=? AND start_date<=? AND (end_date>=? OR end_date='') ORDER BY start_date LIMIT 50", (wid, end, start))
    events = q("SELECT * FROM events WHERE workspace_id=? AND date BETWEEN ? AND ? ORDER BY date", (wid, start, end))
    audits = q("SELECT * FROM retail_audits WHERE workspace_id=? AND audit_date BETWEEN ? AND ?", (wid, start, end))
    aud = dict(n=len(audits), in_stock=len([a for a in audits if a["availability"] == "In stock"]), posm_ok=len([a for a in audits if a["posm"] == "Present & correct"]))
    return dict(month=month, label=first.strftime("%B %Y"), kpis=kpis, camps=camps, content=content, by_channel=by_channel.most_common(), published=published,
                leads=leads, lead_stage=Counter(l["stage"] for l in leads).most_common(), promos=promos, events=events, audits=aud,
                budget=sum(num(c["budget"]) for c in camps), spent=sum(num(c["spent"]) for c in camps))


def _month(arg):
    return arg if re.match(r"^\d{4}-(0[1-9]|1[0-2])$", arg or "") else S.today().strftime("%Y-%m")


def report_token():
    return URLSafeSerializer(C.SECRET_KEY, salt="report").dumps([W(), g.ws["ics_key"]])


@route("/report")
def report():
    month = _month(request.args.get("month"))
    share = None
    if "analytics" in g.plan["features"] and g.role in ("owner", "admin", "lead", "manager") and g.ws["ics_key"]:
        share = C.APP_URL + url_for("report_public", token=report_token())
    return render_template("report.html", r=build_report(W(), month), ws=g.ws, share=share, public=False, prev_m=(dt.date.fromisoformat(month + "-01") - dt.timedelta(days=1)).strftime("%Y-%m"),
                           next_m=(dt.date.fromisoformat(month + "-01") + dt.timedelta(days=32)).strftime("%Y-%m"))


@route("/r/<token>")
def report_public(token):
    try:
        wid, key_ = URLSafeSerializer(C.SECRET_KEY, salt="report").loads(token)
    except (BadSignature, ValueError, TypeError):
        abort(404)
    ws = q("SELECT * FROM workspaces WHERE id=? AND ics_key=? AND ics_key!=''", (S.to_int(wid) or 0, str(key_)), one=True) or abort(404)
    if not S.feature_ok(ws, "analytics"):
        abort(404)
    month = _month(request.args.get("month"))
    return render_template("report.html", r=build_report(ws["id"], month), ws=ws, share=None, public=True, hide_chrome=True, bare=True,
                           prev_m=(dt.date.fromisoformat(month + "-01") - dt.timedelta(days=1)).strftime("%Y-%m"), next_m=(dt.date.fromisoformat(month + "-01") + dt.timedelta(days=32)).strftime("%Y-%m"))


# ----------------------------------------------------------------- lead capture: hosted form + website webhook
def _add_lead(ws, f, source, consent=False):
    if q("SELECT COUNT(*) c FROM leads WHERE workspace_id=?", (ws["id"],), one=True)["c"] >= 20000:
        return False
    t = S.clean_text
    note = t(f.get("message") or f.get("notes"), 1900)
    if consent:
        note = (note + "\n" if note else "") + f"[Consent to be contacted given on the enquiry form, {S.today().isoformat()}]"
    ins("leads", dict(workspace_id=ws["id"], name=t(f.get("name"), 120), company=t(f.get("company"), 120), email=t(f.get("email"), 200), phone=t(f.get("phone"), 40),
                      source=t(f.get("source"), 120) or source, stage="New", value="", next_step="Follow up", notes=note))
    return True


@route("/lead/<slug>", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def lead_form(slug):
    """Public enquiry form for a workspace: link it from your bio, website or QR code. Creates a lead."""
    ws = q("SELECT * FROM workspaces WHERE slug=?", (slug,), one=True) or abort(404)
    done = False
    if request.method == "POST":
        f = request.form
        if not f.get("website"):     # honeypot
            if not f.get("consent") or not (f.get("email") or f.get("phone")):
                flash("Please add an email or phone number and tick the consent box.")
                return render_template("lead_form.html", ws=ws, done=False, bare=True, hide_chrome=True, form=f), 400
            _add_lead(ws, f, "Website form", consent=True)
        done = True
    return render_template("lead_form.html", ws=ws, done=done, bare=True, hide_chrome=True, form={})


@route("/hooks/lead/<key>", methods=["POST", "OPTIONS"])
@limiter.limit("300 per hour", methods=["POST"])
def lead_hook(key):
    """Webhook for your own website form (or Zapier/Make): POST JSON or form fields name, email, phone, company, message, source."""
    cors = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"}
    if request.method == "OPTIONS":
        return Response("", 204, cors)
    ws = q("SELECT * FROM workspaces WHERE hook_key=? AND hook_key!=''", (key,), one=True)
    if not ws:
        return jsonify(error="unknown key"), 404, cors
    f = request.get_json(silent=True) if request.is_json else request.form
    if not isinstance(f, dict) and not hasattr(f, "get"):
        return jsonify(error="send a JSON object or form fields"), 400, cors
    if not (f.get("email") or f.get("phone")):
        return jsonify(error="email or phone is required"), 400, cors
    if not _add_lead(ws, f, "Webhook"):
        return jsonify(error="workspace is at capacity"), 403, cors
    return jsonify(ok=True), 200, cors


# ----------------------------------------------------------------- feedback (goes to you, with context)
FEEDBACK_KINDS = ["idea", "problem", "question", "praise"]


@route("/feedback", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def feedback():
    page = S.clean_text(request.values.get("page") or request.args.get("from"), 200)
    if request.method == "POST":
        msg, kind = S.clean_text(request.form.get("message"), 3000), request.form.get("kind", "idea")
        if not msg:
            flash("Please write a message first.")
            return render_template("feedback.html", page=page, kinds=FEEDBACK_KINDS), 400
        kind = kind if kind in FEEDBACK_KINDS else "idea"
        fid = ins("feedback", dict(workspace_id=W(), user_id=g.user["id"], kind=kind, page=page, message=msg))
        S.audit("feedback", f"#{fid} {kind}")
        S.send_email(C.SUPPORT_EMAIL, f"[{C.APP_NAME} feedback: {kind}] from {g.user['email']}",
                     f"{msg}\n\n---\nUser: {g.user['name']} <{g.user['email']}> (role {g.role})\nWorkspace: {g.ws['name']} (#{W()}, plan {g.plan_key}, industry {g.ws['industry']})\nPage: {page}\n")
        flash("Thank you! Your feedback reached us. We read every message.")
        return redirect(page if page.startswith("/") and not page.startswith("//") else url_for("dashboard"))
    return render_template("feedback.html", page=page, kinds=FEEDBACK_KINDS)


# ----------------------------------------------------------------- installable app (PWA)
@route("/manifest.webmanifest")
def manifest():
    icons = [dict(src=url_for("static", filename="icons/icon-192.png"), sizes="192x192", type="image/png", purpose="any"),
             dict(src=url_for("static", filename="icons/icon-512.png"), sizes="512x512", type="image/png", purpose="any"),
             dict(src=url_for("static", filename="icons/maskable-512.png"), sizes="512x512", type="image/png", purpose="maskable")]
    return Response(json.dumps(dict(name=C.APP_NAME, short_name=C.APP_NAME[:12], start_url="/app", scope="/", display="standalone", background_color="#faf8ff", theme_color="#7c5cd6", icons=icons)),
                    mimetype="application/manifest+json")


def _sw_cache_version():
    """A cache name that changes whenever static/style.css changes, so every deploy that touches the stylesheet
    automatically invalidates the installed service worker's old cached copy (see SW_JS below) — without this,
    a browser that already has the old service worker installed would keep serving a stale style.css forever,
    since the worker's own script (and so its cache name) would otherwise never change between deploys."""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "style.css")
        with open(p, "rb") as f:
            return "gtm-" + hashlib.md5(f.read()).hexdigest()[:10]
    except OSError:
        return "gtm-v1"


SW_JS = """const V='%s';
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(['/static/style.css','/offline'])));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET')return;const u=new URL(r.url);if(u.origin!==location.origin)return;
if(u.pathname.startsWith('/static/')){e.respondWith(caches.match(r).then(m=>m||fetch(r).then(x=>{const cp=x.clone();caches.open(V).then(c=>c.put(r,cp));return x;})));return;}
if(r.mode==='navigate'){e.respondWith(fetch(r).catch(()=>caches.match('/offline')));}});
""" % _sw_cache_version()


@route("/sw.js")
def service_worker():
    """Only static assets and an offline page are cached: signed-in pages and data are never stored on the device."""
    return Response(SW_JS, mimetype="application/javascript", headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@route("/offline")
def offline():
    return render_template("error.html", code="📡", msg="You're offline. Reconnect to keep working; nothing you saved is lost.", bare=True)


# ----------------------------------------------------------------- client portal: clients see only their own work
STAFF_PREVIEW = ("owner", "admin", "lead", "manager")


def _portal_client():
    """Whose portal this is: a client's own, or (staff preview) the ?client= name."""
    if g.role == "client":
        m = q("SELECT client_name FROM memberships WHERE workspace_id=? AND user_id=?", (W(), g.user["id"]), one=True)
        return (m["client_name"] or "").strip()
    if g.role in STAFF_PREVIEW:
        return S.clean_text(request.args.get("client") or request.form.get("client"), 120)
    abort(403)


def _portal_item(iid, cn):
    it = q("SELECT * FROM content_items WHERE id=? AND workspace_id=?", (iid, W()), one=True) or abort(404)
    if not cn or (it["client"] or "").strip().lower() != cn.lower():
        abort(404)
    return it


def _tell_team(kind, msg, iid, item):
    """Notify the item's owner and every approver when a client acts."""
    seen = set()
    link = url_for("m_edit", key="content_items", rid=iid)
    owner = S.find_member(W(), item["owner"])
    for mem in ([owner] if owner else []) + [x for x in S.members(W()) if x["role"] in ("owner", "admin", "lead", "manager")]:
        if mem["uid"] not in seen:
            seen.add(mem["uid"])
            S.notify(W(), mem["uid"], kind, msg, link)


@route("/portal")
def portal():
    cn = _portal_client()
    if not cn:                                   # staff without a client chosen: pick one
        names = sorted({(r["client"] or "").strip() for k in ("content_items", "campaigns") for r in q(f"SELECT DISTINCT client FROM {k} WHERE workspace_id=?", (W(),)) if (r["client"] or "").strip()}
                       | {(m["client_name"] or "").strip() for m in q("SELECT client_name FROM memberships WHERE workspace_id=? AND role='client'", (W(),))})
        return render_template("portal.html", cn="", names=names, preview=True)
    w, today = W(), S.today().isoformat()
    items = q("SELECT * FROM content_items WHERE workspace_id=? AND LOWER(client)=LOWER(?) ORDER BY publish_date, id", (w, cn))
    camps = q("SELECT * FROM campaigns WHERE workspace_id=? AND LOWER(client)=LOWER(?) ORDER BY id DESC", (w, cn))
    return render_template("portal.html", cn=cn, names=[], preview=g.role != "client",
                           review=[i for i in items if i["status"] == "Review"],
                           upcoming=[i for i in items if i["status"] in ("Approved", "Scheduled") and (i["publish_date"] or "") >= today],
                           published=[i for i in items if i["status"] == "Published"][-10:][::-1], camps=camps, total=len(items))


@route("/portal/item/<int:iid>")
def portal_item(iid):
    cn = _portal_client()
    it = _portal_item(iid, cn)
    thread = q("SELECT c.*, u.name AS uname FROM comments c LEFT JOIN users u ON u.id=c.user_id WHERE c.workspace_id=? AND c.module='content_items' AND c.record_id=? AND c.client_visible=1 ORDER BY c.id", (W(), iid))
    return render_template("portal_item.html", it=it, cn=cn, thread=thread, preview=g.role != "client")


@route("/portal/item/<int:iid>/decide", methods=["POST"])
def portal_decide(iid):
    if g.role != "client":
        abort(403)
    cn = _portal_client()
    it = _portal_item(iid, cn)
    action, note = request.form.get("action"), S.clean_text(request.form.get("comment"), 2000)
    if it["status"] != "Review" or action not in ("approve", "changes"):
        flash("This item is not waiting for your review.")
        return redirect(url_for("portal_item", iid=iid))
    if action == "changes" and not note:
        flash("Please tell us what to change.")
        return redirect(url_for("portal_item", iid=iid))
    if note:
        ins("comments", dict(workspace_id=W(), module="content_items", record_id=iid, user_id=g.user["id"], body=note, client_visible=1))
    who = g.user["name"] or g.user["email"]
    if action == "approve":
        ex("UPDATE content_items SET status='Approved' WHERE id=? AND workspace_id=?", (iid, W()))
        S.audit("client_approved", f"content_items#{iid} by {who}")
        _tell_team("client_approved", f"{cn} approved: {it['title']}", iid, it)
        flash("Approved. Thank you! The team has been notified.")
    else:
        ex("UPDATE content_items SET status='In progress' WHERE id=? AND workspace_id=?", (iid, W()))
        S.audit("client_changes", f"content_items#{iid} by {who}")
        _tell_team("client_changes", f"{cn} requested changes on {it['title']}: {note[:80]}", iid, it)
        flash("Thanks. We've sent your changes to the team.")
    return redirect(url_for("portal"))


@route("/portal/item/<int:iid>/comment", methods=["POST"])
def portal_comment(iid):
    if g.role != "client":
        abort(403)
    it = _portal_item(iid, _portal_client())
    note = S.clean_text(request.form.get("comment"), 2000)
    if note:
        ins("comments", dict(workspace_id=W(), module="content_items", record_id=iid, user_id=g.user["id"], body=note, client_visible=1))
        S.audit("client_comment", f"content_items#{iid}")
        _tell_team("client_comment", f"{g.user['name'] or g.user['email']} ({it['client']}) commented on {it['title']}: {note[:80]}", iid, it)
    return redirect(url_for("portal_item", iid=iid) + "#thread")


# ----------------------------------------------------------------- Market Pulse: live signals for this workspace
PULSE_ROLES = ("owner", "admin", "lead", "manager")
HOLIDAY_COUNTRIES = [("IN", "India"), ("US", "United States"), ("GB", "United Kingdom"), ("AE", "United Arab Emirates"), ("SG", "Singapore"), ("AU", "Australia"), ("CA", "Canada")]


@route("/pulse")
def pulse_page():
    data = S.latest_pulse(W())
    age = S.pulse_age_minutes(data) if data else None
    watch = S.pulse_watch(W(), g.plan["watch"])
    watch_rows = q("SELECT * FROM watchlist WHERE workspace_id=? ORDER BY id DESC", (W(),))
    return render_template("pulse.html", data=data, age=age, watch=watch, watch_rows=watch_rows, limit=g.plan["watch"], can_refresh=g.role in PULSE_ROLES and g.role != "viewer",
                           wait=max(0, C.PULSE_MIN_REFRESH_MINUTES - int(age)) if age is not None else 0, stale=age is None or age > C.PULSE_CACHE_MINUTES,
                           yt=bool(C.YOUTUBE_API_KEY), provider=C.NEWS_PROVIDER, countries=HOLIDAY_COUNTRIES, year=S.today().year, ai=bool(C.ANTHROPIC_API_KEY), cost=C.AI_COST.get("pulse_brief", 2))


@route("/pulse/refresh", methods=["POST"])
@limiter.limit("20 per hour")
@S.roles(*PULSE_ROLES)
def pulse_refresh():
    data = S.latest_pulse(W())
    if data and S.pulse_age_minutes(data) < C.PULSE_MIN_REFRESH_MINUTES:
        flash(f"Market Pulse was refreshed a moment ago. Try again in {C.PULSE_MIN_REFRESH_MINUTES} minutes.")
        return redirect(url_for("pulse_page"))
    if not S.pulse_watch(W(), g.plan["watch"]):
        flash("Add something to track first (see the watchlist below).")
        return redirect(url_for("pulse_page"))
    fresh = S.run_pulse(W(), g.ws["industry"], g.plan)
    S.audit("pulse_refresh", f"{sum(len(x['items']) for x in fresh['groups'])} items")
    flash("Market Pulse refreshed." + (f" {len(fresh['errors'])} source(s) had a problem: see the notes at the bottom." if fresh["errors"] else ""))
    return redirect(url_for("pulse_page"))


@route("/pulse/watch/add", methods=["POST"])
@S.roles(*PULSE_ROLES)
def pulse_watch_add():
    """Add a source to track, right from the Market Pulse page itself - no separate Watchlist tab to find."""
    term = S.clean_text(request.form.get("term"), 120)
    if not term:
        flash("Enter a keyword, brand, competitor or subreddit to track.")
        return redirect(url_for("pulse_page"))
    if q("SELECT COUNT(*) c FROM watchlist WHERE workspace_id=?", (W(),), one=True)["c"] >= g.plan["watch"]:
        flash(f"Your {g.plan['name']} plan can track {g.plan['watch']} items in Market Pulse. Remove one or upgrade for more.")
        return redirect(url_for("pulse_page"))
    typ = request.form.get("type", "Keyword")
    region = request.form.get("region", "India")
    ins("watchlist", dict(workspace_id=W(), term=term, type=typ if typ in ("Keyword", "Competitor", "Brand", "Subreddit") else "Keyword",
                           region=region if region in ("India", "Global", "Both") else "India", notes=""))
    S.audit("create", "watchlist")
    flash(f"Now tracking “{term}”.")
    return redirect(url_for("pulse_page"))


@route("/pulse/watch/<int:wid>/remove", methods=["POST"])
@S.roles(*PULSE_ROLES)
def pulse_watch_remove(wid):
    ex("DELETE FROM watchlist WHERE id=? AND workspace_id=?", (wid, W()))
    S.audit("delete", f"watchlist#{wid}")
    return redirect(url_for("pulse_page"))


@route("/pulse/holidays", methods=["POST"])
@limiter.limit("10 per hour")
@S.roles(*PULSE_ROLES)
def pulse_holidays():
    """Add a country's public holidays to Key Dates (live from the Nager.Date public API)."""
    import pulse
    country, year = (request.form.get("country") or "").upper(), S.to_int(request.form.get("year"), 0)
    if country not in dict(HOLIDAY_COUNTRIES) or not (2020 <= year <= 2100):
        abort(400)
    try:
        days = pulse.public_holidays(country, year)
    except Exception:
        flash("Could not load holidays right now (the holiday service may not cover that country). Please try again later.")
        return redirect(url_for("pulse_page"))
    have = {(r["name"], r["date"]) for r in q("SELECT name, date FROM key_dates WHERE workspace_id=?", (W(),))}
    n = 0
    for h in days[:60]:
        nm, dte = S.clean_text(h["name"], 120), S.clean_text(h["date"], 10)
        if nm and re.match(r"^\d{4}-\d{2}-\d{2}$", dte) and (nm, dte) not in have:
            ins("key_dates", dict(workspace_id=W(), name=nm, date=dte, kind="Festival"))
            n += 1
    S.audit("holidays_import", f"{country} {year} x{n}")
    flash(f"Added {n} public holiday(s) for {dict(HOLIDAY_COUNTRIES)[country]} {year} to your Key Dates." if n else "Those holidays are already in your Key Dates.")
    return redirect(url_for("pulse_page"))


@route("/api/pulse/brief", methods=["POST"])
@limiter.limit("5 per minute;30 per hour")
@S.roles(*PULSE_ROLES)
def pulse_brief():
    """AI reads this week's live items and writes an actionable brief, citing item numbers."""
    data = S.latest_pulse(W())
    if not data or not any(g_["items"] for g_ in data["groups"]):
        return jsonify(error="Refresh Market Pulse first so there is something to analyse."), 400
    cost = C.AI_COST.get("pulse_brief", 2)
    err, used, limit = ai_guard(cost)
    if err:
        return err
    items, n = [], 0
    for grp in data["groups"]:
        for it in grp["items"][:6]:
            n += 1
            if n <= 40:
                items.append(f"[{n}] ({grp['term']}) {it['title']} | {it['source']} | {it['date']} | {it['url']}")
    trends = "; ".join(f"{k}: " + ", ".join(t["term"] for t in v[:8]) for k, v in data.get("trends", {}).items() if v)
    ind = IND.get(g.ws["industry"])
    prompt = "\n".join([f"TASK: Turn this week's live market signals into a practical brief for a {ind['label']} business in India. Use ONLY the numbered items below and cite them like [3]. "
                        "Sections: 1) What is happening (5 bullets). 2) What it means for us. 3) Five opportunities. 4) Three risks or watch-outs. 5) Five content ideas (channel, hook, why now). 6) Three actions for this week. "
                        "If the items are thin or irrelevant, say so plainly instead of stretching them.", f"TRENDING SEARCHES TODAY: {trends or 'not available'}",
                        "RISING WORDS IN HEADLINES: " + ", ".join(t[0] for t in data.get("terms", [])[:10]), "LIVE ITEMS:\n" + "\n".join(items)] + workspace_context())
    try:
        text, _ = claude_call(SYSTEM + "\nINDUSTRY CONTEXT: " + ind["ai_context"], prompt, 3500, False)
    except Exception as e:
        return ai_fail(e)
    ins("ai_usage", dict(workspace_id=W(), user_id=g.user["id"], task="pulse_brief", credits=cost, month=S.month_key()))
    return jsonify(text=text, sources=[], used=used + cost, limit=limit)
