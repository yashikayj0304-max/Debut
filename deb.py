"""Deb: the friendly layer. Wrapped (shareable week/month/year cards), Radar (what to post about next, with ready scripts),
quick answers when AI is off, and the tone switch."""
import datetime as dt
from urllib.parse import quote
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort, jsonify, Response
import config as C
import services as S
import voice
from db import q, ex

bp = Blueprint("deb", __name__)
W = lambda: g.ws["id"]


def _need():
    if g.role in (None, "client"):
        abort(403)


def festival_next(limit=1):
    t = S.today().isoformat()
    rows = q("SELECT name, date FROM key_dates WHERE workspace_id=? AND date>=? ORDER BY date LIMIT ?", (W(), t, limit))
    out = []
    for r in rows:
        try:
            days = (dt.date.fromisoformat(r["date"]) - S.today()).days
        except ValueError:
            continue
        out.append(dict(name=r["name"], date=r["date"], days=days))
    return out


def bento():
    """Small tiles for Home: today's count, streak, next post, festival countdown, the mascot's mood."""
    w, t = W(), S.today().isoformat()
    due = q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND publish_date=? AND status NOT IN ('Published','On hold')", (w, t), one=True)["c"] + \
        q("SELECT COUNT(*) c FROM tasks WHERE workspace_id=? AND status!='Done' AND due_date!='' AND due_date<=?", (w, t), one=True)["c"]
    nxt = q("SELECT title, publish_date FROM content_items WHERE workspace_id=? AND publish_date>=? AND status NOT IN ('Published','On hold') ORDER BY publish_date, id LIMIT 1", (w, t), one=True)
    fest = festival_next(1)
    return dict(due=due, nxt=nxt, fest=fest[0] if fest else None)


def week_stats(days):
    w, today = W(), S.today()
    a = (today - dt.timedelta(days=days)).isoformat()
    posted = q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status='Published' AND publish_date>=? AND publish_date<=?", (w, a, today.isoformat()), one=True)["c"]
    planned = q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND publish_date>=? AND publish_date<=?", (w, a, today.isoformat()), one=True)["c"]
    tasks = q("SELECT COUNT(*) c FROM tasks WHERE workspace_id=? AND status='Done' AND due_date>=? AND due_date<=?", (w, a, today.isoformat()), one=True)["c"]
    best = q("SELECT channel, COUNT(*) c FROM content_items WHERE workspace_id=? AND status='Published' AND publish_date>=? GROUP BY channel ORDER BY c DESC LIMIT 1", (w, a), one=True)
    active = {str(r["created_at"])[:10] for r in q("SELECT created_at FROM audit_log WHERE workspace_id=? AND user_id=? AND created_at>=?", (w, g.user["id"], a))}
    reach = q("SELECT COALESCE(SUM(CAST(value AS REAL)),0) s FROM kpis WHERE workspace_id=? AND metric='Reach' AND period>=?", (w, a), one=True)["s"]
    return dict(posted=posted, planned=planned, tasks=tasks, best=(best["channel"] if best and best["channel"] else ""), active=len(active), reach=int(reach or 0))


@bp.route("/wrapped")
def wrapped():
    _need()
    span = request.args.get("p", "week")
    days = {"week": 7, "month": 30, "year": 365}.get(span, 7)
    st = week_stats(days)
    from views import _streak_info
    try:
        streak = _streak_info()[0]
    except Exception:
        streak = 0
    pr = None
    try:
        from views import _progress
        pr = _progress()
    except Exception:
        pass
    line = ("You ate that. Keep the streak alive." if st["posted"] >= 3 else "A slow week is still a week. One post gets you moving." if st["posted"] else "Fresh start. Your first post is one tap away.")
    title = {"week": "week", "month": "month", "year": "year"}[span] if span in ("week", "month", "year") else "week"
    return render_template("wrapped.html", st=st, streak=streak, span=span, title=title, line=line, level=(pr or {}).get("level", 1), lname=(pr or {}).get("name", ""), brand=g.ws["name"])


def _when(date, today):
    n = (date - today).days
    return "Overdue" if n < 0 else "Today" if n == 0 else "Tomorrow" if n == 1 else f"In {n} days" if n < 7 else date.strftime("%a %d %b")


def due_items(days=7, limit=8):
    """What is actually due, soonest first: posts going out and open tasks. Only things that need a person, nothing already done."""
    t = S.today()
    lo, hi = (t - dt.timedelta(days=3)).isoformat(), (t + dt.timedelta(days=days)).isoformat()
    out = []
    for r in q("SELECT id, title, channel, publish_date AS d, status FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ? AND status NOT IN ('Published','On hold') ORDER BY publish_date, id LIMIT 30", (W(), lo, hi)):
        out.append(dict(kind="post", id=r["id"], title=r["title"], d=r["d"], extra=r["channel"] or "any channel", status=r["status"]))
    for r in q("SELECT id, title, due_date AS d, status, assignee FROM tasks WHERE workspace_id=? AND due_date BETWEEN ? AND ? AND status NOT IN ('Done','Cancelled') ORDER BY due_date, id LIMIT 30", (W(), lo, hi)):
        out.append(dict(kind="task", id=r["id"], title=r["title"], d=r["d"], extra=r["assignee"] or "task", status=r["status"]))
    rows = []
    for it in sorted(out, key=lambda x: (x["d"], x["kind"])):
        try:
            date = dt.date.fromisoformat(it["d"])
        except ValueError:
            continue
        label = _when(date, t)
        txt = f"{'📸' if it['kind'] == 'post' else '✅'} {it['title']} ({it['extra']}) – {label.lower() if label in ('Today', 'Tomorrow', 'Overdue') else label}, {date:%a %d %b}"
        rows.append(dict(kind=it["kind"], id=it["id"], title=it["title"], when=label, date=date.strftime("%a %d %b"), extra=it["extra"], status=it["status"], late=label == "Overdue",
                         open=url_for("m_edit", key="content_items" if it["kind"] == "post" else "tasks", rid=it["id"]), ics=url_for("deb.item_ics", kind=it["kind"], rid=it["id"]),
                         wa="https://wa.me/?text=" + quote(txt)))
    return rows[:limit]


@bp.route("/deb/ics/<kind>/<int:rid>.ics")
def item_ics(kind, rid):
    """One post or task as a calendar event, so it can be added to Google, Apple or Outlook calendar with a tap."""
    _need()
    if kind == "post":
        r = q("SELECT title, publish_date AS d, channel, copy FROM content_items WHERE id=? AND workspace_id=?", (rid, W()), one=True)
        what = (r["channel"] or "Post") if r else ""
    elif kind == "task":
        r = q("SELECT title, due_date AS d, assignee, description AS copy FROM tasks WHERE id=? AND workspace_id=?", (rid, W()), one=True)
        what = "Task"
    else:
        abort(404)
    if not r:
        abort(404)
    try:
        d0 = dt.date.fromisoformat(r["d"])
    except (ValueError, TypeError):
        abort(404)
    esc = lambda s: (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    ics = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{C.APP_NAME}//EN", "BEGIN:VEVENT", f"UID:{kind}-{rid}@{C.APP_NAME.replace(' ', '').lower()}", f"DTSTAMP:{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}",
           f"DTSTART;VALUE=DATE:{d0:%Y%m%d}", f"DTEND;VALUE=DATE:{d0 + dt.timedelta(days=1):%Y%m%d}", f"SUMMARY:{esc(what + ' - ' + (r['title'] or ''))}", f"DESCRIPTION:{esc((r['copy'] or '')[:300])}",
           "BEGIN:VALARM", "TRIGGER:-PT15H", "ACTION:DISPLAY", "DESCRIPTION:Due tomorrow", "END:VALARM", "END:VEVENT", "END:VCALENDAR"]
    return Response("\r\n".join(ics), mimetype="text/calendar", headers={"Content-Disposition": f"attachment; filename={kind}-{rid}.ics"})


@bp.route("/deb/quick")
def quick():
    """Answers that need no AI: built from your own calendar, so Ask Deb is useful even without an API key."""
    _need()
    k = request.args.get("k", "")
    t = S.today().isoformat()
    if k == "due":
        items = due_items()
        if not items:
            return jsonify(text="Nothing is due in the next 7 days. Nice. Want to plan something?", link=url_for("studio.studio"), label="Make a post")
        return jsonify(text=f"{len(items)} thing{'s' if len(items) != 1 else ''} need you, soonest first:", items=items)
    if k == "howdid":
        import learn as L
        rows = L.awaiting(W())
        if not rows:
            head = L.headline(W())
            return jsonify(text=head or "Nothing is waiting to be rated. Publish something and I'll ask in a few days.")
        items = [dict(title=r["title"], when=r["publish_date"], extra=(r["format"] or "Post"), late=False,
                      href=url_for("m_edit", key="content_items", rid=r["id"]) + "#howdid") for r in rows]
        return jsonify(text=f"{len(rows)} post{'s' if len(rows) != 1 else ''} went out and nobody has said how they did. "
                            "Three taps each, and I can tell you what works for you:", items=items)
    if k == "share":
        items = due_items()
        if not items:
            return jsonify(text="Nothing due this week, so there is nothing to share yet.")
        lines = [f"{'⚠️' if i['late'] else '📌'} {i['when']}: {i['title']} ({i['extra']})" for i in items]
        msg = f"This week at {g.ws['name'].replace(' (demo)', '')}:\n" + "\n".join(lines)
        return jsonify(text="Here is your week, ready to send:\n\n" + "\n".join(lines), links=[dict(label="📲 Share on WhatsApp", href="https://wa.me/?text=" + quote(msg))])
    if k == "sync":
        from itsdangerous import URLSafeSerializer
        import secrets
        key_ = g.ws["ics_key"] or secrets.token_hex(6)
        if not g.ws["ics_key"]:
            ex("UPDATE workspaces SET ics_key=? WHERE id=?", (key_, W()))
        feed = S.app_url() + url_for("ics_feed", token=URLSafeSerializer(C.SECRET_KEY, salt="ics").dumps([W(), key_]))
        web = feed.replace("https://", "webcal://").replace("http://", "webcal://")
        return jsonify(text="Your calendar stays in sync on its own. Add it once and every post and task with a deadline shows up in your phone calendar.", links=[
            dict(label="➕ Google Calendar", href="https://calendar.google.com/calendar/r?cid=" + quote(web, safe="")), dict(label="🍎 Apple / Outlook", href=web), dict(label="📋 Copy feed link", copy=feed)])
    if k == "today":
        p = q("SELECT id, title, channel FROM content_items WHERE workspace_id=? AND publish_date=? AND status NOT IN ('Published','On hold') ORDER BY id", (W(), t))
        if p:
            return jsonify(text="Today's post: " + "; ".join(f"{r['title']} ({r['channel'] or 'any channel'})" for r in p[:3]) + ". Open it, polish it, and post it.", link=url_for("m_edit", key="content_items", rid=p[0]["id"]), label="Open it")
        n = q("SELECT title, publish_date FROM content_items WHERE workspace_id=? AND publish_date>? AND status NOT IN ('Published','On hold') ORDER BY publish_date LIMIT 1", (W(), t), one=True)
        f = festival_next(1)
        if f:
            return jsonify(text=f"Nothing planned for today. {f[0]['name']} is in {f[0]['days']} days, so a teaser is a safe bet. Want a ready one?", link=url_for("studio.studio"), label="Make it in Create")
        return jsonify(text="Nothing planned for today. A quick “behind the scenes” story is always a win.", link=url_for("studio.studio"), label="Make one")
    if k == "coming":
        f = festival_next(3)
        return jsonify(text=("Coming up: " + ", ".join(f"{x['name']} in {x['days']} days" for x in f) + ".") if f else "No key dates ahead. Add some on the calendar.", link=url_for("ideas"), label="See ideas")
    if k == "flop":
        r = q("SELECT title, channel, format FROM content_items WHERE workspace_id=? AND status='Published' ORDER BY publish_date DESC, id DESC LIMIT 1", (W(),), one=True)
        if not r:
            return jsonify(text="No published posts yet. Post one and I can tell you what to try next.", link=url_for("studio.studio"), label="Make a post")
        return jsonify(text=f"About “{r['title']}”: most flops come down to a weak first line, too many words, or posting when your people are offline. Rewrite the hook so it names a person or a number, keep slides to 8 words, and post at 7 to 9 pm. Then compare reach.", link=url_for("studio.studio"), label="Rework it in Create")
    return jsonify(text="Ask me what to post today, what's coming up, or why a post flopped.")




@bp.route("/account/tone", methods=["POST"])
def set_tone():
    t = request.form.get("tone", "")
    if t in voice.TONES:
        ex("UPDATE users SET tone=? WHERE id=?", (t, g.user["id"]))
        flash({"chill": "Chill mode on. 😎", "normal": "Normal mode on.", "corporate": "Corporate mode on."}[t])
    return redirect(request.referrer or url_for("ws.account"))
