"""Team space: idea approvals that land on the calendar, one approvals inbox, personal chat (with images and send-later),
and page locks that a lead sets so only people they approve can open certain pages."""
import datetime as dt
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort, jsonify
import config as C
import services as S
from db import q, ex, ins
from modules import MODULES

bp = Blueprint("tm", __name__)
W = lambda: g.ws["id"]
APPROVERS = ("owner", "admin", "lead", "manager")
CHANNELS = ["Instagram", "LinkedIn", "Facebook", "X / Twitter", "YouTube", "WhatsApp", "Email", "Other"]
FORMATS = ["Post", "Carousel", "Reel", "Story", "Video", "Blog", "Email"]

# Pages a lead can lock. Core daily pages (calendar, tasks, create) are never lockable, so nobody is cut off from their own work.
LOCK_EPS = [("ep:analytics", "📈 Results and KPIs"), ("ep:ai_studio", "🤖 AI Studio"), ("ep:content_ops", "💸 Creator overview"), ("ep:moodboards", "🖼️ Mood boards"), ("ep:campaigns_all", "📣 Campaigns")]
LOCK_MODS = ("leads", "clients", "payments", "content_orders", "creators", "rate_card", "budget", "accounts", "competitors", "influencers", "brand_kit")


def lockable():
    out = list(LOCK_EPS)
    for k in LOCK_MODS:
        m = MODULES.get(k)
        if m:
            out.append(("m:" + k, f"{m.get('icon', '')} {m['title']}".strip()))
    return out


def page_key(ep, key):
    if key and ("m:" + key) in dict(lockable()):
        return "m:" + key
    k = "ep:" + (ep or "")
    return k if k in dict(LOCK_EPS) else ""


def blocked(ep, key):
    """Called on every request: the page key if this page is locked for this person (and they have no approved access), else ''."""
    if not g.get("user") or not g.get("ws") or g.role in C.TEAM_MANAGERS or g.get("support"):
        return ""
    pk = page_key(ep, key)
    if not pk or not q("SELECT 1 FROM page_locks WHERE workspace_id=? AND page_key=?", (W(), pk), one=True):
        return ""
    if q("SELECT 1 FROM page_access WHERE workspace_id=? AND page_key=? AND user_id=? AND status='granted'", (W(), pk, g.user["id"]), one=True):
        return ""
    return pk


def now_s():
    return S.now_ist().strftime("%Y-%m-%d %H:%M")


def deliver_due():
    """Scheduled messages that are now due: tell the recipient once."""
    for m in q("SELECT * FROM chat_messages WHERE workspace_id=? AND notified=0 AND send_at!='' AND send_at<=?", (W(), now_s())):
        ex("UPDATE chat_messages SET notified=1 WHERE id=?", (m["id"],))
        who = q("SELECT name,email FROM users WHERE id=?", (m["from_id"],), one=True)
        S.notify(W(), m["to_id"], "chat", f"{(who['name'] or who['email'])}: {(m['body'] or 'sent an image')[:80]}", url_for("tm.thread", uid=m["from_id"]))


def _need_member():
    if g.role in (None, "client"):
        abort(403)


# ------------------------------------------------------------ approvals inbox
@bp.route("/approvals")
def approvals():
    _need_member()
    deliver_due()
    me, mgr = g.user["id"], g.role in APPROVERS
    ideas = q("SELECT r.*, u.name AS who FROM idea_requests r LEFT JOIN users u ON u.id=r.user_id WHERE r.workspace_id=? AND r.status='pending' ORDER BY r.id", (W(),)) if mgr else []
    mine = q("SELECT * FROM idea_requests WHERE workspace_id=? AND user_id=? ORDER BY id DESC LIMIT 8", (W(), me))
    content = q("SELECT id,title,channel,publish_date,owner FROM content_items WHERE workspace_id=? AND status='Review' ORDER BY publish_date LIMIT 20", (W(),)) if mgr else []
    access = q("SELECT a.*, u.name AS who FROM page_access a LEFT JOIN users u ON u.id=a.user_id WHERE a.workspace_id=? AND a.status='pending' ORDER BY a.id", (W(),)) if g.role in C.TEAM_MANAGERS else []
    labels = dict(lockable())
    return render_template("approvals.html", ideas=ideas, mine=mine, content=content, access=access, labels=labels, mgr=mgr, channels=CHANNELS, formats=FORMATS,
                           today=S.today().isoformat(), total=len(ideas) + len(content) + len(access))


def add_to_calendar(title, channel, fmt, day, note, by):
    row = dict(workspace_id=W(), title=title[:200], status="Planned", publish_date=day, channel=channel if channel in CHANNELS else "Other", format=fmt if fmt in FORMATS else "Post", notes=note[:500])
    cid = ins("content_items", row)
    S.audit("create", f"content_items#{cid} (approved idea by {by})")
    return cid


@bp.route("/approvals/idea", methods=["POST"])
def idea_submit():
    _need_member()
    f = request.form
    title = S.clean_text(f.get("title"), 200)
    if not title:
        flash("Write the idea first.")
        return redirect(url_for("tm.approvals"))
    day = (f.get("date") or "")[:10]
    try:
        dt.date.fromisoformat(day)
    except ValueError:
        day = ""
    ch, fm, note = f.get("channel", "Other"), f.get("format", "Post"), S.clean_text(f.get("note") or f.get("pillar") or "", 300)
    if g.role in APPROVERS:      # approvers do not wait for themselves
        if day:
            add_to_calendar(title, ch, fm, day, note, g.user["name"] or "you")
            flash("Added to the calendar. 📅")
            return redirect(safe(url_for("calendar_view", d=day)))
        flash("Pick a date to put it on the calendar.")
        return redirect(safe(f.get("next") or url_for("tm.approvals")))
    rid = ins("idea_requests", dict(workspace_id=W(), user_id=g.user["id"], title=title, channel=ch, format=fm, proposed_date=day, note=note, status="pending"))
    who = g.user["name"] or g.user["email"]
    for m in S.members(W()):
        if m["role"] in APPROVERS and m["uid"] != g.user["id"]:
            S.notify(W(), m["uid"], "approval", f"{who} suggested: {title}", url_for("tm.approvals"))
    S.audit("idea_request", f"#{rid}")
    flash("Sent for approval. You will be told when it is decided. ✅")
    return redirect(safe(f.get("next") or url_for("tm.approvals")))


def safe(u):
    return u if u and u.startswith("/") and not u.startswith("//") else url_for("tm.approvals")


@bp.route("/approvals/idea/<int:rid>/decide", methods=["POST"])
def idea_decide(rid):
    if g.role not in APPROVERS:
        abort(403)
    r = q("SELECT * FROM idea_requests WHERE id=? AND workspace_id=? AND status='pending'", (rid, W()), one=True) or abort(404)
    ok = request.form.get("do") == "approve"
    day = (request.form.get("date") or r["proposed_date"] or "")[:10]
    if ok:
        try:
            dt.date.fromisoformat(day)
        except ValueError:
            flash("Pick a date, then approve.")
            return redirect(url_for("tm.approvals"))
        cid = add_to_calendar(r["title"], r["channel"], r["format"], day, r["note"], g.user["name"] or "")
        ex("UPDATE idea_requests SET status='approved', decided_by=?, content_id=?, proposed_date=? WHERE id=?", (g.user["id"], cid, day, rid))
        S.notify(W(), r["user_id"], "approved", f"Your idea was approved and is on the calendar for {day}: {r['title']}", url_for("calendar_view", d=day))
        flash("Approved and added to the calendar. 📅")
    else:
        ex("UPDATE idea_requests SET status='declined', decided_by=?, reason=? WHERE id=?", (g.user["id"], S.clean_text(request.form.get("reason"), 200), rid))
        S.notify(W(), r["user_id"], "declined", f"Your idea was not taken this time: {r['title']}", url_for("tm.approvals"))
        flash("Declined. They have been told.")
    return redirect(url_for("tm.approvals"))


# ------------------------------------------------------------ page locks
@bp.route("/team/access", methods=["GET", "POST"])
def access():
    if g.role not in C.TEAM_MANAGERS:
        abort(403)
    allk = [k for k, _ in lockable()]
    if request.method == "POST":
        want = {k for k in request.form.getlist("lock") if k in allk}
        ex("DELETE FROM page_locks WHERE workspace_id=?", (W(),))
        for k in want:
            ins("page_locks", dict(workspace_id=W(), page_key=k))
        S.audit("page_locks", ",".join(sorted(want)))
        flash("Saved. Locked pages now ask for your approval." if want else "Saved. Nothing is locked.")
        return redirect(url_for("tm.access"))
    locked = {r["page_key"] for r in q("SELECT page_key FROM page_locks WHERE workspace_id=?", (W(),))}
    grants = q("SELECT a.*, u.name AS who, u.email FROM page_access a JOIN users u ON u.id=a.user_id WHERE a.workspace_id=? AND a.status='granted' ORDER BY a.id", (W(),))
    return render_template("access.html", pages=lockable(), locked=locked, grants=grants, labels=dict(lockable()))


@bp.route("/team/access/request", methods=["POST"])
def access_request():
    _need_member()
    pk = request.form.get("page", "")
    if pk not in dict(lockable()):
        abort(400)
    if not q("SELECT 1 FROM page_access WHERE workspace_id=? AND page_key=? AND user_id=? AND status IN ('pending','granted')", (W(), pk, g.user["id"]), one=True):
        ins("page_access", dict(workspace_id=W(), page_key=pk, user_id=g.user["id"], status="pending"))
        who = g.user["name"] or g.user["email"]
        for m in S.members(W()):
            if m["role"] in C.TEAM_MANAGERS and m["uid"] != g.user["id"]:
                S.notify(W(), m["uid"], "approval", f"{who} asks to open {dict(lockable())[pk]}", url_for("tm.approvals"))
    flash("Asked. You will be told when a lead decides.")
    return redirect(request.referrer or url_for("dashboard"))


@bp.route("/team/access/<int:aid>/decide", methods=["POST"])
def access_decide(aid):
    if g.role not in C.TEAM_MANAGERS:
        abort(403)
    a = q("SELECT * FROM page_access WHERE id=? AND workspace_id=?", (aid, W()), one=True) or abort(404)
    do = request.form.get("do")
    st = "granted" if do == "grant" else "denied"
    if do == "revoke":
        ex("DELETE FROM page_access WHERE id=?", (aid,))
        flash("Access removed.")
    else:
        ex("UPDATE page_access SET status=?, decided_by=? WHERE id=?", (st, g.user["id"], aid))
        S.notify(W(), a["user_id"], "approved" if st == "granted" else "declined", f"{dict(lockable()).get(a['page_key'], 'That page')}: access {st}", url_for("dashboard"))
        flash("Access granted. ✅" if st == "granted" else "Access declined.")
    return redirect(request.referrer or url_for("tm.approvals"))


# ------------------------------------------------------------ chat: channels (group chats) and direct messages
import os, re, uuid
from markupsafe import Markup, escape
import config as _C
REACTS = ["👍", "❤️", "😂", "🔥", "🎉"]
FILE_OK = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv", "txt", "zip", "mp3", "m4a", "ogg", "wav", "webm", "mp4", "mov"}
AUDIO = {"mp3", "m4a", "ogg", "wav", "webm"}
DEFAULT_CHANNELS = [("general", "Everyone, all the time"), ("ideas", "Drop ideas here. Approved ones go on the calendar"), ("wins", "Posted it? Brag here 🎉")]


@bp.app_template_filter("mention")
def _mention(t):
    return Markup(re.sub(r"(@\w+)", r"<b class='mn'>\1</b>", str(escape(t or "")))).replace("\n", Markup("<br>"))


@bp.app_template_filter("hhmm")
def _hhmm(v):
    """Stored times are UTC; people read them in India time."""
    try:
        t = dt.datetime.strptime(str(v)[:16], "%Y-%m-%d %H:%M") + dt.timedelta(hours=5, minutes=30)
        return t.strftime("%H:%M")
    except ValueError:
        return str(v)[11:16]


@bp.app_template_filter("is_audio")
def _is_audio(name):
    return (name or "").rsplit(".", 1)[-1].lower() in AUDIO


def _people():
    return [m for m in S.members(W()) if m["uid"] != g.user["id"]]


def ensure_channels():
    if not q("SELECT 1 FROM channels WHERE workspace_id=? LIMIT 1", (W(),), one=True):
        for n, t in DEFAULT_CHANNELS:
            ins("channels", dict(workspace_id=W(), name=n, topic=t, private=0, created_by=g.user["id"]))


def my_channels():
    ensure_channels()
    me = g.user["id"]
    return q("SELECT c.* FROM channels c WHERE c.workspace_id=? AND (c.private=0 OR c.created_by=? OR EXISTS (SELECT 1 FROM channel_members m WHERE m.channel_id=c.id AND m.user_id=?)) ORDER BY c.id", (W(), me, me))


def chan_or_404(cid):
    return next((c for c in my_channels() if c["id"] == cid), None) or abort(404)


def _due(alias=""):
    return f"({alias}send_at='' OR {alias}send_at<=? OR {alias}from_id=?)"


def chan_unread(cid):
    last = q("SELECT last_id FROM chat_reads WHERE user_id=? AND channel_id=?", (g.user["id"], cid), one=True)
    return q(f"SELECT COUNT(*) c FROM chat_messages WHERE workspace_id=? AND channel_id=? AND id>? AND from_id!=? AND (send_at='' OR send_at<=?)", (W(), cid, last["last_id"] if last else 0, g.user["id"], now_s()), one=True)["c"]


def unread_total():
    n = q("SELECT COUNT(*) c FROM chat_messages WHERE workspace_id=? AND channel_id=0 AND to_id=? AND is_read=0 AND (send_at='' OR send_at<=?)", (W(), g.user["id"], now_s()), one=True)["c"]
    try:
        n += sum(chan_unread(c["id"]) for c in my_channels())
    except Exception:
        pass
    return n


def _sidebar():
    me, now = g.user["id"], now_s()
    chans = [dict(c=c, unread=chan_unread(c["id"])) for c in my_channels()]
    dms = []
    for m in _people():
        last = q("SELECT * FROM chat_messages WHERE workspace_id=? AND channel_id=0 AND ((from_id=? AND to_id=?) OR (from_id=? AND to_id=? AND (send_at='' OR send_at<=?))) ORDER BY id DESC LIMIT 1", (W(), me, m["uid"], m["uid"], me, now), one=True)
        un = q("SELECT COUNT(*) c FROM chat_messages WHERE workspace_id=? AND channel_id=0 AND from_id=? AND to_id=? AND is_read=0 AND (send_at='' OR send_at<=?)", (W(), m["uid"], me, now), one=True)["c"]
        dms.append(dict(m=m, last=last, unread=un))
    dms.sort(key=lambda r: -(r["last"]["id"] if r["last"] else 0))
    return chans, dms


def _decorate(msgs):
    """Everything a message row needs: sender names, reactions, quoted replies and shared cards."""
    ids = [m["id"] for m in msgs]
    names = {m["uid"]: (m["name"] or m["email"]) for m in S.members(W(), clients=True)}
    reacts = {}
    if ids:
        for r in q("SELECT message_id, emoji, user_id FROM chat_reacts WHERE message_id IN (" + ",".join("?" * len(ids)) + ")", tuple(ids)):
            reacts.setdefault(r["message_id"], {}).setdefault(r["emoji"], []).append(r["user_id"])
    quotes, refs = {}, {}
    for m in msgs:
        if m["reply_to"]:
            r = q("SELECT id, from_id, body, file_name FROM chat_messages WHERE id=? AND workspace_id=?", (m["reply_to"], W()), one=True)
            if r:
                quotes[m["id"]] = r
        if m["ref"] and ":" in m["ref"]:
            kind, _, rid = m["ref"].partition(":")
            if rid.isdigit():
                if kind == "content_items":
                    r = q("SELECT title, status, publish_date FROM content_items WHERE id=? AND workspace_id=?", (int(rid), W()), one=True)
                    if r:
                        refs[m["id"]] = ("📅 " + (r["title"] or "Post"), f"{r['status']} · {r['publish_date'] or 'no date'}", url_for("m_edit", key="content_items", rid=int(rid)))
                elif kind == "tasks":
                    r = q("SELECT title, status, due_date FROM tasks WHERE id=? AND workspace_id=?", (int(rid), W()), one=True)
                    if r:
                        refs[m["id"]] = ("✅ " + (r["title"] or "Task"), f"{r['status']} · {r['due_date'] or 'no date'}", url_for("m_edit", key="tasks", rid=int(rid)))
    return dict(names=names, reacts=reacts, quotes=quotes, refs=refs, REACTS=REACTS, now=now_s(), me=g.user["id"])


def _render_thread(title, kind, ident, msgs, extra):
    chans, dms = _sidebar()
    ctx = _decorate(msgs)
    ctx.update(extra)
    ctx["people"] = _people()
    ctx["member_names"] = [m["name"] or m["email"] for m in S.members(W())]
    if request.args.get("frag"):
        return render_template("chat_msgs.html", msgs=msgs, **ctx)
    return render_template("chat_thread.html", title=title, kind=kind, ident=ident, msgs=msgs, chans=chans, dms=dms, **ctx)


@bp.route("/chat")
def chat():
    _need_member()
    deliver_due()
    chans, dms = _sidebar()
    return render_template("chat.html", chans=chans, dms=dms, people=_people())


@bp.route("/chat/c/<int:cid>")
def channel(cid):
    _need_member()
    c = chan_or_404(cid)
    deliver_due()
    msgs = q("SELECT * FROM chat_messages WHERE workspace_id=? AND channel_id=? AND (send_at='' OR send_at<=? OR from_id=?) ORDER BY id DESC LIMIT 100", (W(), cid, now_s(), g.user["id"]))[::-1]
    top = msgs[-1]["id"] if msgs else 0
    ex("DELETE FROM chat_reads WHERE user_id=? AND channel_id=?", (g.user["id"], cid))
    ins("chat_reads", dict(user_id=g.user["id"], channel_id=cid, last_id=top))
    pinned = q("SELECT * FROM chat_messages WHERE workspace_id=? AND channel_id=? AND pinned=1 ORDER BY id DESC LIMIT 3", (W(), cid))
    return _render_thread("#" + c["name"], "c", cid, msgs, dict(topic=c["topic"], pinned=pinned, other=None, members=S.members(W())))


@bp.route("/chat/<int:uid>")
def thread(uid):
    _need_member()
    other = next((m for m in _people() if m["uid"] == uid), None) or abort(404)
    deliver_due()
    me = g.user["id"]
    ex("UPDATE chat_messages SET is_read=1 WHERE workspace_id=? AND channel_id=0 AND from_id=? AND to_id=? AND (send_at='' OR send_at<=?)", (W(), uid, me, now_s()))
    msgs = q("SELECT * FROM chat_messages WHERE workspace_id=? AND channel_id=0 AND ((from_id=? AND to_id=?) OR (from_id=? AND to_id=? AND (send_at='' OR send_at<=?))) ORDER BY id DESC LIMIT 100", (W(), me, uid, uid, me, now_s()))[::-1]
    return _render_thread(other["name"] or other["email"], "u", uid, msgs, dict(topic=other["role"], pinned=[], other=other, members=S.members(W())))


def _save_file(f):
    """(url, display name, is_image). Images are sniffed; documents and audio are allowed by a short safe list of extensions."""
    data = f.read(10 * 1024 * 1024 + 1)
    if not data or len(data) > 10 * 1024 * 1024:
        return None
    ext = S.sniff_image(data)
    if ext:
        return S.store_file(W(), ext, data), (f.filename or "picture")[:80], True
    e = (f.filename or "").rsplit(".", 1)[-1].lower()
    if e not in FILE_OK or _C.S3_BUCKET:
        return None
    d = os.path.join(_C.UPLOAD_DIR, str(W()))
    os.makedirs(d, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{e}"
    with open(os.path.join(d, name), "wb") as fh:
        fh.write(data)
    return f"/media/{W()}/{name}", (f.filename or name)[:80], False


def _mentions(body, channel_name):
    if "@" not in (body or ""):
        return
    tags = {t.lower() for t in re.findall(r"@(\w+)", body)}
    who = g.user["name"] or g.user["email"]
    for m in S.members(W()):
        first = ((m["name"] or m["email"]).split() or [""])[0].lower()
        if m["uid"] != g.user["id"] and (first in tags or (m["name"] or "").replace(" ", "").lower() in tags or "everyone" in tags or "all" in tags):
            S.notify(W(), m["uid"], "chat", f"{who} mentioned you in {channel_name}: {body[:70]}", url_for("tm.chat"))


def _post(channel_id, to_id, back):
    f = request.form
    body = S.clean_text(f.get("body"), 2000)
    img = fname = ""
    up = request.files.get("file")
    if up and up.filename:
        r = _save_file(up)
        if not r:
            flash("That file isn't allowed. Pictures, PDFs, Office files, audio and short videos up to 10 MB work.")
            return redirect(back)
        img, fname, _ = r
    if not body and not img:
        return redirect(back)
    when = (f.get("send_at") or "").replace("T", " ")[:16]
    later = bool(when) and when > now_s()
    rt = f.get("reply_to", "")
    rt = int(rt) if rt.isdigit() and q("SELECT 1 FROM chat_messages WHERE id=? AND workspace_id=?", (int(rt), W()), one=True) else 0
    ref = f.get("ref", "")[:40] if re.match(r"^(content_items|tasks):\d+$", f.get("ref", "")) else ""
    ins("chat_messages", dict(workspace_id=W(), from_id=g.user["id"], to_id=to_id, channel_id=channel_id, body=body, image=img if (img and not fname.rsplit('.', 1)[-1].lower() in FILE_OK) else "", file=img if (img and fname.rsplit('.', 1)[-1].lower() in FILE_OK) else "", file_name=fname,
                              send_at=when if later else "", notified=0 if later else 1, reply_to=rt, ref=ref))
    if later:
        flash(f"Scheduled for {when.replace(' ', ' at ')}. ⏰")
    elif to_id:
        S.notify(W(), to_id, "chat", f"{g.user['name'] or g.user['email']}: {(body or 'sent a file')[:80]}", url_for("tm.thread", uid=g.user["id"]))
    else:
        _mentions(body, "#" + (q("SELECT name FROM channels WHERE id=?", (channel_id,), one=True) or {"name": "chat"})["name"])
    if request.headers.get("X-Requested-With") == "fetch":
        return ("", 204)
    return redirect(back)


@bp.route("/chat/c/<int:cid>/send", methods=["POST"])
def send_channel(cid):
    _need_member()
    chan_or_404(cid)
    return _post(cid, 0, url_for("tm.channel", cid=cid))


@bp.route("/chat/<int:uid>/send", methods=["POST"])
def send(uid):
    _need_member()
    next((m for m in _people() if m["uid"] == uid), None) or abort(404)
    return _post(0, uid, url_for("tm.thread", uid=uid))


@bp.route("/chat/new", methods=["POST"])
def new_channel():
    _need_member()
    if g.role == "viewer":
        abort(403)
    name = re.sub(r"[^a-z0-9\-]+", "-", (request.form.get("name") or "").lower().strip()).strip("-")[:30]
    if not name:
        flash("Give the channel a short name.")
        return redirect(url_for("tm.chat"))
    ensure_channels()
    private = 1 if request.form.get("private") else 0
    ex_ = q("SELECT id FROM channels WHERE workspace_id=? AND name=?", (W(), name), one=True)
    if ex_:
        return redirect(url_for("tm.channel", cid=ex_["id"]))
    cid = ins("channels", dict(workspace_id=W(), name=name, topic=S.clean_text(request.form.get("topic"), 100), private=private, created_by=g.user["id"]))
    if private:
        valid = {str(m["uid"]) for m in S.members(W())}
        for u in request.form.getlist("member"):
            if u in valid:
                ins("channel_members", dict(channel_id=cid, user_id=int(u)))
                S.notify(W(), int(u), "chat", f"{g.user['name'] or g.user['email']} added you to #{name}", url_for("tm.channel", cid=cid))
    return redirect(url_for("tm.channel", cid=cid))


def _msg_or_404(mid):
    m = q("SELECT * FROM chat_messages WHERE id=? AND workspace_id=?", (mid, W()), one=True) or abort(404)
    if m["channel_id"]:
        chan_or_404(m["channel_id"])
    elif g.user["id"] not in (m["from_id"], m["to_id"]):
        abort(404)
    return m


def _back(m):
    return url_for("tm.channel", cid=m["channel_id"]) if m["channel_id"] else url_for("tm.thread", uid=m["to_id"] if m["from_id"] == g.user["id"] else m["from_id"])


@bp.route("/chat/msg/<int:mid>/react", methods=["POST"])
def react(mid):
    _need_member()
    m = _msg_or_404(mid)
    e = request.form.get("emoji", "")
    if e not in REACTS:
        abort(400)
    if q("SELECT 1 FROM chat_reacts WHERE message_id=? AND user_id=? AND emoji=?", (mid, g.user["id"], e), one=True):
        ex("DELETE FROM chat_reacts WHERE message_id=? AND user_id=? AND emoji=?", (mid, g.user["id"], e))
    else:
        ins("chat_reacts", dict(message_id=mid, user_id=g.user["id"], emoji=e))
    return ("", 204) if request.headers.get("X-Requested-With") == "fetch" else redirect(_back(m))


@bp.route("/chat/msg/<int:mid>/pin", methods=["POST"])
def pin(mid):
    m = _msg_or_404(mid)
    if g.role not in APPROVERS or not m["channel_id"]:
        abort(403)
    ex("UPDATE chat_messages SET pinned=? WHERE id=?", (0 if m["pinned"] else 1, mid))
    return redirect(_back(m))


@bp.route("/chat/msg/<int:mid>/delete", methods=["POST"])
def delete_msg(mid):
    m = _msg_or_404(mid)
    if m["from_id"] != g.user["id"] and g.role not in C.TEAM_MANAGERS:
        abort(403)
    ex("DELETE FROM chat_reacts WHERE message_id=?", (mid,))
    ex("DELETE FROM chat_messages WHERE id=?", (mid,))
    return redirect(_back(m))


@bp.route("/chat/msg/<int:mid>/cancel", methods=["POST"])
def cancel(mid):
    m = q("SELECT * FROM chat_messages WHERE id=? AND workspace_id=? AND from_id=? AND send_at>?", (mid, W(), g.user["id"], now_s()), one=True) or abort(404)
    ex("DELETE FROM chat_messages WHERE id=?", (mid,))
    flash("Scheduled message cancelled.")
    return redirect(_back(m))


@bp.route("/chat/share", methods=["POST"])
def share():
    """Drop a post or task into a channel as a card, so nobody has to copy it into a WhatsApp group."""
    _need_member()
    ref = request.form.get("ref", "")
    if not re.match(r"^(content_items|tasks):\d+$", ref):
        abort(400)
    cid = int(request.form.get("channel") or 0) or (my_channels()[0]["id"])
    chan_or_404(cid)
    ins("chat_messages", dict(workspace_id=W(), from_id=g.user["id"], to_id=0, channel_id=cid, body=S.clean_text(request.form.get("body"), 300) or "Take a look 👀", ref=ref, notified=1))
    flash("Shared in chat. 💬")
    return redirect(request.referrer or url_for("tm.channel", cid=cid))
