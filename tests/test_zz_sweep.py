import re
from tests.test_app import signup, _invite

def test_sweep_every_page_every_role_no_500(app):
    o = signup(app, "sw@x.com", ws="Sweep Co")
    rules = [r for r in app.url_map.iter_rules() if "GET" in r.methods and r.endpoint != "static" and not r.arguments - {"key"}]
    paths = set()
    from modules import MODULES
    for r in rules:
        if r.arguments:
            for k in MODULES:
                paths.add(r.rule.replace("<key>", k).replace("<string:key>", k))
        else:
            paths.add(r.rule)
    bad = []
    for p in sorted(paths):
        if "<" in p or p.startswith("/admin") or "logout" in p or "/delete" in p or "/demo" in p:
            continue
        r = o.get(p)
        if r.status_code >= 500:
            bad.append((p, r.status_code))
    assert not bad, bad

def test_sweep_blank_and_hostile_posts_never_500(app):
    from modules import MODULES
    o = signup(app, "sw2@x.com", ws="Sweep Two")
    bad = []
    for k in MODULES:
        for data in ({}, {"title": "x" * 5000, "name": "<script>", "date": "garbage", "status": "zzz"}):
            for suf in ("save",):
                r = o.post(f"/m/{k}/{suf}", data=data)
                if r.status_code >= 500: bad.append((k, r.status_code))
        r = o.get(f"/m/{k}/new?modal=1")
        if r.status_code >= 500: bad.append((k, "new"))
    assert not bad, bad


def test_personal_reminders_set_fire_and_stay_private(app):
    import datetime as _d
    import services as S
    a = signup(app, "rem1@x.in", "Rem", "Rem Co", "Passw0rd!x")
    b = signup(app, "rem2@x.in", "Other", "Other Co", "Passw0rd!x")
    r = a.post("/reminders/add", data={"text": "Call the printer", "when": "tomorrow"}, follow_redirects=True)
    assert b"Reminder set" in r.data and b"Call the printer" in a.get("/app").data
    assert b"Call the printer" not in b.get("/app").data
    a.post("/reminders/add", data={"text": "", "when": "1h"}, follow_redirects=True)
    a.post("/reminders/add", data={"text": "x", "when": "pick", "date": "nope"}, follow_redirects=True)
    past = (S.now_ist() - _d.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
    a.post("/reminders/add", data={"text": "Due now", "when": "pick", "date": past[:10], "time": past[11:]}, follow_redirects=True)
    with app.app_context():
        assert S.fire_due_reminders() == 0                          # the dashboard visit already fired it, once
        from db import q
        assert len(q("SELECT id FROM notifications WHERE kind='reminder' AND message LIKE ?", ("%Due now%",))) == 1


def test_reminders_page_snooze_repeat_and_record_button(app):
    from db import q, ins

    def Q(sql):
        with app.app_context():
            return [dict(r) for r in q(sql)]
    a = signup(app, "rem3@x.in", "Rem3", "Rem3 Co", "Passw0rd!x")
    with app.app_context():
        wid = q("SELECT id FROM workspaces WHERE name='Rem3 Co'")[0]["id"]
        rid = ins("content_items", dict(workspace_id=wid, title="Diwali reel"))
    assert b"Remind me" in a.get(f"/m/content_items/{rid}/edit").data
    a.post("/reminders/add", data={"text": "Diwali reel", "when": "1h", "link": f"/m/content_items/{rid}/edit"}, follow_redirects=True)
    a.post("/reminders/add", data={"text": "Weekly review", "when": "pick", "date": "2020-01-01", "time": "09:00", "repeat": "weekly"}, follow_redirects=True)
    r = a.get("/reminders"); assert r.status_code == 200 and b"Diwali reel" in r.data and b"repeats weekly" in r.data
    rem = Q("SELECT id FROM reminders WHERE text='Diwali reel'")[0]["id"]
    assert a.post(f"/reminders/{rem}/snooze", data={"by": "tomorrow"}, follow_redirects=True).status_code == 200
    assert a.post(f"/reminders/{rem}/delete", follow_redirects=True).status_code == 200
    assert not Q("SELECT id FROM reminders WHERE text='Diwali reel'")
    assert len(Q("SELECT id FROM reminders WHERE text='Weekly review' AND done=0")) == 1       # repeat leaves exactly one pending


def test_client_gets_one_nudge_a_day_for_posts_waiting(app):
    import services as S
    from db import q, ins
    a = signup(app, "nud@x.in", "Nud", "Nud Co", "Passw0rd!x")
    with app.app_context():
        wid = q("SELECT id FROM workspaces WHERE name='Nud Co'")[0]["id"]
        uid = ins("users", dict(email="cl@x.in", name="Cli", password_hash="x"))
        ins("memberships", dict(workspace_id=wid, user_id=uid, role="client", client_name="Acme"))
        ins("content_items", dict(workspace_id=wid, title="Reel", status="Review", client="Acme"))
        assert S.client_approval_nudges() == 1 and S.client_approval_nudges() == 0


def test_teammate_reminder_and_client_brand(app):
    from db import q, ins
    a = signup(app, "tm1@x.in", "Boss", "Tm Co", "Passw0rd!x")
    with app.app_context():
        wid = q("SELECT id FROM workspaces WHERE name='Tm Co'")[0]["id"]
        uid = ins("users", dict(email="mate@x.in", name="Mate Kumar", password_hash="x"))
        ins("memberships", dict(workspace_id=wid, user_id=uid, role="lead"))
        ins("clients", dict(workspace_id=wid, name="Acme", brand_color="#e63946", logo_url=""))
    assert b"Mate Kumar" in a.get("/reminders").data
    r = a.post("/reminders/add", data={"text": "Send the brief", "when": "1h", "for": str(uid)}, follow_redirects=True)
    assert b"They will get a notification" in r.data
    with app.app_context():
        row = q("SELECT user_id, by_user FROM reminders WHERE text='Send the brief'")[0]
        assert row["user_id"] == uid and row["by_user"] != uid
        # someone outside the workspace can never be targeted
        a.post("/reminders/add", data={"text": "Sneaky", "when": "1h", "for": "99999"}, follow_redirects=True)
        assert q("SELECT user_id FROM reminders WHERE text='Sneaky'")[0]["user_id"] != 99999


def test_studio_has_new_layouts_motion_and_industry_wording():
    js = open("static/studio.js").read()
    for lay in ("photo", "split", "price", "countdown", "review", "spotlight", "poll", "bold", "coupon", "menu", "timeline", "stat3", "event", "ribbon", "collage", "magazine", "versus"):
        assert f"{lay}: function (c)" in js and f'{lay}: "' in js, lay
    for word in ("progressBar", "frameAt", 'id="st-trans"' if False else "st-trans"):
        assert word in js
    assert 'id="st-trans"' in open("templates/studio.html").read()
    tpl = open("static/studio_tpl.js").read()
    for lab in ("Product spotlight", "Price tag", "Stop scrolling reel", "Countdown reel", "Review card", "Coupon", "Event invite", "Magazine cover", "How it works"):
        assert lab in tpl
    for cta in ("Book a table", "Start free trial", "Book a site visit", "Enrol now"):
        assert cta in tpl


def test_launch_deck_is_paid_only_and_adds_dated_items(app):
    from db import q
    from tests.conftest import dbx
    o = signup(app, "ld@x.in", "Lead", "Deck Co", "Passw0rd!x")
    assert o.get("/launch-deck").status_code == 200
    items = [{"title": f"Piece {i}", "caption": "cap", "date": f"2027-01-{i+1:02d}", "kind": "post", "channel": "Instagram", "board": {}} for i in range(15)]
    items.append({"title": "bad date", "date": "nope"})
    # free plan: page opens (teaser) but saving is blocked
    dbx(app, "UPDATE workspaces SET plan='free', plan_status='free'")
    assert o.get("/launch-deck").status_code == 200
    r = o.post("/launch-deck/create", json={"campaign": "Glow", "items": items})
    assert r.status_code == 402 and r.get_json()["upgrade"] == "/billing"
    # paid plan: all valid items are saved with their dates, bad ones skipped
    dbx(app, "UPDATE workspaces SET plan='starter', plan_status='active'")
    r = o.post("/launch-deck/create", json={"campaign": "Glow", "items": items})
    assert r.status_code == 200
    assert len(r.get_json()["items"]) == 15
    with app.app_context():
        rows = q("SELECT publish_date FROM content_items WHERE title LIKE 'Piece %'")
        assert len(rows) == 15 and all(str(x["publish_date"]).startswith("2027-01") for x in rows)
    # the paid feature is advertised on the plan cards
    assert b"Complete Launch Deck" in app.test_client().get("/pricing").data


def test_push_keys_autogenerate_scheduler_jobs_run_once_and_test_button(app, monkeypatch):
    import datetime as _d
    import services as S
    from db import q, ins
    o = signup(app, "pu@x.in", "Pushy", "Push Co", "Passw0rd!x")
    k1 = o.get("/push/key").get_json()["key"]
    assert len(k1) > 60 and o.get("/push/key").get_json()["key"] == k1   # stable across calls
    assert o.post("/push/test").status_code == 400                          # nothing subscribed yet
    with app.app_context():
        uid = q("SELECT id FROM users WHERE email='pu@x.in'")[0]["id"]
        ins("push_subs", dict(user_id=uid, endpoint="https://push.example/abc", p256dh="p", auth="a"))
        sent = []
        monkeypatch.setattr(S, "send_push", lambda u, m, l="": sent.append((u, m)))
        assert S.claim_job("t", "2027-01-01") is True
        assert S.claim_job("t", "2027-01-01") is False                       # second worker is refused
        assert S.claim_job("t", "2027-01-02") is True
    assert o.post("/push/test").get_json()["ok"] is True and sent
    with app.app_context():
        wid = q("SELECT id FROM workspaces WHERE name='Push Co'")[0]["id"]
        past = (S.now_ist() - _d.timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M")
        ins("reminders", dict(workspace_id=wid, user_id=uid, text="Ring ring", remind_at=past, link="", repeat="", by_user=0))
        assert S.run_due_jobs()["reminders"] == 1
        assert S.run_due_jobs()["reminders"] == 0


def test_moodboard_real_photo_search_and_add(app, monkeypatch):
    import photos, services as S
    from db import q
    o = signup(app, "ph@x.in", "Pho", "Photo Co", "Passw0rd!x")
    o.post("/moodboards/new", data={"name": "Cafe look"})
    with app.app_context():
        bid = q("SELECT id FROM boards WHERE name='Cafe look'")[0]["id"]
    monkeypatch.setattr(photos, "search", lambda qs, n=18: [dict(thumb="https://x/t.jpg", full="https://x/f.jpg", credit="Photo by Ann on Pexels", link="")])
    r = o.get(f"/moodboards/{bid}/photos?q=coffee").get_json()
    assert r["results"][0]["credit"].startswith("Photo by Ann")
    monkeypatch.setattr(S, "safe_get", lambda url, **k: b"\x89PNG\r\n\x1a\n" + b"0" * 50)
    assert o.post(f"/moodboards/{bid}/photos/add", json={"url": "https://x/f.jpg", "credit": "Photo by Ann on Pexels"}).get_json()["ok"]
    assert o.post(f"/moodboards/{bid}/photos/add", json={"url": "http://x/f.jpg"}).status_code == 400   # https only
    monkeypatch.setattr(S, "safe_get", lambda url, **k: b"<html>not an image</html>")
    assert o.post(f"/moodboards/{bid}/photos/add", json={"url": "https://x/f.jpg"}).status_code == 400
    with app.app_context():
        rows = q("SELECT kind, caption FROM board_items WHERE board_id=? AND caption LIKE 'Photo by Ann%'", (bid,))
        assert len(rows) == 1 and rows[0]["kind"] == "image"
    def boom(*a, **k): raise OSError("down")
    monkeypatch.setattr(photos, "search", boom)
    assert o.get(f"/moodboards/{bid}/photos?q=x").status_code == 502          # friendly failure, never a 500
    assert b"Find real photos" in o.get(f"/moodboards/{bid}").data


def test_reference_links_fold_into_the_library_once_and_the_old_table_is_gone(app):
    import db as D
    from modules import MODULES
    from db import ex, q
    with app.app_context():
        ex("CREATE TABLE reference_links (id " + D._pk() + ", workspace_id INTEGER, title TEXT, url TEXT, category TEXT, tags TEXT, notes TEXT, favorite TEXT, created_at TIMESTAMP)")
        ex("INSERT INTO reference_links (workspace_id, title, url, category, tags, notes, favorite, created_at) VALUES (7,'Great ad','https://e.com/a','Inspiration','ads','nice hook','Yes','2026-01-01')")
        ex("INSERT INTO reference_links (workspace_id, title, url, category, tags, notes, favorite, created_at) VALUES (7,'No cat','https://e.com/b','','','','No','2026-01-02')")
        D.init_schema(MODULES)
        D.init_schema(MODULES)                                   # a second boot must not copy them again
        rows = q("SELECT title, type, url, tags, favorite, body, status FROM assets WHERE workspace_id=7 ORDER BY id")
        assert [r["title"] for r in rows] == ["Great ad", "No cat"]
        assert rows[0]["type"] == "Inspiration" and rows[0]["url"] == "https://e.com/a" and rows[0]["favorite"] == "Yes" and rows[0]["body"] == "nice hook"
        assert rows[1]["type"] == "Link"
        from sqlalchemy import inspect
        assert "reference_links" not in inspect(D.engine).get_table_names()
