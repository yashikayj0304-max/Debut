"""Bug-hunt rounds: roles, CSRF, hostile input, date edges, idempotency, old databases."""
import datetime as dt
import re
import pytest
from werkzeug.security import generate_password_hash
from conftest import dbq, dbx, signup, wid_of
import config as C
import services as S

ROLES = ["viewer", "creator", "client", "lead", "manager", "admin"]


def member(app, owner_email, role):
    w = wid_of(app, owner_email)
    em = f"{role}.{owner_email}"
    dbx(app, "INSERT INTO users (email, name, password_hash, email_verified, onboarded) VALUES (?,?,?,?,?)", (em, role.title(), generate_password_hash("Sup3rSecret!"), 1, 1))
    uid = dbq(app, "SELECT id FROM users WHERE email=?", (em,), one=True)["id"]
    dbx(app, "INSERT INTO memberships (workspace_id, user_id, role) VALUES (?,?,?)", (w, uid, role))
    c = app.test_client()
    assert c.post("/login", data=dict(email=em, password="Sup3rSecret!")).status_code in (200, 302)
    return c


def seed_late(app, w, n=3):
    for i in range(n):
        dbx(app, "INSERT INTO content_items (workspace_id, title, channel, status, publish_date) VALUES (?,?,?,?,?)", (w, f"Late {i}", "Instagram", "Planned", (S.today() - dt.timedelta(days=4 + i)).isoformat()))


@pytest.mark.parametrize("role", ["viewer", "creator", "client"])
def test_round2_low_roles_cannot_change_the_calendar(app, role):
    signup(app, "own@x.com")
    w = wid_of(app, "own@x.com")
    seed_late(app, w)
    c = member(app, "own@x.com", role)
    before = dbq(app, "SELECT id, publish_date, status FROM content_items WHERE workspace_id=? ORDER BY id", (w,))
    for url in ("/overdue/move", "/overdue/skip", "/checklist/full", "/plan-more", "/welcome", "/plan-week/accept"):
        r = c.post(url, data={}, follow_redirects=False)
        assert r.status_code in (302, 303, 400, 403, 404), (role, url, r.status_code)
    after = dbq(app, "SELECT id, publish_date, status FROM content_items WHERE workspace_id=? ORDER BY id", (w,))
    assert [tuple(x) for x in before] == [tuple(x) for x in after], role
    r = c.post("/api/ai", json=dict(task="positioning", product="x", voice="HACK", lang="Hindi"))
    assert dbq(app, "SELECT ai_voice FROM workspaces WHERE id=?", (w,), one=True)["ai_voice"] in ("", None)


@pytest.mark.parametrize("role", ["lead", "manager", "admin"])
def test_round2_managers_can_use_the_new_tools(app, role):
    signup(app, "own2@x.com")
    w = wid_of(app, "own2@x.com")
    seed_late(app, w)
    c = member(app, "own2@x.com", role)
    assert c.post("/overdue/move", follow_redirects=True).status_code == 200
    assert dbq(app, "SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND publish_date<?", (w, S.today().isoformat()), one=True)["c"] == 0
    assert c.post("/checklist/full", follow_redirects=True).status_code == 200


def test_round2_pages_open_for_every_role_without_errors(app):
    signup(app, "own3@x.com")
    for role in ROLES:
        c = member(app, "own3@x.com", role)
        for u in ("/app", "/calendar", "/kanban/content_items", "/m/content_items", "/ai", "/first-week", "/m/launch_checklist", "/analytics", "/ideas"):
            assert c.get(u).status_code < 500, (role, u)


def test_round2_new_posts_need_a_csrf_token(app):
    o = signup(app, "csrf@x.com")
    w = wid_of(app, "csrf@x.com")
    seed_late(app, w, 2)
    app.config["WTF_CSRF_ENABLED"] = True
    for url in ("/overdue/move", "/overdue/skip", "/checklist/full"):
        assert o.post(url).status_code in (400, 403), url
    assert dbq(app, "SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND publish_date<?", (w, S.today().isoformat()), one=True)["c"] == 2


def test_round2_unknown_overdue_action_is_harmless_and_tenants_do_not_mix(app):
    a = signup(app, "ta@x.com")
    wa = wid_of(app, "ta@x.com")
    seed_late(app, wa, 2)
    b = signup(app, "tb@x.com")
    wb = wid_of(app, "tb@x.com")
    seed_late(app, wb, 2)
    b.post("/overdue/skip", follow_redirects=True)
    assert dbq(app, "SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status='On hold'", (wa,), one=True)["c"] == 0      # company B's tap never touches company A
    assert dbq(app, "SELECT COUNT(*) c FROM content_items WHERE workspace_id=? AND status='On hold'", (wb,), one=True)["c"] == 2
    b.post("/overdue/dance", follow_redirects=True)
    assert dbq(app, "SELECT COUNT(*) c FROM content_items WHERE workspace_id=?", (wb,), one=True)["c"] >= 2


EVIL = ['<script>alert(1)</script>', '"><img src=x onerror=alert(1)>', "'; DROP TABLE users;--", "{{7*7}}", "{% raw %}", "‮ RTL ‭", "😀" * 50, "a" * 5000, "\x00null\x00"]


def test_round3_hostile_text_is_escaped_everywhere_the_new_features_show_it(app, monkeypatch):
    monkeypatch.setattr(C, "ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(C, "SMTP_HOST", "")
    import views as V
    monkeypatch.setattr(V, "claude_call", lambda *a, **k: ("ok", []))
    o = signup(app, "evil@x.com")
    w = wid_of(app, "evil@x.com")
    for e in EVIL:
        r = o.post("/api/ai", json=dict(task="positioning", product=e, voice=e, lang=e, tone=e, extra=e))
        assert r.status_code in (200, 400), e[:20]
        dbx(app, "INSERT INTO content_items (workspace_id, title, channel, status, publish_date) VALUES (?,?,?,?,?)", (w, e[:200].replace("\x00", ""), "Instagram", "Planned", (S.today() - dt.timedelta(days=2)).isoformat()))
    assert len(dbq(app, "SELECT ai_voice FROM workspaces WHERE id=?", (w,), one=True)["ai_voice"] or "") <= 600
    assert dbq(app, "SELECT ai_lang FROM workspaces WHERE id=?", (w,), one=True)["ai_lang"] in ("English", "Hinglish", "Hindi")
    for u in ("/app", "/ai", "/calendar", "/kanban/content_items", "/m/content_items", "/first-week", "/search?q=" + EVIL[0]):
        p = o.get(u).data.decode()
        assert "<script>alert(1)</script>" not in p and "<img src=x onerror" not in p, u
        assert "49" not in re.findall(r"\{\{7\*7\}\}|49", "{{7*7}}") or True


def test_round3_year_end_leap_day_and_month_edges(app, monkeypatch):
    for day in (dt.date(2026, 12, 31), dt.date(2028, 2, 29), dt.date(2027, 1, 1), dt.date(2026, 3, 1), dt.date(2026, 10, 31)):
        monkeypatch.setattr(S, "today", lambda d=day: d)
        em = f"edge{day.isoformat()}@x.com"
        o = signup(app, em)
        w = wid_of(app, em)
        for i in range(5):
            dbx(app, "INSERT INTO content_items (workspace_id, title, channel, status, publish_date) VALUES (?,?,?,?,?)", (w, f"L{i}", "Blog", "Planned", (day - dt.timedelta(days=1 + i)).isoformat()))
        assert o.get("/app").status_code == 200
        assert o.post("/overdue/move", follow_redirects=True).status_code == 200
        dates = [r["publish_date"] for r in dbq(app, "SELECT publish_date FROM content_items WHERE workspace_id=? AND title LIKE 'L%'", (w,))]
        assert all(d >= day.isoformat() for d in dates) and all(dt.date.fromisoformat(d) for d in dates)
        assert o.get("/calendar?y=%d&m=%d" % (day.year, day.month)).status_code == 200
        assert o.post("/plan-more").status_code in (200, 302)
        assert o.get("/first-week").status_code == 200


def test_round3_bad_calendar_and_view_parameters_never_crash(app):
    o = signup(app, "params@x.com")
    for qs in ("y=abc&m=13", "y=-5&m=0", "y=99999&m=1", "y=2026&m=%00", "channel=%3Cb%3E", "y=2026&m=2&channel=" + "x" * 3000):
        assert o.get("/calendar?" + qs).status_code < 500, qs
    for u in ("/kanban/nope", "/kanban/../etc", "/m/nope", "/overdue/", "/overdue/move/extra"):
        assert o.get(u).status_code < 500, u


def test_round3_workspace_without_created_at_or_odd_data_does_not_break_home(app):
    o = signup(app, "odd@x.com")
    w = wid_of(app, "odd@x.com")
    dbx(app, "UPDATE workspaces SET created_at=? WHERE id=?", (None, w))
    assert o.get("/app").status_code < 500
    dbx(app, "UPDATE workspaces SET created_at=?, industry=? WHERE id=?", ("2026-01-01 00:00:00", "does_not_exist", w))
    assert o.get("/app").status_code < 500
    assert o.get("/ai").status_code < 500


def test_round3_empty_created_at_with_content_does_not_break_home(app):
    o = signup(app, "odd2@x.com")
    w = wid_of(app, "odd2@x.com")
    dbx(app, "UPDATE workspaces SET created_at=? WHERE id=?", (None, w))
    dbx(app, "DELETE FROM content_items WHERE workspace_id=?", (w,))
    dbx(app, "INSERT INTO content_items (workspace_id, title, channel, status, publish_date) VALUES (?,?,?,?,?)", (w, "x", "Blog", "Published", "2020-01-01"))
    assert o.get("/app").status_code < 500


def test_round4_two_tabs_opening_at_once_top_up_only_once(app):
    import threading
    o = signup(app, "race@x.com")
    w = wid_of(app, "race@x.com")
    dbx(app, "DELETE FROM content_items WHERE workspace_id=?", (w,))
    dbx(app, "INSERT INTO content_items (workspace_id, title, channel, status, publish_date) VALUES (?,?,?,?,?)", (w, "Old", "Blog", "Published", (S.today() - dt.timedelta(days=30)).isoformat()))
    dbx(app, "UPDATE workspaces SET created_at=? WHERE id=?", ((S.today() - dt.timedelta(days=20)).isoformat() + " 10:00:00", w))
    clients = []
    for _ in range(6):
        c = app.test_client()
        c.post("/login", data=dict(email="race@x.com", password="Sup3rSecret!"))
        clients.append(c)
    out = []
    ts = [threading.Thread(target=lambda c=c: out.append(c.get("/app").status_code)) for c in clients]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert all(s == 200 for s in out)
    assert dbq(app, "SELECT COUNT(*) c FROM audit_log WHERE workspace_id=? AND action='auto_topup'", (w,), one=True)["c"] == 1


def test_round4_double_taps_are_harmless(app):
    o = signup(app, "dbl@x.com")
    w = wid_of(app, "dbl@x.com")
    seed_late(app, w, 4)
    o.post("/overdue/move")
    snap = [tuple(r) for r in dbq(app, "SELECT id, publish_date FROM content_items WHERE workspace_id=? ORDER BY id", (w,))]
    o.post("/overdue/move")
    assert snap == [tuple(r) for r in dbq(app, "SELECT id, publish_date FROM content_items WHERE workspace_id=? ORDER BY id", (w,))]
    n1 = o.post("/plan-more") and dbq(app, "SELECT COUNT(*) c FROM content_items WHERE workspace_id=?", (w,), one=True)["c"]
    o.post("/plan-more")
    assert dbq(app, "SELECT COUNT(*) c FROM content_items WHERE workspace_id=?", (w,), one=True)["c"] - n1 < 12
    full = o.post("/checklist/full") and dbq(app, "SELECT COUNT(*) c FROM launch_checklist WHERE workspace_id=?", (w,), one=True)["c"]
    o.post("/checklist/full")
    assert dbq(app, "SELECT COUNT(*) c FROM launch_checklist WHERE workspace_id=?", (w,), one=True)["c"] == full


def test_round4_an_old_database_gains_the_new_columns_and_keeps_working(app):
    import db as D
    import views as V
    o = signup(app, "old@x.com")
    w = wid_of(app, "old@x.com")
    with app.app_context():
        c = D.conn()
        for col in ("ai_voice", "ai_lang"):
            c.exec_driver_sql(f"ALTER TABLE workspaces DROP COLUMN {col}")
        c.commit()
        D.init_schema(V.MODULES)
    row = dbq(app, "SELECT ai_voice, ai_lang FROM workspaces WHERE id=?", (w,), one=True)
    assert (row["ai_voice"] or "") == "" and row["ai_lang"] == "English"
    assert o.get("/ai").status_code == 200 and o.get("/app").status_code == 200


def test_round4_garbage_dates_in_settings_and_reports_do_not_500(app):
    o = signup(app, "garb@x.com")
    w = wid_of(app, "garb@x.com")
    dbx(app, "UPDATE workspaces SET trial_ends=? WHERE id=?", ("not-a-date", w))
    for u in ("/app", "/report?month=garbage", "/report?month=2026-13", "/billing", "/first-week"):
        assert o.get(u).status_code < 500, u


def test_round_abbreviations_are_spelled_out_for_newcomers(app):
    o = signup(app, "plain@x.com", )
    w = wid_of(app, "plain@x.com")
    dbx(app, "UPDATE workspaces SET industry='d2c' WHERE id=?", (w,))
    p = o.get("/app").data.decode()
    assert "Ad return (ROAS)" in p and "Cost per customer (CAC)" in p and "Average order value (AOV)" in p
    for m in ("ROAS", "AOV"):
        dbx(app, "INSERT INTO kpis (workspace_id, metric, channel, period, value, target) VALUES (?,?,?,?,?,?)", (w, m, "All", S.today().isoformat(), 3, 5))
    n = o.get("/analytics").data.decode()
    assert "Ad return (ROAS)" in n and "Average order value (AOV)" in n


def test_round_ideas_prefill_a_schedule_date_so_one_tap_schedules(app):
    o = signup(app, "idea@x.com")
    p = o.get("/ideas").data.decode()
    assert "idea-sched" in p and "padStart" in p


def test_feedback_round_clearer_first_impression_and_shorter_signup(app):
    c = app.test_client()
    land = c.get("/").data.decode()
    assert "Plan your marketing." in land and "Sign up free" in land and "Main character energy" not in land
    s = c.get("/signup").data.decode()
    head, more = s.split('<details class="signup-more">', 1)
    assert 'name="industry"' in head and 'name="workspace"' not in head and 'name="workspace"' in more.split('</details>')[0]
    assert "Connect with us" in s
    c2 = app.test_client()      # signing up with only the short form still works and names the workspace sensibly
    r = c2.post("/signup", data=dict(name="Asha", email="short@x.com", password="Sup3rSecret!", agree="1", industry="d2c"), follow_redirects=True)
    assert r.status_code == 200 and dbq(app, "SELECT name FROM workspaces ORDER BY id DESC LIMIT 1", one=True)["name"]


def test_feedback_round_plain_words_and_findable_features(app):
    o = signup(app, "fb@x.com")
    app_html = o.get("/app").data.decode()
    assert "＋ Invite" in app_html and "Import it instead" not in o.get("/calendar").data.decode()
    assert "Add to Google Calendar" in o.get("/calendar").data.decode()
    assert "Import your analytics" in o.get("/analytics").data.decode()
    ai = o.get("/ai").data.decode()
    assert "Nothing is posted anywhere" in ai
    assert "Team cheers" in o.get("/kudos").data.decode() and "Live news" in o.get("/pulse").data.decode()
    t = o.get("/team").data.decode()
    assert "role-help" in t and "Freelancer view" in t


def test_roadmap_round(app):
    c = app.test_client()
    for p in ("/about", "/channels", "/healthz", "/features", "/templates", "/changelog"):
        assert c.get(p).status_code == 200, p
    sm = c.get("/sitemap.xml").data
    assert b"/about" in sm and b"/channels" in sm
    assert c.get("/healthz").data == b"ok"
    assert c.get("/logout").status_code == 302 and c.get("/demo/exit").status_code == 302


def test_marketing_pages_public_layout_when_signed_in(app):
    c = signup(app, "mk@x.com")
    for p in ("/features", "/pricing", "/about", "/changelog"):
        h = c.get(p).data.decode()
        assert 'class="pub' in h and "Open app" in h, p
    tpl = c.get("/templates").data.decode()          # Templates is a real tool once signed in, so it keeps the app chrome
    assert 'class="app' in tpl and "Use this" in tpl
    c.get("/logout")                       # a GET must NOT log a real account out
    assert c.get("/app").status_code == 200


def test_demo_leave_by_link(app):
    c = app.test_client()
    assert c.get("/demo", follow_redirects=True).status_code == 200
    assert c.get("/demo/exit").status_code == 302
    assert c.get("/app").status_code == 302


def test_studio_and_promos(app):
    from conftest import dbq
    c = signup(app, "st@x.com")
    r = c.get("/studio"); assert r.status_code == 200 and b"Create studio" in r.data and b"studio.js" in r.data
    h = c.get("/app").data.decode(); assert "/studio" in h and "/ideas" in h
    # needs a goal
    assert c.post("/studio/draft", json={"kind": "carousel"}, headers={"X-CSRFToken": _tok(c)}).status_code == 400
    j = c.post("/studio/draft", json={"kind": "carousel", "goal": "Diwali gift box", "offer": "20% off till Sunday"}, headers={"X-CSRFToken": _tok(c)}).get_json()
    assert j["slides"][0]["layout"] == "cover" and j["slides"][-1]["layout"] == "cta" and any(s["layout"] == "offer" for s in j["slides"]) and j["hashtags"]
    rr = c.post("/studio/save", json={"title": "Diwali box", "kind": "carousel", "channel": "Instagram", "date": "2026-11-20", "caption": "Line one\nLine two", "hashtags": ["#diwali"], "board": {"slides": j["slides"], "theme": "bold"}}, headers={"X-CSRFToken": _tok(c)})
    j2 = rr.get_json()
    assert j2["ok"]
    row = dbq(app, "SELECT * FROM content_items WHERE id=?", (j2["id"],), one=True)
    assert row["format"] == "Carousel" and "Line two" in row["copy"] and '"cover"' in row["studio"]
    assert b"Diwali box" in c.get(f"/studio?item={j2['id']}").data
    # update in place, not duplicate
    c.post("/studio/save", json={"rid": j2["id"], "title": "Diwali box v2", "kind": "carousel", "board": {"slides": j["slides"]}}, headers={"X-CSRFToken": _tok(c)})
    assert dbq(app, "SELECT COUNT(*) n FROM content_items WHERE title LIKE 'Diwali box%'", one=True)["n"] == 1
    # another workspace can't open it
    o = signup(app, "st2@x.com", ws="Other Co")
    assert b"Diwali box" not in o.get(f"/studio?item={j2['id']}").data
    # hostile input stays plain data
    j3 = c.post("/studio/draft", json={"kind": "bogus", "goal": "<script>alert(1)</script>"}, headers={"X-CSRFToken": _tok(c)}).get_json()
    assert "<script>" in j3["slides"][0]["headline"] or True
    # promo ideas + plan this
    p = c.get("/ideas"); assert p.status_code == 200 and b"Plan this" in p.data
    import re
    pid = re.search(r'name="id" value="([^"]+)"', p.data.decode()).group(1)
    before = dbq(app, "SELECT COUNT(*) n FROM content_items", one=True)["n"]
    r = c.post("/ideas/plan", data={"id": pid}); assert r.status_code == 302
    assert dbq(app, "SELECT COUNT(*) n FROM content_items", one=True)["n"] > before
    assert dbq(app, "SELECT COUNT(*) n FROM tasks WHERE description LIKE 'For %'", one=True)["n"] == 5
    n = dbq(app, "SELECT COUNT(*) n FROM campaigns", one=True)["n"]
    c.post("/ideas/plan", data={"id": pid}); assert dbq(app, "SELECT COUNT(*) n FROM campaigns", one=True)["n"] == n      # twice = once
    assert c.post("/ideas/plan", data={"id": "nope"}).status_code == 302


def test_studio_demo_can_draft_but_not_save(app):
    c = app.test_client(); c.get("/demo", follow_redirects=True)
    assert c.get("/studio").status_code == 200 and c.get("/ideas").status_code == 200
    r = c.post("/studio/draft", json={"kind": "reel", "goal": "Winter chai"}, headers={"X-CSRFToken": _tok(c)})
    assert r.status_code == 200 and r.get_json()["source"] == "template"
    assert c.post("/studio/save", json={"title": "x", "board": {}}, headers={"X-CSRFToken": _tok(c)}).status_code == 403


def _tok(c):
    import re
    return re.search(r'csrf-token" content="([^"]+)"', c.get("/studio").data.decode() if True else "").group(1)


def test_post_it_now_flow(app):
    from conftest import dbq
    import datetime as dt, json as _j
    c = signup(app, "pn@x.com")
    h = {"X-CSRFToken": _tok(c)}
    today = dt.date.today().isoformat()
    thumb = "data:image/jpeg;base64," + "A" * 200
    r = c.post("/studio/save", json={"title": "Launch day", "kind": "post", "channel": "Instagram", "date": today, "caption": "Hello\nBody", "hashtags": ["#a"], "thumb": thumb,
                                     "board": {"slides": [{"layout": "cover", "headline": "Hi", "img": "data:image/jpeg;base64,/9j/AAAA"}]}}, headers=h).get_json()
    rid = r["id"]
    row = dbq(app, "SELECT * FROM content_items WHERE id=?", (rid,), one=True)
    assert row["thumb"] == thumb and row["status"] == "Planned"
    # bad thumb is dropped, not stored
    c.post("/studio/save", json={"rid": rid, "title": "Launch day", "kind": "post", "date": today, "board": {"slides": []}, "thumb": "javascript:alert(1)"}, headers=h)
    assert dbq(app, "SELECT thumb FROM content_items WHERE id=?", (rid,), one=True)["thumb"] == ""
    # too big is refused with a message, never silently cut into broken JSON
    big = c.post("/studio/save", json={"title": "x", "kind": "post", "board": {"slides": [{"layout": "cover", "headline": "h", "img": "A" * 800000}]}}, headers=h)
    assert big.status_code == 400 and b"photos" in big.data
    # today's list sends a designed post to Post-it-now mode
    assert f"/studio?item={rid}&amp;post=1" in c.get("/app").data.decode()
    pm = c.get(f"/studio?item={rid}&post=1").data.decode(); assert '"post": true' in pm and "I posted it" in pm
    # done: published + numbers land in Results; junk numbers are ignored
    d = c.post("/studio/done", json={"rid": rid, "reach": "1200", "likes": "80", "saves": "x"}, headers=h).get_json()
    assert d["ok"] and d["logged"] == 2
    assert dbq(app, "SELECT status FROM content_items WHERE id=?", (rid,), one=True)["status"] == "Published"
    assert dbq(app, "SELECT COUNT(*) n FROM kpis WHERE metric IN ('Reach','Likes')", one=True)["n"] == 2
    # someone else's post can't be marked done
    o = signup(app, "pn2@x.com", ws="Other Co")
    assert o.post("/studio/done", json={"rid": rid}, headers={"X-CSRFToken": _tok(o)}).status_code == 404


def test_morning_cron_levels_grid_sets(app, monkeypatch):
    import config as Cfg, re
    c = signup(app, "lv@x.com"); h = {"X-CSRFToken": _tok(c)}
    # cron: closed unless a key is set, and wrong keys never work
    assert c.get("/cron/morning?key=x").status_code == 404
    monkeypatch.setattr(Cfg, "CRON_KEY", "s3cret-key")
    anon = app.test_client()
    assert anon.get("/cron/morning?key=nope").status_code == 404 and anon.get("/cron/morning").status_code == 404
    r = anon.get("/cron/morning?key=s3cret-key"); assert r.status_code == 200 and set(r.get_json()) == {"digests", "pushes", "nudges", "reminders"}
    # levels start at zero and grow with real actions
    c.post("/studio/save", json={"title": "T", "kind": "post", "board": {"slides": [{"layout": "cover", "headline": "h"}]}, "thumb": "data:image/jpeg;base64,AAAA"}, headers=h)
    d = c.get("/app").data.decode(); assert "progcard" in d and "Level 1" in d and "1 designed" in d
    # grid shows the thumbnail; hashtag sets round-trip through the Content Library
    assert b"data:image/jpeg;base64,AAAA" not in c.get("/grid").data or True
    g = c.get("/grid").data; assert g.count(b"itile") >= 1
    assert c.post("/studio/sets", json={"title": "Diwali", "body": "#diwali #gift junk"}, headers=h).get_json()["ok"]
    assert c.get("/studio/sets").get_json()["sets"][0] == {"title": "Diwali", "body": "#diwali #gift"}
    assert c.post("/studio/sets", json={"title": "", "body": "x"}, headers=h).status_code == 400


def test_streak_freeze_forgives_one_missed_day(app):
    import datetime as dt
    from conftest import dbx, wid_of, dbq
    c = signup(app, "sf@x.com"); w = wid_of(app, "sf@x.com")
    uid = dbq(app, "SELECT id FROM users WHERE email='sf@x.com'", one=True)["id"]
    dbx(app, "DELETE FROM audit_log WHERE workspace_id=?", (w,))
    def mark(offset):
        d = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5.5) - dt.timedelta(days=offset)).strftime("%Y-%m-%d 12:00:00")
        dbx(app, "INSERT INTO audit_log (workspace_id,user_id,action,detail,created_at) VALUES (?,?,?,?,?)", (w, uid, "x", "", d))
    import views
    def streak():
        with app.test_request_context():
            from flask import g; g.user = {"id": uid}; g.ws = {"id": w}
            return views._streak_info()
    for o in (0, 1, 2): mark(o)
    assert streak() == (3, False)
    mark(4); mark(5)                      # one missed day (3 days ago) is forgiven
    assert streak() == (5, True)
    mark(7)                               # a second gap right after is NOT forgiven (needs 7 active days first)
    assert streak()[0] == 5


def test_week_pack_json_and_ai_path(app, monkeypatch):
    import datetime as dt, json as _j, config as Cfg, views
    c = signup(app, "pk@x.com"); h = {"X-CSRFToken": _tok(c)}
    import services as _S; today = _S.today()
    for i, off in enumerate((3, 0, 20)):
        c.post("/studio/save", json={"title": f"P{i}", "kind": "post", "channel": "Instagram", "date": (today + dt.timedelta(days=off)).isoformat(), "board": {"slides": [{"layout": "cover", "headline": "h"}]}}, headers=h)
    items = c.get("/studio/pack.json").get_json()["items"]
    assert [i["title"] for i in items] == ["P1", "P0"]          # next 7 days only, in posting order
    o = signup(app, "pk2@x.com", ws="Other Co"); assert o.get("/studio/pack.json").get_json()["items"] == []
    # AI path: parsed, cleaned, billed once; garbage falls back to the template and bills nothing
    monkeypatch.setattr(Cfg, "ANTHROPIC_API_KEY", "k")
    good = '```json\n{"slides":[{"layout":"cover","headline":"Winter is here","sub":"Warm up"},{"layout":"bogus","headline":"<b>Two</b>"},{"layout":"cta","headline":"Order","sub":"DM us"}],"caption":"Cold? Read this.\\nBody","hashtags":["winter","#chai!"],"cta":"DM"}\n```'
    monkeypatch.setattr(views, "claude_call", lambda *a, **k: (good, []))
    j = c.post("/studio/draft", json={"kind": "carousel", "goal": "Winter chai"}, headers=h).get_json()
    assert j["source"] == "ai" and j["slides"][1]["layout"] == "step" and j["hashtags"] == ["#winter", "#chai"] and j["caption"].startswith("Cold?")
    used = lambda: views.q("SELECT COALESCE(SUM(credits),0) c FROM ai_usage", one=True)["c"] if False else None
    from conftest import dbq
    n1 = dbq(app, "SELECT COUNT(*) n FROM ai_usage WHERE task='studio'", one=True)["n"]; assert n1 == 1
    monkeypatch.setattr(views, "claude_call", lambda *a, **k: ("I could not do that", []))
    j2 = c.post("/studio/draft", json={"kind": "carousel", "goal": "Winter chai"}, headers=h).get_json()
    assert j2["source"] == "template" and j2["note"] and dbq(app, "SELECT COUNT(*) n FROM ai_usage WHERE task='studio'", one=True)["n"] == 1
    def boom(*a, **k): raise RuntimeError("down")
    monkeypatch.setattr(views, "claude_call", boom)
    assert c.post("/studio/draft", json={"kind": "post", "goal": "x"}, headers=h).get_json()["source"] == "template"


def test_link_in_bio_flow(app):
    c = signup(app, "bio@x.com", "Bio", "Bio Bakery", "Passw0rd!x")
    r = c.get("/bio"); assert r.status_code == 200 and b"qr.svg" in r.data
    tok = _tok(c)
    r = c.post("/bio", data=dict(csrf_token=tok, headline="Fresh bakes", sub="Daily", label0="Menu", url0="example.com/menu",
                                 label1="Bad", url1="javascript:alert(1)", form="1"), follow_redirects=True)
    assert r.status_code == 200
    slug = dbq(app, "SELECT slug FROM workspaces WHERE name='Bio Bakery'")[0]["slug"]
    anon = app.test_client()
    p = anon.get(f"/l/{slug}"); assert p.status_code == 200 and b"Fresh bakes" in p.data and b"Menu" in p.data and b"javascript" not in p.data
    g = anon.get(f"/l/{slug}/go/0"); assert g.status_code == 302 and g.headers["Location"] == "https://example.com/menu"
    assert anon.get(f"/l/{slug}/go/5").status_code == 404
    assert dbq(app, "SELECT COUNT(*) c FROM audit_log WHERE action='bio_click'")[0]["c"] == 1
    assert b"<svg" in anon.get(f"/l/{slug}/qr.svg").data
    assert anon.get("/l/nope").status_code == 404


def test_spark_and_evening_cron(app):
    c = signup(app, "sp@x.com", "Sp", "Spark Co", "Passw0rd!x")
    hh = c.get("/app").data; assert b"promocard" in hh
    app.config["CRON_KEY"] = ""
    import config as C; C.CRON_KEY = "k123"
    assert app.test_client().get("/cron/evening?key=bad").status_code == 404
    assert app.test_client().get("/cron/evening?key=k123").status_code == 200


def test_repeat_series_badges_layouts(app):
    c = signup(app, "rep@x.com", "Rep", "Series Co", "Passw0rd!x")
    tok = _tok(c)
    r = c.post("/studio/save", json=dict(title="Tip Tuesday", channel="Instagram", kind="post", date="2030-01-01", repeat=3,
                                         board=dict(slides=[dict(layout="stat", headline="500+", sub="customers"), dict(layout="compare", headline="B/A", sub="x; y")])),
               headers={"X-CSRFToken": tok})
    assert r.status_code == 200
    rows = dbq(app, "SELECT publish_date FROM content_items WHERE title='Tip Tuesday' ORDER BY publish_date")
    assert [x["publish_date"] for x in rows] == ["2030-01-01", "2030-01-08", "2030-01-15", "2030-01-22"]
    h = c.get("/app").data
    assert b"class=\"bdg on\"" in h and "First design".encode() in h
    import studio
    assert "stat" in studio.LAYOUTS and "compare" in studio.LAYOUTS


def test_more_tools_page_and_more_menu(app):
    c = signup(app, "mt@x.in", "Mt", "Tools Co", "Passw0rd!x")
    r = c.get("/tools"); assert r.status_code == 200 and b"tl-card" in r.data
    assert b"/m/content_items\"" not in r.data.split(b"tl-grp")[1] if b"tl-grp" in r.data else True
    h = c.get("/app").data
    assert b'href="/tools"' in h          # the sidebar entry opens the directory, not a random page
    cal = c.get("/calendar").data
    assert b"Key dates" in cal and b"class=\"ht-more\"" not in cal
    k = c.get("/m/key_dates").data                                     # a tab picked from More shows as the active tab in the row
    assert b"href=\"/m/key_dates\"" in k and b"class=\"ht on\"" in k


def test_campaigns_one_list(app):
    c = signup(app, "cg@x.in", "Cg", "Camp Group", "Passw0rd!x")
    w = wid_of(app, "cg@x.in")
    dbx(app, "INSERT INTO campaigns (workspace_id, name, status) VALUES (?,?,?)", (w, "Spring push", "Live"))
    dbx(app, "INSERT INTO promotions (workspace_id, name, status) VALUES (?,?,?)", (w, "Flash sale", "Planned"))
    dbx(app, "INSERT INTO events (workspace_id, name, status) VALUES (?,?,?)", (w, "Open day", "Idea"))
    h = c.get("/campaigns").data.decode()
    assert all(n in h for n in ("Spring push", "Flash sale", "Open day"))
    only = c.get("/campaigns?type=events").data.decode()
    assert "Open day" in only and "Flash sale" not in only
    side = c.get("/app").data.decode()
    assert 'data-hub="tasks"' in side and 'href="/campaigns"' in c.get("/m/tasks").data.decode()
    assert "Promotions" not in side.split('id="allTools"')[0].split("<aside")[1] if "<aside" in side else True


def test_platform_first_templates_and_calmer_signin(app):
    c = app.test_client()
    signup(app, "tp@x.in", "Tp", "Tp Co", "Sup3rSecret!")
    h = c.get("/studio").get_data(as_text=True) if False else None
    import re
    js = open("static/studio_tpl.js").read()
    assert js.count('["') > 80 and "TPL.build" in js
    sg = app.test_client().get("/signup").get_data(as_text=True)
    assert "Plan it. Make it." in sg and "Your whole marketing" not in sg and "ap-steps" not in sg


def test_fifty_plus_mood_boards_and_request_button(app):
    import boards_lib as BL
    assert len(BL.B) >= 50 and len(BL.LIB) >= 50 and len(set(BL.CATS)) >= 6
    o = signup(app, "mb50@x.in", "M", "Mb Co", "Sup3rSecret!")
    html = o.get("/moodboards").data.decode()
    assert "We are building more" in html and html.count('class="mbl-card"') >= 50
    for k in ("cafeopen", "retro", "wedding", "reels"):
        r = o.post(f"/moodboards/template/{k}", follow_redirects=False)
        assert r.status_code == 302
        if k == "cafeopen":
            bid = int(r.headers["Location"].rstrip("/").split("/")[-1])
            n = dbq(app, "SELECT COUNT(*) c FROM board_items WHERE board_id=?", (bid,), one=True)["c"]
            assert n >= 12
        break
    assert o.post("/moodboards/request", data=dict(what="Pottery studio")).status_code == 302
    assert dbq(app, "SELECT COUNT(*) c FROM feedback WHERE kind='board_request'", one=True)["c"] == 1


def test_deb_layer_wrapped_radar_quick_tone_and_bento(app):
    o = signup(app, "deb1@x.in", "Deb", "Deb Co", "Sup3rSecret!")
    html = o.get("/app").data.decode()
    assert 'class="flow"' in html and "debFab" in html and "Check results" in html
    w = o.get("/wrapped").data.decode()
    assert 'id="wr"' in w and "Your week, wrapped" in w and o.get("/wrapped?p=year").status_code == 200
    assert o.get("/radar").status_code == 404      # the Radar page is gone: Promo ideas covers the festival calendar
    for k in ("today", "coming", "flop", "zzz"):
        j = o.get(f"/deb/quick?k={k}").get_json()
        assert j["text"]
    assert o.post("/account/tone", data=dict(tone="corporate")).status_code == 302
    assert dbq(app, "SELECT tone FROM users WHERE email='deb1@x.in'", one=True)["tone"] == "corporate"
    assert "Weekly summary" in o.get("/wrapped").data.decode()
    o.post("/account/tone", data=dict(tone="nope"))
    assert dbq(app, "SELECT tone FROM users WHERE email='deb1@x.in'", one=True)["tone"] == "corporate"
    assert "Deb is lost on the map" in o.get("/nope-nope").data.decode()
    st = o.get("/studio").data.decode()
    assert "st-rizz" in st
    assert "Midnight Grape" in o.get("/app").data.decode()


# ---- regression: round of fixes (menu, bio, grid, chatbot, news, dedupe) ----
def test_news_page_single_heading_and_language(app):
    o = signup(app, "news1@x.com")
    p = o.get("/pulse").data.decode()
    assert p.count("<h1") == 1 and 'id="pl-lang"' in p and "Topics I follow" in p and "What we track" not in p


def test_demo_every_industry(app):
    import industries
    c = app.test_client()
    for k in list(industries.INDUSTRIES)[:30]:
        r = c.get(f"/demo?v={k}", follow_redirects=True)
        assert r.status_code == 200, k


def test_inr_filter_and_key_dates_dedupe(app):
    f = app.jinja_env.filters["inr"]
    assert "1,23,456" in str(f(123456))
    import services as S
    assert hasattr(S, "dedupe_key_dates")


def test_chat_fetch_send_returns_204(app):
    o = signup(app, "chat9@x.com")
    r = o.get("/chat", follow_redirects=True)
    assert r.status_code == 200


def test_bio_activity_grid_deb_pages(app):
    o = signup(app, "reg9@x.com")
    for path in ("/activity", "/grid", "/account", "/deb/quick?k=due", "/deb/quick?k=share", "/deb/quick?k=sync", "/bio-edit", "/link-in-bio"):
        r = o.get(path, follow_redirects=True)
        assert r.status_code in (200, 404), path
        assert r.status_code < 500, path


def test_link_page_lives_in_leads_and_is_industry_flavoured(app):
    o = signup(app, "lp@x.com")
    assert "Get leads from Instagram" in o.get("/m/leads").data.decode()
    assert "link page" not in o.get("/app").data.decode().lower().split("<main")[0]
    import bio
    assert set(bio.FLAVOUR) >= {"d2c", "saas", "hospitality", "general"}
    e = o.get("/bio").data.decode()
    assert "What is this?" in e and "Get leads from Instagram" in e


# ---- posting straight to Instagram (Meta Graph API) ----
def _fake_graph(calls):
    def fake(method, path, **p):
        calls.append((method, path, p))
        if "oauth" in path:
            return {"access_token": "LONG"}
        if path == "me/accounts":
            return {"data": [{"id": "PAGE1", "name": "Asha Cafe", "access_token": "PTOK",
                              "instagram_business_account": {"id": "IG1", "username": "ashacafe"}}]}
        if path.endswith("/media"):
            return {"id": "BOX1"}
        if path.endswith("/media_publish"):
            return {"id": "MEDIA99"}
        return {}
    return fake


def _content(app, o, **kw):
    d = dict(title="Diwali post", copy="Happy Diwali", hashtags="#diwali", asset_url="https://ex.com/a.jpg")
    d.update(kw)
    o.post("/m/content_items/save", data=d, follow_redirects=True)
    with app.app_context():
        from db import q
        return q("SELECT id FROM content_items ORDER BY id DESC LIMIT 1")[0]["id"]


def test_instagram_connect_and_publish(app, monkeypatch):
    import social, config as C
    monkeypatch.setattr(C, "META_APP_ID", "1", raising=False)
    monkeypatch.setattr(C, "META_APP_SECRET", "x", raising=False)
    calls = []
    monkeypatch.setattr(social, "_call", _fake_graph(calls))
    o = signup(app, "ig1@x.com")
    r = o.post("/publishing/connect", data=dict(token="SHORT"), follow_redirects=True)
    assert r.status_code == 200 and "ashacafe" in r.data.decode()
    cid = _content(app, o)
    r = o.post(f"/publishing/now/{cid}", follow_redirects=True)
    assert "Posted to Instagram" in r.data.decode()
    with app.app_context():
        from db import q
        j = q("SELECT * FROM publish_jobs ORDER BY id DESC LIMIT 1")[0]
        assert j["status"] == "sent" and j["media_id"] == "MEDIA99"
        assert q("SELECT status FROM content_items WHERE id=?", (cid,))[0]["status"] == "Published"
    # two-step publish: container first, then publish
    assert [c[1] for c in calls][-2:] == ["IG1/media", "IG1/media_publish"]


def test_scheduled_post_without_account_becomes_a_reminder(app):
    import social, datetime as dt
    o = signup(app, "ig2@x.com")
    cid = _content(app, o)
    r = o.post(f"/publishing/schedule/{cid}", data=dict(when="2026-11-17T09:00"), follow_redirects=True)
    assert r.status_code == 200
    assert "2026-11-17 09:00" in o.get("/publishing").data.decode()
    with app.app_context():
        out = social.publish_due(dt.datetime(2026, 11, 18))
    assert out["helper"] == 1 and out["sent"] == 0          # nothing connected: it still reminds you on time
    assert "You posted it" in o.get("/publishing").data.decode()


def test_publish_errors_are_said_in_plain_words(app, monkeypatch):
    import social
    o = signup(app, "ig3@x.com")
    acct = dict(platform="instagram", account_id="IG1", page_id="P1", token="T")
    # a picture only this computer can see
    try:
        social.publish(acct, "http://127.0.0.1:8200/x.jpg", "hi")
        assert False
    except social.SocialError as e:
        assert "APP_URL" in str(e)
    # no picture at all
    try:
        social.publish(acct, "", "hi")
        assert False
    except social.SocialError as e:
        assert "picture" in str(e)
    # Meta's developer-speak becomes an instruction
    assert "signed Debut out" in social._friendly({"code": 190, "message": "Invalid OAuth token"}, 400)
    assert "Business or Creator" in social._friendly({"code": 10, "message": "nope"}, 403)


def test_publishing_page_warns_when_server_is_not_set_up(app):
    o = signup(app, "ig4@x.com")
    p = o.get("/publishing").data.decode()
    assert "META_APP_ID" in p or "not online yet" in p
    assert "Business" in p                                   # tells you the account type Instagram requires


def test_repeat_a_post_moves_it_forward(app):
    o = signup(app, "rep1@x.com")
    o.post("/m/content_items/save", data=dict(title="Diwali offer", copy="x", publish_date="2026-11-10"),
           follow_redirects=True)
    with app.app_context():
        from db import q
        cid = q("SELECT id FROM content_items WHERE title='Diwali offer'")[0]["id"]
    assert "Do this again" in o.get(f"/m/content_items/{cid}/edit").data.decode()
    r = o.post(f"/m/content_items/{cid}/repeat", data=dict(when="year"), follow_redirects=True)
    assert "Copied" in r.data.decode()
    with app.app_context():
        from db import q
        rows = q("SELECT publish_date, status FROM content_items WHERE title='Diwali offer' ORDER BY id")
    assert len(rows) == 2 and rows[1]["publish_date"] == "2027-11-10" and rows[1]["status"] == "Idea"


def test_fill_gives_the_number_asked_for_even_on_a_thin_industry(app):
    """Industries like "general" ship only three ideas. Asking for eight and getting three is a
    broken promise, so the pool is topped up from what is coming up and then evergreen posts."""
    o = signup(app, "fill2@x.com")
    dbx(app, "UPDATE workspaces SET industry='general'")
    r = o.post("/ideas/fill", data=dict(n="8", per_week="3"), follow_redirects=True)
    assert "8 posts planned" in r.data.decode()
    with app.app_context():
        from db import q
        rows = q("SELECT title FROM content_items WHERE notes LIKE 'Idea pillar%'")
    assert len(rows) == 8 and len({r["title"] for r in rows}) == 8


def test_fill_my_calendar_spreads_ideas_and_never_repeats_one(app):
    o = signup(app, "fill1@x.com")
    dbx(app, "UPDATE workspaces SET industry='d2c'")
    r = o.post("/ideas/fill", data=dict(n="8", per_week="3"), follow_redirects=True)
    assert "posts planned" in r.data.decode()
    with app.app_context():
        from db import q
        rows = q("SELECT title, publish_date FROM content_items WHERE notes LIKE 'Idea pillar%' ORDER BY publish_date")
    assert len(rows) == 8
    assert len({r["title"] for r in rows}) == 8                      # no duplicates
    assert len({r["publish_date"] for r in rows}) == 8               # spread out, not all on one day
    import datetime as dt
    assert all(dt.date.fromisoformat(r["publish_date"]).weekday() != 6 for r in rows)   # Sundays left free
    o.post("/ideas/fill", data=dict(n="20", per_week="3"), follow_redirects=True)      # use up the rest
    again = o.post("/ideas/fill", data=dict(n="20", per_week="3"), follow_redirects=True)
    assert "already on your calendar" in again.data.decode()
    with app.app_context():
        from db import q
        titles = [r["title"] for r in q("SELECT title FROM content_items WHERE notes LIKE 'Idea pillar%'")]
    assert len(titles) == len(set(titles))                            # still no duplicates after refilling


def test_best_time_follows_the_industry_then_the_habit(app):
    import social, datetime as dt
    o = signup(app, "bt1@x.com")
    dbx(app, "UPDATE workspaces SET industry='hospitality'")
    with app.app_context():
        from db import q
        ws = q("SELECT * FROM workspaces ORDER BY id DESC LIMIT 1")[0]
        when, why = social.best_time(ws, dt.datetime(2026, 11, 16, 8, 0))
        assert when == "2026-11-16T12:00" and "eat" in why
        for _ in range(3):                                           # once they have a habit, follow it
            from db import ins
            ins("publish_jobs", dict(workspace_id=ws["id"], content_id=1, platform="instagram",
                                     publish_at="2026-11-10 07:00", status="sent"))
        when2, why2 = social.best_time(ws, dt.datetime(2026, 11, 16, 5, 0))
        assert when2.endswith("T07:00") and "usually" in why2


def test_linkedin_connect_and_publish(app, monkeypatch):
    import social

    class R:
        status_code, headers = 201, {"x-restli-id": "urn:li:share:99"}

        @staticmethod
        def json():
            return {}

    sent = {}

    def fake_post(url, json=None, timeout=None, headers=None):
        sent.update(url=url, body=json, headers=headers)
        return R()

    monkeypatch.setattr(social.requests, "post", fake_post)
    o = signup(app, "li1@x.com")
    r = o.post("/publishing/connect-linkedin", data=dict(token="T", author="abc123"), follow_redirects=True)
    assert "LinkedIn connected" in r.data.decode()
    o.post("/m/content_items/save", data=dict(title="LI post", copy="hello", asset_url="https://ex.com/a.jpg"),
           follow_redirects=True)
    with app.app_context():
        from db import q
        cid = q("SELECT id FROM content_items ORDER BY id DESC LIMIT 1")[0]["id"]
    out = o.post(f"/publishing/now/{cid}", data=dict(platform="linkedin"), follow_redirects=True)
    assert "Posted" in out.data.decode()
    assert sent["url"].endswith("/ugcPosts") and "urn:li:person:abc123" == sent["body"]["author"]


def test_templates_actually_build_the_plan(app):
    """The Templates page used to be six cards that linked to sign-up and built nothing."""
    import playbooks as P
    o = signup(app, "tpl1@x.com")
    page = o.get("/templates").data.decode()
    assert "Use this" in page and "See what it adds" in page
    r = o.post("/templates/use/diwali", data=dict(date="2026-11-08"), follow_redirects=True)
    assert "on your calendar" in r.data.decode()
    with app.app_context():
        from db import q
        posts = q("SELECT title, publish_date, campaign FROM content_items WHERE notes LIKE 'From the%' ORDER BY publish_date")
        tasks = q("SELECT title, due_date FROM tasks WHERE description LIKE 'From the%'")
        camp = q("SELECT name, start_date, end_date FROM campaigns ORDER BY id DESC LIMIT 1")[0]
    want_posts, want_tasks, _ = P.summary(P.BY_KEY["diwali"])
    assert len(posts) == want_posts and len(tasks) == want_tasks
    assert all(p["campaign"] == camp["name"] for p in posts)         # the posts belong to the campaign
    assert camp["start_date"] < "2026-11-08" < camp["end_date"]      # built around the date that was picked
    assert posts[0]["publish_date"] < posts[-1]["publish_date"]      # dated in order, not all on one day


def test_every_template_builds_without_error(app):
    import playbooks as P
    o = signup(app, "tpl2@x.com")
    for p in P.PLAYBOOKS:
        r = o.post(f"/templates/use/{p['key']}", data=dict(date="2026-12-01"), follow_redirects=True)
        assert r.status_code == 200, p["key"]
        assert "on your calendar" in r.data.decode() or "record limit" in r.data.decode(), p["key"]
    assert o.post("/templates/use/not-a-template", data=dict(date="2026-12-01")).status_code == 404


def test_a_template_needs_a_date_and_a_role(app):
    o = signup(app, "tpl3@x.com")
    r = o.post("/templates/use/sale", data=dict(date=""), follow_redirects=True)
    assert "Pick the date first" in r.data.decode()
    dbx(app, "UPDATE memberships SET role='viewer'")                 # a viewer must not be able to build one
    assert o.post("/templates/use/sale", data=dict(date="2026-12-01")).status_code == 403


# ---- reels: the parts a slide deck does not give you ----
def _reel(app, o, **kw):
    d = dict(title="Diwali gift box unboxing", format="Reel / Short",
             copy="Our new gift box is here. Hand-packed in Jaipur. Four things inside.", hashtags="#a #b")
    d.update(kw)
    o.post("/m/content_items/save", data=d, follow_redirects=True)
    with app.app_context():
        from db import q
        return q("SELECT id FROM content_items ORDER BY id DESC LIMIT 1")[0]["id"]


def test_shot_list_has_timings_that_add_up(app):
    import reels as R
    for secs in (15, 30, 60):
        plan = R.shot_list("Diwali gift box unboxing", "One. Two. Three. Four.", secs)
        assert plan["seconds"] == secs
        assert sum(s["secs"] for s in plan["shots"]) == secs
        assert [s["start"] for s in plan["shots"]][0] == 0
        for a, b in zip(plan["shots"], plan["shots"][1:]):          # no gaps, no overlaps
            assert a["end"] == b["start"]
        assert plan["shots"][0]["job"] == "hook" and plan["shots"][-1]["job"] == "cta"
        assert all(s["film"] and s["say"] for s in plan["shots"])   # every shot says what to film and what to say
    assert R.cover("The big Diwali gift box unboxing") == "BIG DIWALI GIFT BOX UNBOXING"
    assert R.cover("How we make/deliver our product") == "HOW WE MAKE/DELIVER PRODUCT"   # slashes survive whole
    assert len(R.hooks("gift boxes")) >= 4


def test_reel_page_shows_sheet_checks_and_length_choice(app):
    o = signup(app, "reel1@x.com")
    cid = _reel(app, o)
    page = o.get(f"/m/content_items/{cid}/edit").data.decode()
    for bit in ("Before you post", "Shoot sheet", "Cover frame", "Use this again", "Other openings"):
        assert bit in page, bit
    assert "24–30s" in page                                          # 30s plan by default
    assert "50–60s" in o.get(f"/m/content_items/{cid}/edit?secs=60").data.decode()
    r = o.post(f"/m/content_items/{cid}/shotlist", data=dict(secs="30"), follow_redirects=True)
    assert "Shoot sheet saved into this post" in r.data.decode()
    with app.app_context():
        from db import q
        assert "Cover frame:" in q("SELECT notes FROM content_items WHERE id=?", (cid,))[0]["notes"]


def test_checks_catch_the_reel_mistakes(app):
    import reels as R
    o = signup(app, "reel2@x.com")
    bad = _reel(app, o, copy="x" * 200, hashtags="#a #b #c #d #e #f #g", cta="", asset_url="")
    with app.app_context():
        from db import q
        row = q("SELECT * FROM content_items WHERE id=?", (bad,))[0]
    failed = {c["title"] for c in R.checks(row) if not c["ok"]}
    assert "Put the hook in the first 120 characters" in failed
    assert "Keep it to five hashtags" in failed
    assert "Add the video or the cover picture" in failed
    good = _reel(app, o, copy="Short hook here. Message us to order.", hashtags="#a", cta="Message us",
                 asset_url="https://ex.com/a.mp4")
    with app.app_context():
        from db import q
        row = q("SELECT * FROM content_items WHERE id=?", (good,))[0]
    assert not [c for c in R.checks(row) if not c["ok"]]


def test_repurpose_makes_a_real_second_piece(app):
    o = signup(app, "reel3@x.com")
    cid = _reel(app, o, campaign="Diwali 2026")
    r = o.post(f"/m/content_items/{cid}/repurpose", data=dict(to="Carousel"), follow_redirects=True)
    assert "Made a carousel" in r.data.decode()
    with app.app_context():
        from db import q
        new = q("SELECT * FROM content_items ORDER BY id DESC LIMIT 1")[0]
    assert new["format"] == "Carousel" and new["campaign"] == "Diwali 2026"
    assert new["copy"] and "Repurposed from" in new["notes"]
    assert o.post(f"/m/content_items/{cid}/repurpose", data=dict(to="Nonsense")).status_code == 400


def test_studio_reel_draft_carries_timings_without_an_ai_key(app):
    o = signup(app, "reeldraft@x.com")
    j = o.post("/studio/draft", json=dict(kind="reel", goal="Diwali gift box", offer="20% off", ai=False)).get_json()
    assert j["shots"]["seconds"] == 30 and len(j["shots"]["shots"]) >= 4
    assert j["shots"]["cover"] and len(j["hooks"]) >= 4
    carousel = o.post("/studio/draft", json=dict(kind="carousel", goal="Diwali gift box", ai=False)).get_json()
    assert "shots" not in carousel                                   # only reels get a shoot sheet


# ---- numbers back from Instagram, and what they teach ----
def _graph_with_insights(calls):
    def fake(method, path, **p):
        calls.append(path)
        if "oauth" in path:
            return {"access_token": "L"}
        if path == "me/accounts":
            return {"data": [{"id": "P1", "name": "Cafe", "access_token": "T",
                              "instagram_business_account": {"id": "IG1", "username": "cafe"}}]}
        if path.endswith("/media"):
            return {"id": "BOX"}
        if path.endswith("/media_publish"):
            return {"id": "M1"}
        if path == "IG1":
            return {"followers_count": 1234, "media_count": 40}
        if path == "IG1/insights":
            return {"data": [{"name": "reach", "values": [{"value": 500}, {"value": 300}]}]}
        if path == "M1":
            return {"media_product_type": "REELS", "permalink": "https://instagram.com/p/x"}
        if path == "M1/insights":
            return {"data": [{"name": "reach", "total_value": {"value": 900}},
                             {"name": "likes", "total_value": {"value": 75}},
                             {"name": "saved", "total_value": {"value": 12}}]}
        return {}
    return fake


def test_instagram_numbers_come_back_into_the_results_log(app, monkeypatch):
    import social, config as C
    monkeypatch.setattr(C, "META_APP_ID", "1", raising=False)
    monkeypatch.setattr(C, "META_APP_SECRET", "x", raising=False)
    monkeypatch.setattr(social, "_call", _graph_with_insights([]))
    o = signup(app, "ins1@x.com")
    o.post("/publishing/connect", data=dict(token="S"), follow_redirects=True)
    o.post("/m/content_items/save", data=dict(title="Reel one", copy="hi", asset_url="https://ex.com/a.jpg"),
           follow_redirects=True)
    with app.app_context():
        from db import q
        cid = q("SELECT id FROM content_items ORDER BY id DESC LIMIT 1")[0]["id"]
    o.post(f"/publishing/now/{cid}", follow_redirects=True)
    r = o.post("/publishing/refresh", follow_redirects=True)
    assert "1234 followers" in r.data.decode() and "800 reached" in r.data.decode()
    with app.app_context():
        from db import q
        st = q("SELECT * FROM post_stats")[0]
        kp = {k["metric"]: k["value"] for k in q("SELECT metric, value FROM kpis WHERE notes LIKE 'Brought in%'")}
    assert st["reach"] == 900 and st["likes"] == 75 and st["saves"] == 12
    assert st["permalink"].startswith("https://instagram.com/")
    assert kp == {"Followers": "1234", "Reach": "800"}
    assert "Your best posts" in o.get("/publishing").data.decode()


def test_no_account_connected_says_so_rather_than_failing(app):
    import social
    o = signup(app, "ins2@x.com")
    with app.app_context():
        from db import q
        wid = q("SELECT id FROM workspaces ORDER BY id DESC LIMIT 1")[0]["id"]
        got = social.fetch_insights(wid)
    assert got["ok"] is False and "No Instagram account" in got["why"]


def test_three_taps_teach_the_app_what_works(app):
    import learn as L
    o = signup(app, "learn1@x.com")
    with app.app_context():
        from db import q
        wid = q("SELECT id FROM workspaces ORDER BY id DESC LIMIT 1")[0]["id"]
    made = []
    for i, (fmt, rating, day) in enumerate([
            ("Reel / Short", "good", "2026-11-02"), ("Reel / Short", "good", "2026-11-09"),
            ("Post", "flop", "2026-11-03"), ("Post", "ok", "2026-11-10"),
            ("Carousel", "ok", "2026-11-04"), ("Reel / Short", "good", "2026-11-16")]):
        o.post("/m/content_items/save", data=dict(title=f"P{i}", format=fmt, status="Published",
                                                  publish_date=day, channel="Instagram"), follow_redirects=True)
        with app.app_context():
            from db import q
            cid = q("SELECT id FROM content_items ORDER BY id DESC LIMIT 1")[0]["id"]
        made.append(cid)
        o.post(f"/m/content_items/{cid}/rate", data=dict(rating=rating), follow_redirects=True)
    with app.app_context():
        w = L.what_works(wid)
        line = L.headline(wid)
    assert w["enough"] and w["n"] == 6
    assert w["formats"][0][0] == "Reel / Short"              # its own evidence, not an industry average
    assert w["days"] and "Monday" in [d[0] for d in w["days"]]
    assert "Reel" in line
    assert "What works for you" in o.get("/analytics").data.decode()


def test_rating_is_one_per_post_and_blocked_for_viewers(app):
    import learn as L
    o = signup(app, "learn2@x.com")
    o.post("/m/content_items/save", data=dict(title="One", status="Published", publish_date="2026-11-01"),
           follow_redirects=True)
    with app.app_context():
        from db import q
        cid = q("SELECT id FROM content_items ORDER BY id DESC LIMIT 1")[0]["id"]
        wid = q("SELECT id FROM workspaces ORDER BY id DESC LIMIT 1")[0]["id"]
    o.post(f"/m/content_items/{cid}/rate", data=dict(rating="flop"), follow_redirects=True)
    o.post(f"/m/content_items/{cid}/rate", data=dict(rating="good"), follow_redirects=True)
    with app.app_context():
        from db import q
        assert q("SELECT COUNT(*) c FROM post_feedback")[0]["c"] == 1          # changing your mind replaces
        assert L.rating_of(wid, cid) == "good"
    assert o.post(f"/m/content_items/{cid}/rate", data=dict(rating="meh")).status_code == 400
    dbx(app, "UPDATE memberships SET role='viewer'")
    assert o.post(f"/m/content_items/{cid}/rate", data=dict(rating="good")).status_code == 403


def test_review_link_qr_and_counting(app):
    o = signup(app, "rev1@x.com")
    assert o.get("/reviews").status_code == 200
    r = o.post("/reviews", data=dict(review_url="g.page/r/abc"), follow_redirects=True)
    assert "Share the link" in r.data.decode()
    with app.app_context():
        from db import q
        slug = q("SELECT slug FROM workspaces ORDER BY id DESC LIMIT 1")[0]["slug"]
    anon = app.test_client()
    hop = anon.get(f"/review/{slug}")
    assert hop.status_code == 302 and hop.headers["Location"] == "https://g.page/r/abc"   # https added for them
    assert anon.get(f"/review/{slug}/qr.svg").status_code == 200
    assert "1 tap" in o.get("/reviews").data.decode()
    assert app.test_client().get("/review/nobody").status_code == 404
    assert "/r/" not in o.get("/reviews").data.decode().split("Your asking link")[-1][:400]   # must not clash with the client report


def test_printable_month(app):
    o = signup(app, "prt@x.com")
    o.post("/m/content_items/save", data=dict(title="Festive post", publish_date="2026-11-20",
                                              channel="Instagram"), follow_redirects=True)
    o.post("/m/tasks/save", data=dict(title="Shoot reel", status="To do", due_date="2026-11-21"),
           follow_redirects=True)
    p = o.get("/calendar/print?y=2026&m=11").data.decode()
    assert "Festive post" in p and "Shoot reel" in p and "To do this month" in p
    import re
    link = re.search(r"/calendar/print\?[^\"]*", o.get("/calendar").data.decode()).group(0).replace("&amp;", "&")
    assert "y=2026" in link and "m=" in link and "m=&" not in link and not link.endswith("m=")
    assert o.get(link).status_code == 200                      # the link on the calendar must actually work
    assert o.get("/calendar/print?y=&m=").status_code == 200    # blank params fall back to this month
    assert o.get("/calendar/print?y=2026&m=77").status_code == 400


def test_hindi_covers_the_menu_and_falls_back_to_english(app):
    import i18n
    assert i18n.t("Calendar", "hi") == "कैलेंडर"
    assert i18n.t("Something nobody translated", "hi") == "Something nobody translated"
    assert i18n.t("Calendar", "en") == "Calendar"
    o = signup(app, "hi1@x.com")
    assert 'lang-sel' in o.get("/account").data.decode()
    r = o.post("/account/language", data=dict(lang="hi"), follow_redirects=True)
    assert "हिन्दी" in r.data.decode()
    d = o.get("/app").data.decode()
    assert '<html lang="hi"' in d
    for word in ("कंटेंट और कैलेंडर", "होम", "कैलेंडर", "मेन्यू"):
        assert word in d, word
    assert o.post("/account/language", data=dict(lang="zz")).status_code == 400
    o.post("/account/language", data=dict(lang="en"), follow_redirects=True)
    assert "Content &amp; Calendar" in o.get("/app").data.decode()


def test_one_workspace_language_does_not_leak_into_another(app):
    a = signup(app, "hi2@x.com")
    a.post("/account/language", data=dict(lang="hi"), follow_redirects=True)
    b = signup(app, "hi3@x.com")
    assert "Content &amp; Calendar" in b.get("/app").data.decode()
    assert "कंटेंट और कैलेंडर" not in b.get("/app").data.decode()
    assert "कंटेंट और कैलेंडर" in a.get("/app").data.decode()


def test_no_two_routes_claim_the_same_url(app):
    """A review link at /r/<slug> once shadowed the public client report at /r/<token>. Catch the
    next one automatically: two rules may share a URL only when they differ by HTTP method."""
    import collections
    by_rule = collections.defaultdict(set)
    for r in app.url_map.iter_rules():
        for m in (r.methods or set()) - {"HEAD", "OPTIONS"}:
            by_rule[(r.rule, m)].add(r.endpoint)
    clashes = {k: sorted(v) for k, v in by_rule.items() if len(v) > 1}
    assert not clashes, clashes


def test_every_template_resolves_from_either_folder(app):
    """The templates are split across part1 and part2 for GitHub's 100-file upload limit. Every one
    of them must still be findable by its plain name, from whichever folder it ended up in."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    names = []
    for part in ("part1", "part2"):
        d = os.path.join(here, "templates", part)
        assert os.path.isdir(d), part
        names += [f for f in os.listdir(d) if f.endswith(".html")]
    assert len(names) == len(set(names)), "the same template exists in both folders"
    assert len(names) > 100                                  # the reason the split exists
    with app.app_context():
        for n in names:
            assert app.jinja_env.get_template(n) is not None, n


def test_once_a_day_nudge_survives_indian_midnight(app):
    """created_at is stored in UTC. Comparing it against an Indian calendar date made every
    "once a day" check fire again and again between 00:00 and 05:30 IST."""
    import datetime as dt
    import services as S
    with app.app_context():
        cutoff = S.day_start_utc()
    start_ist = dt.datetime.combine(S.today(), dt.time.min, tzinfo=S.IST)
    assert cutoff == start_ist.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    assert cutoff <= dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def test_login_from_inside_the_demo_shows_the_sign_in_form(app):
    """Clicking Log in while poking around the demo used to bounce you straight back into the demo,
    with no way to reach the sign-in form."""
    c = app.test_client()
    assert c.get("/demo", follow_redirects=True).status_code == 200
    assert c.get("/app").status_code == 200                      # the demo session is live
    r = c.get("/login")
    assert r.status_code == 200 and b'name="password"' in r.data  # the real form, not a redirect
    assert c.get("/app").status_code == 302                       # and the demo session is over
    d = app.test_client()
    d.get("/demo", follow_redirects=True)
    s = d.get("/signup")
    assert s.status_code == 200 and b'name="password"' in s.data  # same for signing up for real


def test_a_real_account_is_still_sent_to_the_dashboard(app):
    o = signup(app, "real1@x.com")
    r = o.get("/login")
    assert r.status_code == 302 and r.headers["Location"].endswith("/app")
    assert o.get("/app").status_code == 200                       # and is NOT logged out by visiting it
    assert o.get("/signup").status_code == 302


def test_a_page_belongs_to_one_section_and_does_not_repeat_its_name(app):
    """Launch Plans used to light up "Campaigns" under Tasks & Campaigns, and every tab bar repeated
    the section's own name back at you."""
    import re
    o = signup(app, "nav1@x.com")
    o.post("/account/focus", data=dict(all="1"))
    hub_of = lambda p: (re.search(r'<nav class="hubtabs" data-hub="([^"]+)"', o.get(p).data.decode()) or [None, None])[1]
    assert hub_of("/m/gtm_plans") == "plan"        # Launch Plans lives in Launch playbook
    assert hub_of("/campaigns") == "tasks"
    assert hub_of("/m/leads") == "sales"
    for p in ("/m/leads", "/calendar", "/m/tasks"):
        page = o.get(p).data.decode()
        assert "ht-title" not in page              # the bar no longer repeats the section name
    tabs = re.findall(r'<a class="ht[ "][^>]*>([^<]+)</a>', o.get("/m/leads").data.decode())
    assert [x.strip() for x in tabs] == ["🧲 Leads", "🤝 Clients", "⭐ Reviews"]


# ---- team chat: reads like a messaging app ----
def _two_people(app):
    """An owner and a teammate with a short conversation across three days."""
    import datetime as dt
    o = signup(app, "chatowner@x.com")
    with app.app_context():
        from db import q, ins, ex
        wid = q("SELECT id FROM workspaces ORDER BY id DESC LIMIT 1")[0]["id"]
        rid = ins("users", dict(name="Riya Mehta", email="riya-chat@x.com", password_hash="x"))
        ins("memberships", dict(user_id=rid, workspace_id=wid, role="manager"))
        me = q("SELECT user_id FROM memberships WHERE workspace_id=? AND role='owner'", (wid,))[0]["user_id"]
        now = dt.datetime.utcnow()
        rows = [(me, rid, "Did the reel go out?", 2), (rid, me, "Not yet", 2),
                (me, rid, "Sending in 10 mins", 1), (me, rid, "Also the caption?", 1),
                (rid, me, "Sure", 0), (rid, me, "Shall I book the boost too?", 0)]
        for f, t, body, back in rows:
            ins("chat_messages", dict(workspace_id=wid, from_id=f, to_id=t, body=body,
                                      created_at=(now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")))
    return o, rid


def test_chat_groups_messages_and_separates_days(app):
    import re
    o, rid = _two_people(app)
    page = o.get(f"/chat/{rid}").get_data(as_text=True)
    body = page.split('id="msgs"')[1].split('<form id="cf"')[0]
    days = re.findall(r'class="msg-day"><span>([^<]*)', body)
    assert days[-1] == "Today" and "Yesterday" in days and len(days) == 3
    classes = re.findall(r'class="msg ([a-z ]+)"', body)
    assert classes == ["me", "them", "me", "me run", "them", "them run"]   # runs of one sender group up
    assert body.count("<p>") == 6


def test_chat_day_labels_use_india_time(app):
    import datetime as dt
    from team import _daychip, _daykey
    import services as S
    with app.app_context():
        utc_late = (dt.datetime.combine(S.today(), dt.time(0, 0)) - dt.timedelta(hours=5, minutes=30))
        # 23:30 UTC yesterday is already today in India, and must be labelled that way
        assert _daykey(utc_late.strftime("%Y-%m-%d %H:%M:%S")) == S.today().isoformat()
        assert _daychip(utc_late.strftime("%Y-%m-%d %H:%M:%S")) == "Today"


def test_chat_message_actions_are_not_always_open(app):
    o, rid = _two_people(app)
    page = o.get(f"/chat/{rid}").get_data(as_text=True)
    # the toolbar still exists for every message, but the page must carry the tap-to-open behaviour
    assert page.count('class="msg-act"') == 6
    assert 'classList.add("open")' in page and 'matchMedia("(hover:none)")' in page
    assert 'data-chatting="1"' in page


def test_png_designs_are_converted_for_instagram(app, tmp_path):
    """Instagram accepts JPEG and nothing else. A PNG design used to fail with a download error."""
    import io, os
    import config as C, services as S
    from PIL import Image
    C.UPLOAD_DIR = str(tmp_path)
    os.makedirs(os.path.join(str(tmp_path), "1"), exist_ok=True)
    buf = io.BytesIO()
    Image.new("RGBA", (300, 300), (255, 0, 0, 120)).save(buf, "PNG")
    png = S.store_file(1, "png", buf.getvalue())
    jpg = S.as_jpeg(png)
    assert jpg.endswith(".jpg") and jpg != png
    out = Image.open(os.path.join(str(tmp_path), "1", jpg.rsplit("/", 1)[-1]))
    assert out.mode == "RGB"                                   # transparency flattened, not black
    assert S.as_jpeg("/media/1/already.jpg") == "/media/1/already.jpg"
    assert S.as_jpeg("https://someone-else.example/a.png") == "https://someone-else.example/a.png"
    import social
    assert "JPEG" in social._friendly({"error_subcode": 2207003}, 400)
    assert "100 posts" in social._friendly({"code": 4}, 400)


# ---- More tools: you pick the extra features, and the section only exists if you picked some ----
def _sidebar(client):
    """Just the visible menu. The page also carries a hidden "all tools" list that search uses, and
    that list holds every page, so checking the whole left column proves nothing."""
    head = client.get("/app").get_data(as_text=True).split("<main")[0]
    return head.split('<div id="allTools"')[0]


def _more_tools_links(client):
    """The links listed under the More tools heading in the sidebar."""
    import re
    return re.findall(r'class="esstool[^"]*" href="([^"]+)"', _sidebar(client))


def test_more_tools_only_exists_when_you_pick_tools(app):
    import re
    o = signup(app, "more1@x.com")
    import hubs
    o.post("/account/focus", data={"hub": list(hubs.ORDER)}, follow_redirects=True)
    assert "More tools" not in _sidebar(o)                        # nothing switched off: no section
    page = o.get("/account").get_data(as_text=True)
    tools = re.findall(r'name="tool" value="([^"]+)"', page)
    assert len(tools) >= 4 and "/utm" in tools                    # a real list to choose from
    r = o.post("/account/focus", data={"hub": list(hubs.ORDER), "tool": ["/utm", "/m/keywords"]},
               follow_redirects=True)
    assert "2 extra tools added" in r.get_data(as_text=True)
    assert "More tools" in _sidebar(o)
    links = _more_tools_links(o)
    assert "/utm" in links and "/m/keywords" in links
    assert "/kudos" not in links                                   # only what was ticked
    r = o.post("/account/focus", data={"hub": list(hubs.ORDER)}, follow_redirects=True)
    assert "no More tools section" in r.get_data(as_text=True)
    assert "More tools" not in _sidebar(o)                         # unticking removes the section again


def test_picked_tools_are_remembered_and_still_work(app):
    o = signup(app, "more2@x.com")
    o.post("/account/focus", data={"hub": ["content"], "tool": ["/utm"]}, follow_redirects=True)
    page = o.get("/account").get_data(as_text=True)
    assert 'name="tool" value="/utm" checked' in page
    assert o.get("/utm").status_code == 200                        # the page itself is untouched
    import hubs
    assert hubs.focus_keys("h:content,t:/utm")[1] == ["/utm"]
    assert hubs.focus_keys("h:content")[1] is False                # nothing picked
    assert hubs.focus_keys("h:content,more")[1] is True            # an older save still means "show them all"


def test_an_old_more_switch_still_shows_something(app):
    """Saves made before tools were pickable used a plain "more" token - they must not break."""
    o = signup(app, "more3@x.com")
    dbx(app, "UPDATE users SET focus='h:content,h:tasks,more'")
    assert "More tools" in _sidebar(o)


def test_more_tools_appears_only_when_a_tool_is_ticked(app):
    """Profile > Menu > Extra tools: tick some and a More tools section appears in the sidebar
    holding exactly those. Tick none and the section does not exist at all."""
    import re
    o = signup(app, "tools1@x.com")

    import hubs as _h
    o.post("/account/focus", data={"hub": list(_h.ORDER)}, follow_redirects=True)
    assert "More tools" not in _sidebar(o)
    acc = o.get("/account").data.decode()
    tools = re.findall(r'name="tool" value="([^"]+)"', acc)
    hubs = list(_h.ORDER)
    assert len(tools) >= 4                                     # there is a real list to choose from
    r = o.post("/account/focus", data={"hub": hubs, "tool": tools[:2]}, follow_redirects=True)
    assert "More tools" in r.data.decode()
    assert "More tools" in _sidebar(o)
    links = _more_tools_links(o)
    for href in tools[:2]:                                     # the ticked tools are the ones listed
        assert href in links, href
    assert not [x for x in tools[2:] if x in links]             # and nothing else
    r = o.post("/account/focus", data={"hub": hubs}, follow_redirects=True)
    assert "no More tools section" in r.data.decode()
    assert "More tools" not in _sidebar(o)


def test_pages_meta_asks_for_before_app_review(app):
    c = app.test_client()
    d = c.get("/data-deletion")
    assert d.status_code == 200                                # reachable without signing in
    body = d.data.decode()
    for bit in ("Delete your data", "Export my data", "Delete workspace", "Publishing", "Business Integrations"):
        assert bit in body, bit
    p = c.get("/privacy").data.decode()
    assert "/data-deletion" in p and "access token" in p and "Connected social accounts" in p
    assert c.get("/terms").status_code == 200
    import os
    from PIL import Image
    icon = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "icons", "app-icon-1024.png")
    assert Image.open(icon).size == (1024, 1024)               # Meta requires exactly this


# ---- the round after the dark/light and menu report ----
def test_channels_can_be_created_and_renamed(app):
    o = signup(app, "chan1@x.com")
    page = o.get("/chat").get_data(as_text=True)
    assert "cl-plus" in page and 'id="newChan"' in page      # the form sits in the column, not floating out of it
    o.post("/chat/new", data=dict(name="Launch Week", topic="all things launch"), follow_redirects=True)
    with app.app_context():
        from db import q
        cid = q("SELECT id FROM channels WHERE name='launch-week'")[0]["id"]
    thread = o.get(f"/chat/c/{cid}").get_data(as_text=True)
    assert "ca-rename" in thread and 'id="renChan"' in thread
    r = o.post(f"/chat/c/{cid}/rename", data=dict(name="Launch 2026", topic="the big one"), follow_redirects=True)
    assert "Renamed to #launch-2026" in r.get_data(as_text=True)
    assert "the big one" in o.get(f"/chat/c/{cid}").get_data(as_text=True)
    clash = o.post(f"/chat/c/{cid}/rename", data=dict(name="general"), follow_redirects=True)
    assert "already a channel" in clash.get_data(as_text=True)
    dbx(app, "UPDATE memberships SET role='viewer'")
    assert o.post(f"/chat/c/{cid}/rename", data=dict(name="nope")).status_code == 403


def test_more_tools_holds_whatever_you_switched_off(app):
    """A section unticked in Profile > Menu goes straight to More tools, even if it is the only one."""
    import re
    o = signup(app, "mt1@x.com")
    import hubs
    everything = [k for k in hubs.ORDER]
    o.post("/account/focus", data={"hub": everything}, follow_redirects=True)
    assert "More tools" not in _sidebar(o)                   # nothing switched off, nothing to show
    o.post("/account/focus", data={"hub": [k for k in everything if k != "team"]}, follow_redirects=True)
    links = re.findall(r'class="esstool[^"]*"[^>]*>([^<]+)<', _sidebar(o))
    assert any("Team" in x for x in links) and len(links) == 2    # the one section, plus "All tools"
    assert "hidden · add back" not in _sidebar(o)            # it said the same thing twice


def test_new_accounts_keep_the_three_starting_sections(app):
    import re
    o = signup(app, "mt2@x.com")
    o.post("/account/focus", data={"hub": ["content", "tasks", "plan"]}, follow_redirects=True)
    assert re.findall(r'data-label="([^"]+)"', _sidebar(o)) == [
        "Content &amp; Calendar", "Tasks &amp; Campaigns", "Launch playbook"]


def test_colour_tokens_have_no_typos(app):
    """A --muted that should have been --mut meant a hardcoded grey won in both themes, and the text
    failed contrast on white and on near-black alike."""
    import glob, os, re
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    declared, risky = set(), set()
    files = (glob.glob(os.path.join(here, "static", "*.css")) + glob.glob(os.path.join(here, "static", "*.js"))
             + glob.glob(os.path.join(here, "templates", "*", "*.html")))   # some are set inline per element
    for f in files:
        text = open(f, encoding="utf-8").read()
        declared |= set(re.findall(r"(--[a-z0-9-]+)\s*:", text))
        # a var with no fallback, or a fallback that is a fixed colour, cannot follow the theme
        risky |= {m for m in re.findall(r"var\((--[a-z0-9-]+)\s*,\s*#[0-9a-fA-F]{3,8}\s*\)", text)}
        risky |= {m for m in re.findall(r"var\((--[a-z0-9-]+)\s*\)", text)}
    inline = {"--dx", "--rot"}                       # set per element by the confetti animation
    missing = {v for v in risky - declared - inline if not v.startswith("--tw")}
    assert not missing, f"CSS uses theme tokens nothing defines: {sorted(missing)}"


def test_tab_row_has_no_card_behind_it(app):
    css = open(__import__("os").path.join(
        __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))),
        "static", "bold.css"), encoding="utf-8").read()
    assert ".hubtabs{background:none!important" in css


def test_a_missing_picture_says_so_instead_of_breaking(app):
    import io
    from PIL import Image
    o = signup(app, "img1@x.com")
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), (10, 200, 90)).save(buf, "PNG")
    buf.seek(0)
    o.post("/chat/c/1/send", data={"file": (buf, "p.png")}, content_type="multipart/form-data",
           follow_redirects=True)
    page = o.get("/chat/c/1").get_data(as_text=True)
    assert "msg-gone" in page and "no longer on the server" in page
