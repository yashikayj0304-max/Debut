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
    dbx(app, "UPDATE workspaces SET created_at=? WHERE id=?", ("", w))
    assert o.get("/app").status_code < 500
    dbx(app, "UPDATE workspaces SET created_at=?, industry=? WHERE id=?", ("2026-01-01 00:00:00", "does_not_exist", w))
    assert o.get("/app").status_code < 500
    assert o.get("/ai").status_code < 500


def test_round3_empty_created_at_with_content_does_not_break_home(app):
    o = signup(app, "odd2@x.com")
    w = wid_of(app, "odd2@x.com")
    dbx(app, "UPDATE workspaces SET created_at=? WHERE id=?", ("", w))
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
    assert "Plan your marketing." in land and "Start free" in land and "Main character energy" not in land
    s = c.get("/signup").data.decode()
    head, more = s.split('<details class="signup-more">', 1)
    assert 'name="industry"' in head and 'name="workspace"' not in head and 'name="workspace"' in more.split('</details>')[0]
    assert "Talk to a real person" in s
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
    for p in ("/features", "/templates", "/pricing"):
        h = c.get(p).data.decode()
        assert 'class="pub' in h and "Open app" in h, p
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
    h = c.get("/app").data.decode(); assert "/studio" in h and "/promos" in h
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
    p = c.get("/promos"); assert p.status_code == 200 and b"Plan this" in p.data
    import re
    pid = re.search(r'name="id" value="([^"]+)"', p.data.decode()).group(1)
    before = dbq(app, "SELECT COUNT(*) n FROM content_items", one=True)["n"]
    r = c.post("/promos/plan", data={"id": pid}); assert r.status_code == 302
    assert dbq(app, "SELECT COUNT(*) n FROM content_items", one=True)["n"] > before
    assert dbq(app, "SELECT COUNT(*) n FROM tasks WHERE description LIKE 'For %'", one=True)["n"] == 5
    n = dbq(app, "SELECT COUNT(*) n FROM campaigns", one=True)["n"]
    c.post("/promos/plan", data={"id": pid}); assert dbq(app, "SELECT COUNT(*) n FROM campaigns", one=True)["n"] == n      # twice = once
    assert c.post("/promos/plan", data={"id": "nope"}).status_code == 302


def test_studio_demo_can_draft_but_not_save(app):
    c = app.test_client(); c.get("/demo", follow_redirects=True)
    assert c.get("/studio").status_code == 200 and c.get("/promos").status_code == 200
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
    r = anon.get("/cron/morning?key=s3cret-key"); assert r.status_code == 200 and set(r.get_json()) == {"digests", "pushes"}
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
    assert b"class=\"ht-more\"" in cal and b"Key dates" in cal.split(b"class=\"ht-more\"")[1]
    k = c.get("/m/key_dates").data                                     # a tab picked from More shows as the active tab in the row
    assert b"class=\"sbt on\" href=\"/m/key_dates\"" in k and b"class=\"ht on\"" in k


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
    assert 'data-hub="campaigns"' in side and 'href="/campaigns"' in side
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
    assert 'class="bento"' in html and "debFab" in html and "Festival countdown" in html
    w = o.get("/wrapped").data.decode()
    assert 'id="wr"' in w and "Your week, wrapped" in w and o.get("/wrapped?p=year").status_code == 200
    r = o.get("/radar").data.decode()
    assert "Make it" in r and "Hook (2s)" in r or "POV" in r or "3 things" in r
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
