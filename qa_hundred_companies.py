"""50 companies x every operation, in-process against a fresh DB. Writes /tmp/fifty_report.json and prints a summary."""
import os, sys, re, io, json, time, random, tempfile, datetime as dt, collections, struct, zlib
sys.path.insert(0, "/home/claude/work/debut")
tmp = tempfile.mkdtemp()
import config as C, services as S, db as D
from db import q, ex
C.UPLOAD_DIR = os.path.join(tmp, "up"); C.BILLING_MODE = "demo"
from app import create_app
app = create_app(config={"TESTING": True, "PROPAGATE_EXCEPTIONS": False, "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False}, database_url=f"sqlite:///{tmp}/f.db")
from modules import MODULES
import industries as IND
random.seed(7)
MAILS = []
import views as V
C.ANTHROPIC_API_KEY = "test-key"
V.claude_call = lambda system, user, mx, research=False: ("Chai-fuelled caption: kya haal hai! " + user[:40], [("https://example.com", "Src")] if research else [])
S.send_email = lambda to, subject, body: MAILS.append((to, subject, body)) or True

COMPANIES = [  # name, industry
    ("Chai Wallah", "fmcg"), ("Masala Basket", "fmcg"), ("Dal Dhaba Foods", "fmcg"), ("Kulhad Kitchen", "fmcg"),
    ("Glow Rituals", "d2c"), ("Urban Nest", "d2c"), ("Bloom Box", "d2c"), ("Pawfect Pets", "d2c"),
    ("Spice Route Cafe", "hospitality"), ("Hotel Mandala", "hospitality"), ("Brew Lane", "hospitality"), ("Taj Retreat Spa", "hospitality"),
    ("Ledgerly", "saas"), ("PingDesk", "saas"), ("Stackwise", "saas"), ("FormFox", "saas"),
    ("Skyline Homes", "realestate"), ("Greenview Realty", "realestate"), ("PlotPe", "realestate"),
    ("BrightPath Academy", "education"), ("Maths Mitra", "education"), ("CodeKul", "education"), ("Vidya Tutors", "education"),
    ("CareFirst Clinic", "healthcare"), ("Smile Dental", "healthcare"), ("Vita Labs", "healthcare"),
    ("Saree Studio", "fashion"), ("Denim Dost", "fashion"), ("Thread & Loom", "fashion"), ("Kicks Kart", "fashion"),
    ("PayEasy", "fintech"), ("SafeInvest", "fintech"), ("LoanLift", "fintech"),
    ("Studio Neon", "agency"), ("Pixel Pandit", "agency"), ("Growth Guild", "agency"), ("Reel Factory", "agency"),
    ("Riya Creates", "personal_brand"), ("Coach Kabir", "personal_brand"), ("Dr Anaya Speaks", "personal_brand"),
    ("SteelCraft Industries", "b2b"), ("PackRight Solutions", "b2b"), ("CloudKitchen Supplies", "b2b"),
    ("Daily Mart", "retail"), ("Fashion Street Store", "retail"), ("Gadget Galli", "retail"),
    ("LaunchPad Labs", "startup"), ("Fundr", "startup"), ("MoveEasy", "startup"), ("General Traders", "general"),
]
COMPANIES = COMPANIES + [(n + ' Two', i) for n, i in COMPANIES]
assert len(COMPANIES) == 100
PLANS = ["free", "creator", "starter", "team", "agency"]
findings = collections.OrderedDict()
stats = collections.Counter()
slow = []
TALLY = collections.Counter()


def png():
    def ch(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    raw = b"".join(b"\x00" + b"\xff\x80\x40" * 8 for _ in range(8))
    return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b"")


BAD = [("Traceback", "traceback"), ("{{", "unrendered {{"), ("{%", "unrendered {%"), (">None<", "literal None"), ("undefined", "undefined text"), ("NaN", "NaN"), ("Internal Server Error", "500 page"), ("jinja2", "jinja leak")]


def flag(co, op, kind, detail=""):
    k = (kind, op.split("?")[0].split("#")[0])
    d = findings.setdefault(k, dict(kind=kind, op=op, count=0, cos=[], detail=detail))
    d["count"] += 1
    if len(d["cos"]) < 4:
        d["cos"].append(co)


def hit(c, co, method, url, expect=(200, 201, 202, 204, 301, 302, 303, 304, 400, 401, 403, 404, 405, 409, 413, 422, 429), **kw):
    t = time.time()
    try:
        r = getattr(c, method)(url, **kw)
    except Exception as e:
        flag(co, f"{method.upper()} {url}", "EXCEPTION", repr(e)[:200]); return None
    dt_ = time.time() - t
    stats["requests"] += 1
    TALLY[(method.upper(), re.sub(r'/m/[a-z_]+', '/m/K', re.sub(r'\d+', 'N', url.split('?')[0])), r.status_code)] += 1
    if dt_ > 1.5:
        slow.append((round(dt_, 2), method.upper(), url, co))
    if r.status_code >= 500:
        flag(co, f"{method.upper()} {url}", f"HTTP {r.status_code}", (r.get_data(as_text=True)[:160]))
    elif r.status_code == 200 and "html" in (r.mimetype or "") and method == "get":
        body = r.get_data(as_text=True)
        for needle, why in BAD:
            if needle in body:
                if needle == "undefined" and "typeof" in body and body.count("undefined") == body.count("typeof") + body.count("=== undefined") + body.count("== undefined") + body.count("!== undefined"):
                    continue
                i = body.index(needle)
                flag(co, f"GET {url}", why, re.sub(r"\s+", " ", body[max(0, i - 70):i + 70]))
    return r


def val(f, i, co, inds):
    key, label, typ, opts = f[0], f[1], f[2], f[3]
    if typ == "select":
        return random.choice(opts) if opts else ""
    if typ == "multi":
        return ",".join(random.sample(opts, min(2, len(opts)))) if opts else ""
    if typ == "date":
        return (S.today() + dt.timedelta(days=random.randint(-10, 40))).isoformat()
    if typ == "number":
        return str(random.choice([0, 1, 250, 12500, 99999]))
    if typ == "url":
        return f"https://example.com/{key}/{i}"
    if typ == "textarea":
        return f"{co} {label} note {i}\nSecond line with <b>html</b> & \"quotes\" and Hinglish: kya haal hai ₹5,000"
    if "email" in key:
        return f"p{i}@{re.sub('[^a-z]', '', co.lower())}.in"
    return f"{co} {label} {i}"


def run_company(i, name, ind):
    idx = i
    co = f"{name}|{ind}"
    c = app.test_client()
    email = f"owner{i}@{re.sub('[^a-z]', '', name.lower())}.in"
    plan = PLANS[i % 5]
    team_n = [1, 1, 3, 6][i % 4]
    r = hit(c, co, "post", "/signup", data=dict(name=f"Owner {i}", email=email, workspace=name, password="Sup3rSecret!", agree="1", industry=ind, kit="1", starter_posts="1" if i % 2 == 0 else ""))
    if not r or r.status_code != 302:
        flag(co, "POST /signup", "SIGNUP FAILED", str(r and r.status_code)); return
    with app.app_context():
        wid = q("SELECT w.id FROM workspaces w JOIN users u ON u.id=w.owner_id WHERE u.email=?", (email,), one=True)["id"]
        ex("UPDATE workspaces SET plan=?, plan_status='active' WHERE id=?", (plan, wid))
    # ---- new flows
    hit(c, co, "post", "/welcome", data=dict(channels=["Instagram", "Email"], per_week="3", goal="Win the month"))
    hit(c, co, "post", "/plan-week/accept", data={})
    hit(c, co, "post", "/plan-more", data={})
    hit(c, co, "post", "/first-week/numbers", data=dict(followers="1,200", reach="3400", orders="25"))
    hit(c, co, "post", "/first-week/numbers", data=dict(followers="abc", reach="-1", orders="1e99"))
    hit(c, co, "post", "/welcome", data=dict(channels=["Nope"], per_week="99", goal="x" * 500))
    # ---- round-3 flows: late posts, full checklist, AI voice, view switch, bad input
    with app.app_context():
        for i in range(4):
            ex("INSERT INTO content_items (workspace_id, title, channel, status, publish_date) VALUES (?,?,?,?,?)", (wid, f"Late {i}", "Instagram", "Planned", (S.today() - dt.timedelta(days=2 + i)).isoformat()))
    hit(c, co, "get", "/app")
    hit(c, co, "post", "/overdue/move", data={})
    hit(c, co, "post", "/overdue/skip", data={})
    hit(c, co, "post", "/overdue/bogus", data={})
    hit(c, co, "post", "/checklist/full", data={})
    for u in ("/calendar", "/kanban/content_items", "/m/content_items", "/ai", "/m/experiments", "/utm", "/marketing-health"):
        hit(c, co, "get", u)
    hit(c, co, "post", "/api/ai", json=dict(task="positioning", product="x", voice="y" * 5000, lang="Klingon"))
    hit(c, co, "post", "/overdue/move"); hit(c, co, "post", "/overdue/skip"); hit(c, co, "post", "/overdue/nope"); hit(c, co, "post", "/checklist/full")
    for u in ("/kanban/content_items", "/m/content_items", "/m/launch_checklist", "/m/experiments", "/utm", "/marketing-health"):
        hit(c, co, "get", u)
    hit(c, co, "post", "/api/ai", json=dict(task="positioning", product="x", voice="<script>alert(1)</script>", lang="Hinglish"))
    # ---- every plain GET page
    pages = ["/app", "/app?who=mine", "/calendar", "/calendar?view=week", "/calendar?view=list", "/ideas", "/ideas/picker", "/whatnow", "/analytics", "/marketing-health", "/report", "/recap", "/moodboards", "/team", "/team-hub", "/activity", "/activity/export.csv",
             "/account", "/billing", "/integrations", "/notifications", "/notifications/recent", "/search?q=a", "/search?q=" + name.split()[0], "/utm", "/utm/new", "/discover", "/content-ops", "/pulse", "/ai", "/kudos", "/updates", "/templates", "/glossary", "/help", "/manual",
             "/studio", "/promos", "/about", "/channels", "/changelog", "/features", "/pricing", "/terms", "/privacy", "/contact", "/offline", "/export.zip", "/team/invite-template.csv", "/workspace/new", "/refunds", "/feedback", "/manifest.webmanifest", "/sw.js", "/robots.txt", "/sitemap.xml", "/health", "/survey", "/first-week"]
    for p in pages:
        hit(c, co, "get", p)
    for key, m in MODULES.items():
        for p in (f"/m/{key}", f"/m/{key}?q=a", f"/m/{key}/new", f"/m/{key}/export", f"/m/{key}/template", f"/m/{key}/template.xlsx", f"/kanban/{key}"):
            hit(c, co, "get", p)
    # ---- CRUD on every module
    created = {}
    for key, m in MODULES.items():
        for n in range(2):
            data = {f[0]: val(f, n, name, ind) for f in m["fields"]}
            r = hit(c, co, "post", f"/m/{key}/save", data=data)
            if r is not None and r.status_code in (200, 302):
                with app.app_context():
                    row = q(f"SELECT id FROM {key} WHERE workspace_id=? ORDER BY id DESC LIMIT 1", (wid,), one=True)
                if row:
                    created.setdefault(key, []).append(row["id"])
        # hostile input
        evil = {f[0]: "<script>alert(1)</script>" for f in m["fields"] if f[2] in ("text", "textarea")}
        hit(c, co, "post", f"/m/{key}/save", data=evil)
        # missing required / empty
        hit(c, co, "post", f"/m/{key}/save", data={})
    for key, ids in created.items():
        for rid in ids[:1]:
            hit(c, co, "get", f"/m/{key}/{rid}/edit")
            m = MODULES[key]
            data = {f[0]: val(f, 9, name, ind) for f in m["fields"]}
            hit(c, co, "post", f"/m/{key}/save", data=dict(data, id=str(rid)))
            hit(c, co, "post", f"/m/{key}/{rid}/duplicate")
            hit(c, co, "post", f"/m/{key}/{rid}/comment", data=dict(body="Looks good, ship it 🚀"))
            hit(c, co, "post", f"/m/{key}/{rid}/react", data=dict(emoji="🔥"))
            hit(c, co, "post", f"/m/{key}/{rid}/presence")
            for st in ([f[3][-1] for f in m["fields"] if f[0] == (m.get("kanban") or "status") and f[3]][:1]):
                hit(c, co, "post", f"/m/{key}/{rid}/status", data=dict(value=st))
        # export + import round trip
        r = hit(c, co, "get", f"/m/{key}/export")
        if r is not None and r.status_code == 200:
            hit(c, co, "post", f"/m/{key}/import", data=dict(file=(io.BytesIO(r.data), "x.csv")), content_type="multipart/form-data")
        hit(c, co, "post", f"/m/{key}/import", data=dict(file=(io.BytesIO(b"\x00\x01garbage"), "x.csv")), content_type="multipart/form-data")
        hit(c, co, "post", f"/m/{key}/import", data=dict(file=(io.BytesIO(b"name\n\xff\xfe"), "x.csv")), content_type="multipart/form-data")
    for rid in created.get("tasks", [])[:1]:
        hit(c, co, "post", f"/m/tasks/{rid}/snooze")
    for rid in created.get("content_items", [])[:2]:
        hit(c, co, "post", "/api/reschedule", json=dict(id=rid, date=(S.today() + dt.timedelta(days=3)).isoformat()))
        hit(c, co, "post", "/ideas/schedule", data=dict(title="Test idea", channel="Instagram", format="Reel / Short", date=(S.today() + dt.timedelta(days=2)).isoformat()))
    # delete + undo on every module
    for key, ids in created.items():
        if len(ids) > 1:
            hit(c, co, "post", f"/m/{key}/{ids[-1]}/delete")
            hit(c, co, "post", "/m/undo")
    # ---- calendar, ICS, import
    r = hit(c, co, "get", "/calendar")
    mt = re.search(r"(/calendar/[\w.\-]+\.ics)", r.get_data(as_text=True)) if r is not None and r.status_code == 200 else None
    if mt:
        hit(c, co, "get", mt.group(1))
    hit(c, co, "post", "/calendar/reset-link")
    ics = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Imported\nDTSTART;VALUE=DATE:20261201\nEND:VEVENT\nEND:VCALENDAR"
    hit(c, co, "post", "/api/import_calendar", json=dict(text='[{"title":"AI post","channel":"Instagram","format":"Reel / Short","date":"%s"}]' % (S.today() + dt.timedelta(days=2)).isoformat()))
    hit(c, co, "post", "/api/import_calendar", json=dict(text="garbage"))
    # ---- mood boards
    r = hit(c, co, "post", "/moodboards/new", data=dict(name=f"{name} board"))
    with app.app_context():
        b = q("SELECT id FROM boards WHERE workspace_id=? ORDER BY id DESC LIMIT 1", (wid,), one=True)
    if b:
        bid = b["id"]
        hit(c, co, "get", f"/moodboards/{bid}")
        hit(c, co, "post", f"/moodboards/{bid}/add", data=dict(kind="note", content="Tone: warm", caption="Tone"))
        hit(c, co, "post", f"/moodboards/{bid}/add", data=dict(kind="color", content="#7c5cff", caption="Brand"))
        hit(c, co, "post", f"/moodboards/{bid}/add", data=dict(kind="link", content="https://example.com", caption="Ref"))
        hit(c, co, "post", f"/moodboards/{bid}/add", data=dict(kind="image", file=(io.BytesIO(png()), "a.png")), content_type="multipart/form-data")
        hit(c, co, "post", f"/moodboards/{bid}/add", data=dict(kind="image", file=(io.BytesIO(b"not an image"), "a.png")), content_type="multipart/form-data")
        with app.app_context():
            it = q("SELECT id FROM board_items WHERE board_id=? ORDER BY id", (bid,))
        for x in it[:3]:
            hit(c, co, "post", f"/moodboards/item/{x['id']}/edit", json=dict(caption="edited", content="edited"))
            hit(c, co, "post", f"/moodboards/item/{x['id']}/place", json=dict(x=30, y=40, w=200, h=150, z=2))
        hit(c, co, "post", f"/moodboards/{bid}/arrange")
        hit(c, co, "post", f"/moodboards/{bid}/save-colours")
        hit(c, co, "post", f"/moodboards/{bid}/rename", data=dict(name="Renamed 🎨"))
        r = hit(c, co, "post", f"/moodboards/{bid}/share")
        with app.app_context():
            tk = q("SELECT * FROM boards WHERE id=?", (bid,), one=True)
        tok = (dict(tk).get("share_token") or "")
        if tok:
            hit(app.test_client(), co, "get", f"/b/{tok}")
        hit(c, co, "post", f"/moodboards/{bid}/duplicate")
        for x in it[:1]:
            hit(c, co, "post", f"/moodboards/item/{x['id']}/delete")
        hit(c, co, "post", f"/moodboards/{bid}/delete")
    hit(c, co, "post", "/moodboards/sample")
    hit(c, co, "post", "/moodboards/template/diwali", data={})
    # ---- analytics import: realistic CSV exports
    csv = "Date,Impressions,Reach,Clicks,Amount spent (INR)\n2026-10-01,1200,900,40,500\n2026-10-08,1500,1100,52,600\n2026-10-15,1700,1300,61,650\n"
    hit(c, co, "post", "/analytics/import", data=dict(file=(io.BytesIO(csv.encode()), "meta.csv"), channel=""), content_type="multipart/form-data")
    hit(c, co, "post", "/analytics/import", data=dict(file=(io.BytesIO(b"nothing useful"), "x.csv"), channel=""), content_type="multipart/form-data")
    hit(c, co, "post", "/analytics/import", data=dict(), content_type="multipart/form-data")
    # ---- edge cases: injection, giant input, bad dates, CSV formulas, search, undo, plan limits
    evil_title = '<script>alert(1)</script>"><img src=x onerror=alert(2)>'
    hit(c, co, "post", "/m/content_items/save", data=dict(title=evil_title, channel="Instagram", status="Idea", publish_date=(S.today() + dt.timedelta(days=1)).isoformat()))
    hit(c, co, "post", "/m/content_items/save", data=dict(title="=HYPERLINK(\"http://evil\",\"x\")", channel="Instagram", status="Idea"))
    hit(c, co, "post", "/m/content_items/save", data=dict(title="x" * 20000, copy="y" * 200000, channel="Instagram"))
    hit(c, co, "post", "/m/content_items/save", data=dict(title="Bad date", publish_date="31-02-2026", channel="Nope", status="Nope"))
    hit(c, co, "post", "/m/leads/save", data=dict(name="Neg", value="-5", email="not-an-email", phone="x" * 500))
    hit(c, co, "post", "/m/kpis/save", data=dict(metric="M", value="abc", target="1e999", period="soon"))
    hit(c, co, "post", "/m/tasks/save", data=dict(title="Emoji 🚀🔥 नमस्ते ₹", due_date="2026-12-31", priority="High"))
    for p in ("/calendar", "/m/content_items", "/app", "/search?q=script", "/kanban/content_items", "/report", "/analytics"):
        r = hit(c, co, "get", p)
        if r is not None and r.status_code == 200:
            b = r.get_data(as_text=True)
            if "<script>alert(1)" in b or "<img src=x" in b:
                flag(co, f"GET {p}", "XSS", "stored script rendered unescaped")
    r = hit(c, co, "get", "/m/content_items/export")
    if r is not None and r.status_code == 200:
        for ln in r.get_data(as_text=True).splitlines():
            if ln.startswith("=HYPERLINK") or ',=HYPERLINK' in ln or ',"=HYPERLINK' in ln:
                flag(co, "GET /m/content_items/export", "CSV INJECTION", ln[:100]); break
    r = hit(c, co, "get", "/search?q=" + name.split()[0])
    if r is not None and r.status_code == 200 and name.split()[0] not in r.get_data(as_text=True):
        flag(co, "GET /search", "SEARCH MISS", "own company records not found by search")
    with app.app_context():
        lim = q("SELECT plan FROM workspaces WHERE id=?", (wid,), one=True)["plan"]
        tot = sum(q(f"SELECT COUNT(*) c FROM {k} WHERE workspace_id=?", (wid,), one=True)["c"] for k in MODULES)
        bds = q("SELECT COUNT(*) c FROM boards WHERE workspace_id=?", (wid,), one=True)["c"]
    cfg = C.PLANS[lim]
    if tot > cfg["records"] + 150:          # starter kit rows are exempt; this is only a gross overshoot check
        flag(co, "plan limit", "RECORD LIMIT NOT ENFORCED", f"{lim}: {tot} records vs limit {cfg['records']}")
    if bds > cfg["boards"]:
        flag(co, "plan limit", "BOARD LIMIT NOT ENFORCED", f"{lim}: {bds} boards vs limit {cfg['boards']}")
    # ---- AI / pulse / ask (no key set: must fail soft)
    for task in list(V.AI_TASKS)[:40]:
        if task in V.HIDDEN_TASKS: continue
        r = hit(c, co, "post", "/api/ai", json=dict(task=task, product=name, audience="young Indians", tone="Hinglish", use_plan=True))
        if r is not None and r.status_code not in (200, 402, 403, 429):
            flag(co, f"POST /api/ai task={task}", f"AI HTTP {r.status_code}", r.get_data(as_text=True)[:120])
    hit(c, co, "post", "/api/ask", json=dict(q="what should I post this week?"))
    hit(c, co, "post", "/api/pulse/brief", json={})
    hit(c, co, "post", "/pulse/refresh")
    hit(c, co, "post", "/pulse/watch/add", data=dict(term=name, type="brand", region="IN"))
    hit(c, co, "post", "/pulse/holidays", data=dict(country="IN", year="2026"))
    hit(c, co, "post", "/api/save_asset", json=dict(title="Saved", body="Caption text", type="caption", channel="Instagram"))
    # ---- account
    hit(c, co, "post", "/account/profile", data=dict(name=f"Owner {i} ✏️", phone="9999999999"))
    hit(c, co, "post", "/account/theme", data=dict(brand_color="#ff6b35", secondary_color="#2f4858"))
    hit(c, co, "post", "/account/theme/reset")
    hit(c, co, "post", "/account/focus", data=dict(focus="plan"))
    hit(c, co, "post", "/account/password", data=dict(current="Sup3rSecret!", new="N3wSecret!!x", confirm="N3wSecret!!x"))
    hit(c, co, "post", "/account/logo", data=dict(logo=(io.BytesIO(png()), "l.png")), content_type="multipart/form-data")
    hit(c, co, "post", "/account/logo", data=dict(logo=(io.BytesIO(b"nope"), "l.png")), content_type="multipart/form-data")
    hit(c, co, "post", "/account/logo/remove")
    hit(c, co, "post", "/account/digest", data=dict(on="1"))
    hit(c, co, "post", "/account/verify")
    hit(c, co, "post", "/account/onboarded")
    hit(c, co, "post", "/pal", json=dict(pal="sunset"))
    hit(c, co, "post", "/industry", data=dict(industry=random.choice(list(IND.INDUSTRIES))))
    hit(c, co, "post", "/pmf", data=dict(answer="very"))
    hit(c, co, "post", "/feedback", data=dict(kind="idea", message=f"{name}: add dark mode please", page="/app"))
    hit(c, co, "post", "/notifications/read")
    # ---- integrations: API key + REST API CRUD + lead hook
    r = hit(c, co, "post", "/integrations/api-keys", data=dict(name="zap"))
    body = r.get_data(as_text=True) if r is not None else ""
    r2 = hit(c, co, "get", "/integrations")
    mk = re.search(r"(dbt_[A-Za-z0-9_\-]{20,})", (r2.get_data(as_text=True) if r2 is not None else "") + body) or re.search(r"(gtm_[A-Za-z0-9_\-]{20,})", body)
    hit(c, co, "post", "/integrations/hook-reset")
    with app.app_context():
        hk = q("SELECT hook_key, slug FROM workspaces WHERE id=?", (wid,), one=True)
    hit(app.test_client(), co, "post", f"/hooks/lead/{hk['hook_key']}", json=dict(name="Hook Lead", email="h@x.in", phone="9000000000"))
    pc = app.test_client()
    hit(pc, co, "get", f"/lead/{hk['slug']}")
    hit(pc, co, "post", f"/lead/{hk['slug']}", data=dict(name="Form Lead", email="f@x.in", message="Interested", consent="1"))
    hit(pc, co, "post", f"/lead/{hk['slug']}", data=dict(name="", email="bad"))
    hit(pc, co, "get", f"/apply/{hk['slug']}")
    hit(pc, co, "post", f"/apply/{hk['slug']}", data=dict(name="Creator X", email="cx@x.in", skills="video", city="Pune"))
    # ---- team: invite, accept, roles, privileges
    roles = ["manager", "creator", "viewer", "lead", "admin", "creator"][:max(0, team_n - 1)]
    for k, role in enumerate(roles):
        em = f"t{k}_{i}@{re.sub('[^a-z]', '', name.lower())}.in"
        n0 = len(MAILS)
        hit(c, co, "post", "/team/invite", data=dict(email=em, role=role))
        mm = [m for m in MAILS[n0:] if em in m[0]]
        if not mm:
            stats["invite_blocked_by_plan"] += 1
            continue
        link = re.search(r"(/invite/[\w\-]+)", mm[0][2]).group(1)
        t = app.test_client()
        hit(t, co, "get", link)
        r = hit(t, co, "post", "/signup", data=dict(name=f"T{k}", email=em, password="Sup3rSecret!", agree="1", invite=link.split("/")[-1]))
        if r is None or r.status_code != 302:
            flag(co, "POST /signup (invite)", "INVITE SIGNUP FAILED", str(r and r.status_code)); continue
        # every role walks the app
        for p in ("/app", "/calendar", "/m/content_items", "/m/tasks", "/m/leads", "/analytics", "/team", "/account", "/moodboards", "/ideas", "/search?q=a", "/recap", "/billing", "/activity"):
            hit(t, co, "get", p)
        hit(t, co, "post", "/m/content_items/save", data=dict(title=f"By {role}", channel="Instagram", status="Idea"))
        hit(t, co, "post", "/m/tasks/save", data=dict(title=f"Task by {role}"))
        if role == "viewer":                          # a viewer must never write
            with app.app_context():
                n_before = q("SELECT COUNT(*) c FROM leads WHERE workspace_id=?", (wid,), one=True)["c"]
            r = hit(t, co, "post", "/m/leads/save", data=dict(name="Viewer sneaked in"))
            with app.app_context():
                if q("SELECT COUNT(*) c FROM leads WHERE workspace_id=?", (wid,), one=True)["c"] != n_before:
                    flag(co, "POST /m/leads/save as viewer", "PRIVILEGE LEAK", "viewer wrote a lead")
        if role == "creator":                         # creators see only their own scope and cannot reach admin pages
            for p in ("/team", "/billing", "/integrations", "/m/clients", "/m/payments"):
                r = hit(t, co, "get", p)
                if r is not None and r.status_code == 200 and p in ("/team", "/billing", "/integrations"):
                    flag(co, f"GET {p} as creator", "PRIVILEGE LEAK", "creator reached an admin page")
        with app.app_context():
            uid = q("SELECT id FROM users WHERE email=?", (em,), one=True)["id"]
        if k == 0:
            with app.app_context():
                mid = q("SELECT id FROM memberships WHERE workspace_id=? AND user_id=?", (wid, uid), one=True)["id"]
            hit(c, co, "post", "/team/role", data=dict(mid=mid, role="viewer"))
            hit(c, co, "post", "/team/role", data=dict(mid=mid, role="manager"))
    hit(c, co, "post", "/team/invite-csv", data=dict(file=(io.BytesIO(b"email,role\nbulk1@x.in,viewer\nbulk2@x.in,creator\nnot-an-email,viewer\n"), "i.csv")), content_type="multipart/form-data")
    hit(c, co, "post", "/team/invite", data=dict(email="client@acme.in", role="client", client_name="Acme"))
    hit(c, co, "post", "/kudos/send", data=dict(to_user=1, emoji="🎉", note="Great work"))
    # ---- REST API with a real key
    if mk:
        h = dict(Authorization="Bearer " + mk.group(1))
        ac = app.test_client()
        hit(ac, co, "get", "/api/v1/", headers=h)
        r = hit(ac, co, "post", "/api/v1/leads", json=dict(name="API Lead", email="a@x.in"), headers=h)
        hit(ac, co, "get", "/api/v1/leads", headers=h)
        hit(ac, co, "get", "/api/v1/nope", headers=h)
        hit(ac, co, "get", "/api/v1/leads")                  # no key: must be 401
    # ---- tenant isolation: another company's ids must be unreachable
    i = idx
    if i > 0 and created.get("leads"):
        other = app.test_client()
        other_email = f"owner{i - 1}@{re.sub('[^a-z]', '', COMPANIES[i - 1][0].lower())}.in"
        other.post("/login", data=dict(email=other_email, password="N3wSecret!!x"))
        rid = created["leads"][0]
        for p in (f"/m/leads/{rid}/edit",):
            r = hit(other, co, "get", p)
            if r is not None and r.status_code == 200 and name in r.get_data(as_text=True):
                flag(co, f"GET {p} from another company", "TENANT LEAK", "other company opened this record")
        r = hit(other, co, "post", f"/m/leads/{rid}/delete")
        with app.app_context():
            if not q("SELECT 1 FROM leads WHERE id=? AND workspace_id=?", (rid, wid), one=True) and created["leads"]:
                flag(co, "POST delete from another company", "TENANT LEAK", "other company deleted this record")
    # ---- workspace lifecycle
    hit(c, co, "post", "/workspace/rename", data=dict(name=f"{name} Renamed"))
    hit(c, co, "post", "/workspace/new", data=dict(name=f"{name} 2", industry=ind))
    with app.app_context():
        w2 = q("SELECT id FROM workspaces WHERE name=?", (f"{name} 2",), one=True)
    if w2:
        hit(c, co, "post", f"/switch/{w2['id']}")
        hit(c, co, "get", "/app")
        hit(c, co, "post", f"/switch/{wid}")
    hit(c, co, "get", "/billing")
    hit(c, co, "post", "/billing/subscribe/starter")
    hit(c, co, "post", "/billing/cancel")
    if i % 5 == 0:
        hit(c, co, "post", "/workspace/reset", data=dict(confirm=name + " Renamed"))
    hit(c, co, "post", "/logout")
    stats["companies_done"] += 1


t0 = time.time()
for i, (n, ind) in enumerate(COMPANIES):
    try:
        run_company(i, n, ind)
    except Exception as e:
        import traceback
        flag(f"{n}|{ind}", "HARNESS", "HARNESS ERROR", traceback.format_exc()[-300:])
    if i % 10 == 9:
        print(f"{i + 1}/50 done, {stats['requests']} requests, {round(time.time() - t0)}s", flush=True)
rep = dict(stats=dict(stats), secs=round(time.time() - t0), findings=list(findings.values()), slow=sorted(slow, reverse=True)[:25])
json.dump(rep, open("/tmp/fifty_report.json", "w"), indent=1, default=str)
print(json.dumps(dict(stats), indent=1), "secs", rep["secs"])
for f in rep["findings"]:
    print(f"[{f['kind']}] x{f['count']} {f['op']} :: {f['detail'][:150]} :: {f['cos'][:2]}")
print("SLOW", rep["slow"][:10])
by = collections.defaultdict(dict)
for (m, u, st), n in TALLY.items(): by[(m, u)][st] = n
for (m, u), d in sorted(by.items()):
    if any(k >= 400 for k in d): print("STATUS", m, u, dict(sorted(d.items())))
with app.app_context():
    for tname in list(MODULES) + ["boards", "board_items", "users", "workspaces", "comments", "invites", "api_keys", "notifications"]:
        print("ROWS", tname, q(f"SELECT COUNT(*) c FROM {tname}", one=True)["c"])
