"""Create studio (posts, carousels, reels) and Promo Ideas.

The designing and the video recording happen in the user's browser (static/studio.js), so this module stays
small: it writes the storyboard (AI when it is switched on, a built-in template when it is not, so the demo
and free users always get something), saves the result to the calendar, and suggests promotions from the
workspace's own key dates, industry and live-news terms."""
import json, re, datetime as dt
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, g, abort
import config as C
import services as S
import industries as IND
from db import q, ex, ins

bp = Blueprint("studio", __name__)
W = lambda: g.ws["id"]
KINDS = ("post", "carousel", "reel", "story")
FORMAT_OF = {"post": "Post", "carousel": "Carousel", "reel": "Reel / Short", "story": "Story"}
LAYOUTS = ("cover", "step", "tip", "quote", "list", "offer", "cta")
SYSTEM = ("You are a senior Indian social-media creative director. Return ONLY valid JSON, no prose, no code fences. "
          "Write for the brand's real audience in plain, specific words; never invent prices, discounts, reviews or statistics the person did not give you.")


def _is_demo():
    return (g.user["email"] or "").endswith("@demo.debut.invalid")


def _trim(s, n):
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


# ---------------------------------------------------------------- the storyboard
def fallback_board(goal, kind, offer, ind, brand_name):
    """A sensible structure with no AI: the hook, three points to fill in, the offer and a call to action.
    The points are prompts, not invented claims, so nothing untrue ends up on a post by accident."""
    goal = _trim(goal, 120) or f"Why {brand_name} is worth a look"
    offer = _trim(offer, 80)
    slides = [dict(layout="cover", headline=goal, sub=offer)]
    if kind in ("carousel", "reel", "story"):
        for n, (h, sub) in enumerate([("Why now", "Say why this matters this week"), ("What you get", "Name the one thing people will love most"), ("How it works", "Tell them the simple steps")], 1):
            slides.append(dict(layout="step", num=n, headline=h, sub=sub))
    if offer:
        slides.append(dict(layout="offer", headline=offer, sub="For a limited time"))
    slides.append(dict(layout="cta", headline="Ready when you are", sub=f"Message {brand_name} to order or book"))
    if kind == "post":
        slides = [slides[0], slides[-1]]
    caption = f"{goal}.\n\n" + (f"{offer}. " if offer else "") + "Save this so you can come back to it, and tell us what you think in the comments."
    return dict(slides=slides[:8], caption=caption[:900], hashtags=_default_tags(ind), cta="Message us", source="template")


def _default_tags(ind):
    base = re.sub(r"[^a-z0-9]+", "", (ind.get("label") or "").split("/")[0].split("(")[0].lower())
    base = "business" if base in ("", "general", "other") else base
    return [f"#{base}", "#india", "#smallbusiness", "#madeinindia", "#newlaunch"]


def _clean_board(raw, kind):
    slides = []
    for s in (raw.get("slides") or [])[:10]:
        if not isinstance(s, dict):
            continue
        lay = s.get("layout") if s.get("layout") in LAYOUTS else "step"
        item = dict(layout=lay, headline=_trim(s.get("headline"), 90), sub=_trim(s.get("sub"), 180))
        if s.get("num") is not None:
            try:
                item["num"] = int(s["num"])
            except (TypeError, ValueError):
                pass
        if isinstance(s.get("items"), list):
            item["items"] = [_trim(x, 70) for x in s["items"][:5] if x]
        if item["headline"]:
            slides.append(item)
    if not slides:
        return None
    tags = [("#" + re.sub(r"[^A-Za-z0-9_]", "", str(t))) for t in (raw.get("hashtags") or [])[:8] if str(t).strip("# ")]
    return dict(slides=slides, caption=_trim(raw.get("caption"), 1800).replace("\\n", "\n") or slides[0]["headline"], hashtags=tags[:8], cta=_trim(raw.get("cta"), 60), source="ai")


@bp.route("/studio")
def studio():
    ind = IND.get(g.ws["industry"])
    brand = S.brand_shades(g.ws)
    item = None
    rid = request.args.get("item", type=int)
    if rid:
        item = q("SELECT * FROM content_items WHERE id=? AND workspace_id=?", (rid, W()), one=True)
    kd = [dict(name=r["name"], date=r["date"]) for r in q("SELECT name, date FROM key_dates WHERE workspace_id=? AND date>=? ORDER BY date LIMIT 40", (W(), (S.today() - dt.timedelta(days=3)).isoformat()))]
    saved = {}
    if item and item["studio"]:
        try:
            saved = json.loads(item["studio"])
        except ValueError:
            saved = {}
    cfg = dict(brand=g.ws["name"].replace(" (demo)", ""), pri=(brand or {}).get("pri") or g.ws["brand_color"] or "#6a3df0", sec=g.ws["secondary_color"] or "#ff4f9a",
               logo=g.ws["logo_url"] or "", today=S.today().isoformat(), kd=kd, saved=saved, rid=item["id"] if item else 0, title=item["title"] if item else "",
               channel=item["channel"] if item else "", date=item["publish_date"] if item else "", caption=item["copy"] if item else "", demo=_is_demo(),
               goal=_trim(request.args.get("goal"), 140), offer=_trim(request.args.get("offer"), 80), kind=request.args.get("kind") if request.args.get("kind") in KINDS else "carousel",
               post=bool(request.args.get("post")) and bool(item), status=item["status"] if item else "", hashtags=item["hashtags"] if item else "", ideas=[c["title"] for c in suggestions(W(), g.ws["industry"], S.today())[:3]], canwrite=g.role not in ("viewer", "client"), ai=bool(C.ANTHROPIC_API_KEY) and not _is_demo())
    import modules as MOD
    return render_template("studio.html", cfg=cfg, ind=ind, kinds=KINDS, chans=MOD.CHANNELS)


@bp.route("/studio/draft", methods=["POST"])
def draft():
    d = S.jbody()
    kind = d.get("kind") if d.get("kind") in KINDS else "carousel"
    goal, offer = _trim(d.get("goal"), 200), _trim(d.get("offer"), 120)
    if not goal:
        return jsonify(error="Say what this is for first, for example: Diwali gift box, 20% off till Sunday."), 400
    ind = IND.get(g.ws["industry"])
    brand = g.ws["name"].replace(" (demo)", "")
    out = None
    note = ""
    if C.ANTHROPIC_API_KEY and not _is_demo() and d.get("ai", True):
        import views
        cost = C.AI_COST.get("studio", 2)
        err, used, limit = views.ai_guard(cost)
        if err:
            note = "AI credits or limits stopped the smart draft, so this is the built-in template."
        else:
            voice, lang = (g.ws["ai_voice"] or ""), (g.ws["ai_lang"] or "English")
            n = {"post": "1-2", "carousel": "5-7", "reel": "5-6", "story": "3-4"}[kind]
            prompt = (f"Brand: {brand}. Industry: {ind['label']}. Today (IST): {S.today().isoformat()}. Channel: {_trim(d.get('channel'), 40) or 'Instagram'}. Format: {kind}.\n"
                      f"Brand voice: {voice or 'friendly and clear'}. Write in: {lang}.\nGoal: {goal}\nOffer (use exactly, do not invent numbers): {offer or 'none'}\n"
                      f"Return JSON: {{\"slides\":[{{\"layout\":\"cover|step|tip|quote|list|offer|cta\",\"headline\":\"max 8 words\",\"sub\":\"max 20 words\",\"num\":1}}],"
                      f"\"caption\":\"hook in the first 120 characters, then value, then a clear ask\",\"hashtags\":[\"max 5\"],\"cta\":\"short\"}}. Give {n} slides, first is a cover, last is a cta.")
            try:
                import views as V
                text, _ = V.claude_call(SYSTEM, prompt, 2500)
                m = re.search(r"\{.*\}", text, re.S)
                out = _clean_board(json.loads(m.group(0)), kind) if m else None
                if out:
                    ins("ai_usage", dict(workspace_id=W(), user_id=g.user["id"], task="studio", credits=cost, month=S.month_key()))
            except Exception:
                out = None
            if not out:
                note = "The smart draft did not come back clean, so this is the built-in template. No credits were used."
    if not out:
        out = fallback_board(goal, kind, offer, ind, brand)
    out["note"] = note
    return jsonify(out)


@bp.route("/studio/save", methods=["POST"])
def save():
    d = S.jbody()
    if g.role in ("viewer", "client"):
        abort(403)
    title = _trim(d.get("title"), 140)
    if not title:
        return jsonify(error="Give it a title first."), 400
    chan = d.get("channel") if d.get("channel") in __import__("modules").CHANNELS else "Instagram"
    kind = d.get("kind") if d.get("kind") in KINDS else "post"
    date = d.get("date") or ""
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        date = (S.today() + dt.timedelta(days=2)).isoformat()
    board = d.get("board") if isinstance(d.get("board"), dict) else {}
    board = dict(slides=(board.get("slides") or [])[:12], theme=_trim(board.get("theme"), 20), size=_trim(board.get("size"), 12), kind=kind)
    blob = json.dumps(board)
    if len(blob) > 700000:
        return jsonify(error="That is a lot of photos. Remove one or two and save again."), 400
    thumb = str(d.get("thumb") or "")
    thumb = thumb if thumb.startswith("data:image/jpeg;base64,") and len(thumb) < 30000 else ""
    tags = " ".join(_trim(t, 30) for t in (d.get("hashtags") or [])[:8])
    rec = dict(title=title, channel=chan, format=FORMAT_OF[kind], publish_date=date, copy=str(d.get("caption") or "")[:2200],
               cta=_trim(d.get("cta"), 80), hashtags=tags, studio=blob, thumb=thumb, campaign=_trim(d.get("campaign"), 100))
    rid = int(d.get("rid") or 0)
    if rid and q("SELECT id FROM content_items WHERE id=? AND workspace_id=?", (rid, W()), one=True):
        ex("UPDATE content_items SET title=?, channel=?, format=?, publish_date=?, copy=?, cta=?, hashtags=?, studio=?, thumb=? WHERE id=? AND workspace_id=?",
           (rec["title"], rec["channel"], rec["format"], rec["publish_date"], rec["copy"], rec["cta"], rec["hashtags"], rec["studio"], rec["thumb"], rid, W()))
    else:
        rid = ins("content_items", dict(workspace_id=W(), status="Planned", **rec))
    S.audit("studio_save", f"{kind} {rid}")
    return jsonify(ok=True, id=rid, url=url_for("calendar_view"))


# ---------------------------------------------------------------- promotions
GROUP = {"hospitality": "food", "retail": "food", "d2c": "product", "fmcg": "product", "fashion": "product", "b2b": "b2b", "saas": "b2b", "startup": "b2b", "fintech": "b2b",
         "agency": "b2b", "realestate": "service", "education": "service", "healthcare": "service", "personal_brand": "creator"}
# promo type: (name, offer line, [(channel, what to do)], effort, expected result)
PROMOS = {
    "food": [("Festival combo", "Festival combo meal or thali at a bundle price", [("Instagram", "Reel of the combo being plated"), ("WhatsApp", "Broadcast to past customers with the combo and a reply-to-order number"), ("Other", "Update Zomato/Swiggy menu, banner and festival hours"), ("Other", "Google Business offer post and holiday hours")], "Medium", "Orders on the festival week"),
             ("Pre-book table", "Early-bird pre-booking with a free dessert or drink", [("Instagram", "Story countdown with a booking link"), ("WhatsApp", "Broadcast with a booking number"), ("Other", "Google Business event post")], "Low", "Pre-bookings")],
    "product": [("Festival gift box", "Gift box or bundle with an early-bird price and a last-order date", [("Instagram", "Reel unboxing the gift box"), ("Email", "Early access to past buyers"), ("WhatsApp", "Restock and last-day-to-order alerts"), ("Paid Social", "Retarget visitors with the bundle")], "Medium", "Bundle orders and average order value"),
                ("Sale countdown", "Time-boxed sale with a visible countdown", [("Instagram", "3-day countdown stories"), ("Email", "Sale-live email with the best three items"), ("Other", "Marketplace listing banner and coupon")], "Medium", "Sales in the sale window")],
    "b2b": [("Year-end offer", "Audit, trial extension or onboarding help before the date", [("LinkedIn", "Founder post with one real lesson and the offer"), ("Email", "Three-email sequence to warm leads"), ("Events / Webinar", "30-minute live walkthrough")], "Medium", "Demo requests"),
            ("Case study push", "Share one customer result and invite similar companies", [("LinkedIn", "Document carousel of the case study"), ("Email", "Send to leads in the same industry")], "Low", "Qualified replies")],
    "service": [("Open day / site visit", "Open day, site visit or free consult on a set date", [("Instagram", "Walkthrough reel"), ("WhatsApp", "Invite to enquiries and past leads"), ("Facebook", "Event page with a lead form")], "Medium", "Booked visits or consults"),
                ("Limited-seat offer", "Early-bird price or free first session for the first few sign-ups", [("Instagram", "Carousel of what is included"), ("WhatsApp", "Reminder to people who enquired"), ("Email", "Deadline email")], "Low", "Sign-ups before the date")],
    "creator": [("Themed series", "A 5-day series tied to the date, ending with your offer or newsletter", [("Instagram", "Daily reel or carousel"), ("LinkedIn", "Founder-style story post"), ("Email", "Newsletter recap with one link")], "Medium", "Followers and email sign-ups"),
                ("Giveaway", "Giveaway where people save and share to enter", [("Instagram", "Giveaway post and story reminders"), ("WhatsApp", "Broadcast to your community")], "Low", "Reach and new followers")],
    "general": [("Seasonal offer", "A simple offer with a clear last date", [("Instagram", "Post and story countdown"), ("WhatsApp", "Broadcast to past customers"), ("Email", "Offer email")], "Low", "Orders in the window")],
}
EVERGREEN = [("Customer stories", "Share three real customer stories (with permission)", [("Instagram", "Carousel of customer quotes"), ("WhatsApp", "Ask happy customers for a line")], "Low", "Trust and replies"),
             ("Refer a friend", "Both sides get a small reward when a friend buys", [("WhatsApp", "Broadcast with a referral message"), ("Instagram", "Story explaining how it works"), ("Email", "Ask your best customers")], "Medium", "New customers from referrals")]


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def suggestions(wid, ind_key, today):
    ind = IND.get(ind_key)
    lib = PROMOS.get(GROUP.get(ind_key, "general"), PROMOS["general"])
    out = []
    kds = q("SELECT name, date, kind FROM key_dates WHERE workspace_id=? AND date BETWEEN ? AND ? ORDER BY date LIMIT 12", (wid, today.isoformat(), (today + dt.timedelta(days=75)).isoformat()))
    for n, r in enumerate(kds[:6]):
        try:
            when = dt.date.fromisoformat(r["date"])
        except ValueError:
            continue
        days = (when - today).days
        base = re.sub(r"\s*\(.*?\)", "", r["name"]).strip()
        p = lib[n % len(lib)]
        lead = 14 if p[3] == "Medium" else 7
        if days < 3:
            continue
        out.append(dict(id=_slug(f"{base}-{r['date']}-{p[0]}"), title=f"{base}: {p[0].lower()}", event=base, date=r["date"], days=days, why=f"{base} is in {days} day{'s' if days != 1 else ''}" + ("; start now to be ready" if days <= lead else ""),
                        offer=p[1], channels=[dict(channel=c, do=w) for c, w in p[2]], effort=p[3], expect=p[4], lead=min(lead, days), kind=r["kind"] or "", trend=False))
    pulse = S.latest_pulse(wid)
    terms = [t[0] for t in (pulse or {}).get("terms", [])[:3]] if pulse else []
    for t in terms[:2]:
        out.append(dict(id=_slug(f"trend-{t}"), title=f"Join the conversation: {t}", event=t, date=(today + dt.timedelta(days=3)).isoformat(), days=3, why=f"“{t}” is showing up in your live news and trends",
                        offer=f"A quick take, tip or reaction on {t} that links back to what you sell", channels=[dict(channel="Instagram", do=f"Reel or carousel with your take on {t}"), dict(channel="LinkedIn", do="A short opinion post")],
                        effort="Low", expect="Reach from a topic people are already searching", lead=3, kind="Trend", trend=True))
    for p in EVERGREEN:
        out.append(dict(id=_slug(f"always-{p[0]}"), title=p[0], event=p[0], date=(today + dt.timedelta(days=10)).isoformat(), days=10, why="Works any week, no date needed", offer=p[1],
                        channels=[dict(channel=c, do=w) for c, w in p[2]], effort=p[3], expect=p[4], lead=7, kind="Evergreen", trend=False))
    return out


@bp.route("/promos")
def promos():
    today = S.today()
    items = suggestions(W(), g.ws["industry"], today)
    return render_template("promos.html", items=items, ind=IND.get(g.ws["industry"]), today=today.isoformat(), canwrite=g.role not in ("viewer", "client"))


@bp.route("/promos/plan", methods=["POST"])
def promo_plan():
    if g.role in ("viewer", "client"):
        abort(403)
    pid = request.form.get("id", "")
    today = S.today()
    card = next((c for c in suggestions(W(), g.ws["industry"], today) if c["id"] == pid), None)
    if not card:
        flash("That idea is out of date. Here is the latest list.")
        return redirect(url_for("studio.promos"))
    name = f"{card['title']} ({card['date'][5:]})"[:120]
    if q("SELECT id FROM campaigns WHERE workspace_id=? AND name=?", (W(), name), one=True):
        flash("This plan already exists. Find it under Campaigns.")
        return redirect(url_for("studio.promos"))
    end = dt.date.fromisoformat(card["date"])
    start = max(today, end - dt.timedelta(days=card["lead"]))
    ins("campaigns", dict(workspace_id=W(), name=name, objective="Sales" if not card["trend"] else "Awareness", channel=card["channels"][0]["channel"] if card["channels"][0]["channel"] in __import__("modules").CHANNELS else "Instagram",
                          start_date=start.isoformat(), end_date=end.isoformat(), status="Planning", kpi_target=card["expect"], brief=f"{card['why']}.\nOffer: {card['offer']}.\nSuggested by Debut. Edit anything."))
    span = max((end - start).days, 1)
    posts = 0
    for i, ch in enumerate(card["channels"]):
        chan = ch["channel"] if ch["channel"] in __import__("modules").CHANNELS else "Other"
        for stage, frac in (("Teaser", 0.0), ("Launch", 0.5), ("Last call", 0.9)):
            if chan in ("Email", "LinkedIn") and stage == "Teaser" and i % 2:
                continue
            day = start + dt.timedelta(days=min(span, round(span * frac) + (i % 2)))
            ins("content_items", dict(workspace_id=W(), title=f"{card['event']} {stage.lower()}: {ch['do']}"[:140], channel=chan, format="Reel / Short" if "eel" in ch["do"] else "Post", status="Idea",
                                      publish_date=day.isoformat(), campaign=name, notes=f"From the plan “{name}”. Open the Create studio to design it."))
            posts += 1
    tasks = [("Fix the offer and the last date", 0), ("Prepare photos or screenshots", 2), ("Brief anyone helping (designer, staff, partners)", 3), ("Check stock, staff and delivery for the rush", max(1, card["lead"] - 3)), ("Review results after the date", card["lead"] + 2)]
    for t, off in tasks:
        ins("tasks", dict(workspace_id=W(), title=t, description=f"For {name}", due_date=min(start + dt.timedelta(days=off), end + dt.timedelta(days=3)).isoformat() if off else start.isoformat(),
                          priority="Medium", status="To do", related=name))
    S.audit("promo_plan", card["id"])
    flash(f"Plan ready: a campaign, {posts} dated posts and 5 tasks. Open any post to design it in the Create studio.")
    return redirect(url_for("calendar_view"))


@bp.route("/studio/done", methods=["POST"])
def done():
    """'I posted it': mark the post Published and (optionally) log the first numbers, so results start flowing without a separate trip to Results."""
    if g.role in ("viewer", "client"):
        abort(403)
    d = S.jbody()
    rid = int(d.get("rid") or 0)
    row = q("SELECT id, title, channel FROM content_items WHERE id=? AND workspace_id=?", (rid, W()), one=True)
    if not row:
        abort(404)
    ex("UPDATE content_items SET status='Published' WHERE id=? AND workspace_id=?", (rid, W()))
    logged = 0
    for metric in ("Reach", "Likes", "Saves"):
        try:
            v = float(d.get(metric.lower()))
        except (TypeError, ValueError):
            continue
        if 0 <= v < 1e9:
            ins("kpis", dict(workspace_id=W(), metric=metric, channel=row["channel"] or "", period=S.today().isoformat(), value=str(v), campaign="", notes=f"From post: {row['title']}"[:200]))
            logged += 1
    S.audit("studio_done", f"{rid} logged {logged}")
    return jsonify(ok=True, logged=logged, streak=_streak_now())


def _streak_now():
    try:
        import views
        return views._streak()
    except Exception:
        return 0


@bp.route("/studio/sets", methods=["GET", "POST"])
def sets():
    """Saved hashtag sets live in the Content Library (type 'Hashtag set'), so there is one place for saved text."""
    if request.method == "GET":
        rows = q("SELECT title, body FROM assets WHERE workspace_id=? AND type='Hashtag set' ORDER BY id DESC LIMIT 30", (W(),))
        return jsonify(sets=[dict(title=r["title"], body=r["body"]) for r in rows])
    if g.role in ("viewer", "client"):
        abort(403)
    d = S.jbody()
    title, body = _trim(d.get("title"), 60), " ".join(re.findall(r"#\w+", str(d.get("body") or "")))[:300]
    if not title or not body:
        return jsonify(error="Give the set a name and at least one hashtag."), 400
    ins("assets", dict(workspace_id=W(), title=title, type="Hashtag set", channel="Instagram", status="Approved", body=body))
    return jsonify(ok=True)


@bp.route("/grid")
def grid():
    """Instagram-style 3-column preview of what the profile will look like, newest first."""
    rows = q("SELECT id, title, publish_date, status, thumb, channel FROM content_items WHERE workspace_id=? AND channel='Instagram' AND status!='On hold' ORDER BY publish_date DESC, id DESC LIMIT 30", (W(),))
    return render_template("grid.html", rows=rows, today=S.today().isoformat())


@bp.route("/studio/pack.json")
def pack():
    """The next 7 days of designed posts, in posting order, so the browser can render them into one zip."""
    t = S.today()
    rows = q("SELECT id, title, channel, publish_date, copy, hashtags, studio FROM content_items WHERE workspace_id=? AND studio<>'' AND publish_date BETWEEN ? AND ? AND status!='On hold' ORDER BY publish_date, id LIMIT 20",
             (W(), t.isoformat(), (t + dt.timedelta(days=6)).isoformat()))
    items = []
    for r in rows:
        try:
            board = json.loads(r["studio"])
        except ValueError:
            continue
        items.append(dict(id=r["id"], title=r["title"], channel=r["channel"], date=r["publish_date"], caption=r["copy"], hashtags=r["hashtags"], board=board))
    return jsonify(items=items)
