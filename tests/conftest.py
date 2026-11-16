import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import config as C
import services as S
import db as D
from db import q, ex


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(C, "BILLING_MODE", "demo")
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path}/t.db"
    from app import create_app
    a = create_app(config={"TESTING": True, "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False}, database_url=url)
    if url.startswith("postgresql"):  # start every test from a clean slate (and reset ids)
        from modules import MODULES
        tables = ["webhook_events", "audit_log", "ai_usage", "invites", "memberships", "board_items", "boards", "comments", "notifications", "api_keys", "feedback", "pulse_runs", "reminders", "push_subs", "kv", "workspaces", "users"] + list(MODULES)
        with a.app_context():
            ex("TRUNCATE " + ",".join(tables) + " RESTART IDENTITY CASCADE")
    if app_has_js := True:
        _js = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "app.js"), encoding="utf-8").read()

        @a.after_request
        def _inline_app_js(r):
            # The shared page script moved into static/app.js. Tests that look for its code or data in the page still see it.
            if r.mimetype == "text/html" and not r.direct_passthrough and b"static/app.js" in r.get_data():
                import re as _re
                t = r.get_data(as_text=True)
                m = _re.search(r'"tools":(\[.*?\]),"hubnow":(".*?"),"vp"', t, _re.S)
                extra = ("<script>" + (f"window.TOOLS={m.group(1)};window.HUBNOW={m.group(2)};" if m else "") + _js + "</script>")
                r.set_data(t.replace("</body>", extra + "</body>", 1) if "</body>" in t else t + extra)
            return r
    yield a


@pytest.fixture()
def mails(monkeypatch):
    box = []
    monkeypatch.setattr(S, "send_email", lambda to, subject, body: box.append((to, subject, body)) or True)
    return box


def dbq(app, sql, args=(), one=False):
    with app.app_context():
        r = q(sql, args, one=one)
        return dict(r) if (one and r) else ([dict(x) for x in r] if not one else None)


def dbx(app, sql, args=()):
    with app.app_context():
        return ex(sql, args)


def signup(app, email, name="Tester", ws="Acme Foods", pw="Sup3rSecret!"):
    c = app.test_client()
    r = c.post("/signup", data=dict(name=name, email=email, workspace=ws, password=pw, agree="1", focus=["content", "launch", "results", "sales", "reach", "ai", "team"]))   # tests open the full menu; test_new_accounts_start_on_the_short_menu covers the default
    assert r.status_code == 302, r.data[:500]
    return c


def wid_of(app, email):
    return dbq(app, "SELECT w.id FROM workspaces w JOIN users u ON u.id=w.owner_id WHERE u.email=?", (email,), one=True)["id"]


def read_template(name):
    """Read a template by name. They live in templates/part1 or templates/part2 (GitHub's uploader
    takes 100 files at a time, and there are more than 100), so tests must not hardcode either."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for part in ("part1", "part2", ""):
        p = os.path.join(here, "templates", part, name)
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
    raise FileNotFoundError(f"template not found in either part: {name}")
