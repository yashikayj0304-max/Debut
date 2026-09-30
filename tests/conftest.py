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
        tables = ["webhook_events", "audit_log", "ai_usage", "invites", "memberships", "board_items", "boards", "comments", "notifications", "api_keys", "feedback", "pulse_runs", "workspaces", "users"] + list(MODULES)
        with a.app_context():
            ex("TRUNCATE " + ",".join(tables) + " RESTART IDENTITY CASCADE")
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
    r = c.post("/signup", data=dict(name=name, email=email, workspace=ws, password=pw, agree="1"))
    assert r.status_code == 302, r.data[:500]
    return c


def wid_of(app, email):
    return dbq(app, "SELECT w.id FROM workspaces w JOIN users u ON u.id=w.owner_id WHERE u.email=?", (email,), one=True)["id"]
