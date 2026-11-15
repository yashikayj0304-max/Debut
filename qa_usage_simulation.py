"""50 companies x 21 simulated days of real use: do they always have something to do? Where does it run dry?"""
exec(open("fifty.py").read().split("t0 = time.time()")[0])
import views as V
base = S.today()
cur = {"d": 0}
S.today = lambda: base + dt.timedelta(days=cur["d"])
res = []
random.seed(11)
for i, (name, ind) in enumerate(COMPANIES):
    c = app.test_client(); email = f"flow{i}@{re.sub('[^a-z]','',name.lower())}.in"; cur["d"] = 0
    c.post("/signup", data=dict(name=f"Own {i}", email=email, workspace=name, password="Sup3rSecret!", agree="1", industry=ind, kit="1", starter_posts="1"))
    w = wid_of = None
    with app.app_context():
        w = q("SELECT w.id FROM workspaces w JOIN users u ON u.id=w.owner_id WHERE u.email=?", (email,), one=True)["id"]
    persona = random.choice(["diligent", "casual", "ghost"])          # diligent uses it daily, casual every 3rd day, ghost opens once a week
    chans = random.sample(["Instagram", "LinkedIn", "Email", "YouTube", "WhatsApp", "Facebook"], random.choice([1, 2, 3]))
    r = c.post("/welcome", data=dict(channels=chans, per_week=str(random.choice([1, 2, 3, 5])), goal="Grow sales"))
    days = []
    for d in range(21):
        cur["d"] = d
        if persona == "casual" and d % 3: continue
        if persona == "ghost" and d % 7: continue
        pg = c.get("/app"); html = pg.get_data(as_text=True)
        txt = re.sub(r"<[^>]+>", " ", html)
        n_post = html.count('data-val="Published"'); n_tick = html.count('class="tick"') - n_post
        wp = "This week&#39;s plan" in html or "This week's plan" in html
        with app.app_context():
            up = q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND publish_date BETWEEN ? AND ? AND status NOT IN ('Published')", (w, S.today().isoformat(), (S.today() + dt.timedelta(days=7)).isoformat()), one=True)["c"]
            overdue_posts = q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND publish_date<? AND status NOT IN ('Published','Idea','Draft')", (w, S.today().isoformat()), one=True)["c"]
            ideas_old = q("SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND publish_date<? AND status='Idea'", (w, S.today().isoformat()), one=True)["c"]
        actionable = n_post + n_tick + (1 if wp else 0)
        days.append(dict(d=d, actionable=actionable, upcoming=up, wp=wp, overdue_posts=overdue_posts, stale_ideas=ideas_old, headline=re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S) and re.sub(r"<[^>]+>", "", re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S).group(1)).strip()[:60]))
        # act like the persona
        if persona != "ghost":
            if wp: c.post("/plan-week/accept", data={})
            if "Your calendar is running low" in html and (persona == "diligent" or random.random() < .5): c.post("/plan-more", data={})
            for m in re.finditer(r'data-tid="(\d+)"( data-key="content_items" data-val="Published")?', html):
                if persona == "diligent" or random.random() < .5:
                    c.post(f"/m/{'content_items' if m.group(2) else 'tasks'}/{m.group(1)}/status", data=dict(value="Published" if m.group(2) else "Done"))
    res.append(dict(co=name, ind=ind, persona=persona, days=days))
# ---- analysis
dry = collections.Counter(); first_dry = []
for r in res:
    for x in r["days"]:
        if x["upcoming"] == 0: dry["calendar empty for next 7 days"] += 1
        if x["actionable"] == 0 and x["upcoming"] == 0: dry["nothing to do AND nothing coming"] += 1
        if x["overdue_posts"] > 0: dry["has overdue unposted posts"] += 1
        if x["stale_ideas"] > 0: dry["has past 'Idea' posts nobody dealt with"] += 1
    fd = next((x["d"] for x in r["days"] if x["upcoming"] == 0), None)
    first_dry.append((r["persona"], fd))
tot = sum(len(r["days"]) for r in res)
print("visits simulated:", tot, dict(dry))
for p in ("diligent", "casual", "ghost"):
    fs = [f for pp, f in first_dry if pp == p]
    got = [f for f in fs if f is not None]
    print(p, "companies:", len(fs), "| calendar ran dry for:", len(got), "| median first dry day:", sorted(got)[len(got)//2] if got else None)
heads = collections.Counter(x["headline"] for r in res for x in r["days"]); print(heads.most_common(8))
json.dump(res, open("/tmp/flow50.json", "w"), default=str)
