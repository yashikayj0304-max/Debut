"""Thin DB layer over SQLAlchemy Core. Same SQL runs on SQLite (dev) and PostgreSQL (production)."""
from flask import g
from sqlalchemy import create_engine, inspect

engine = None
IS_PG = False


def init_engine(url):
    global engine, IS_PG
    kw = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
    else:
        kw.update(pool_size=5, max_overflow=5, pool_recycle=1800)
    engine = create_engine(url, **kw)
    IS_PG = engine.dialect.name == "postgresql"
    return engine


def qi(name):
    return '"' + name.replace('"', "") + '"'


def _sql(s):
    # psycopg2 uses %s placeholders, so literal % characters in the SQL text must be doubled first
    return s.replace("%", "%%").replace("?", "%s") if IS_PG else s


def conn():
    if "conn" not in g:
        g.conn = engine.connect()
    return g.conn


def close_conn(_=None):
    c = g.pop("conn", None)
    if c is not None:
        c.close()


def q(sql, args=(), one=False):
    rows = conn().exec_driver_sql(_sql(sql), tuple(args)).mappings().all()
    return (rows[0] if rows else None) if one else rows


def ex(sql, args=()):
    c = conn()
    n = c.exec_driver_sql(_sql(sql), tuple(args)).rowcount
    c.commit()
    return n


def ins(table, data):
    cols = list(data)
    sql = f"INSERT INTO {table} ({','.join(qi(c) for c in cols)}) VALUES ({','.join(['?'] * len(cols))}) RETURNING id"
    c = conn()
    nid = c.exec_driver_sql(_sql(sql), tuple(data.values())).scalar()
    c.commit()
    return nid


# ---------------------------------------------------------------- schema
def _pk():
    return "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"


EXTRA_COLUMNS = {
    "workspaces": [("industry", "TEXT DEFAULT 'general'"), ("ics_key", "TEXT DEFAULT ''"), ("hook_key", "TEXT DEFAULT ''"), ("brand_color", "TEXT DEFAULT ''"), ("secondary_color", "TEXT DEFAULT ''"), ("logo_url", "TEXT DEFAULT ''")],
    "memberships": [("client_name", "TEXT DEFAULT ''")],
    "invites": [("client_name", "TEXT DEFAULT ''")],
    "comments": [("client_visible", "INTEGER DEFAULT 0")],
    "users": [("totp_secret", "TEXT DEFAULT ''"), ("totp_on", "INTEGER DEFAULT 0"), ("totp_last", "INTEGER DEFAULT 0"), ("recovery", "TEXT DEFAULT ''"), ("digest", "INTEGER DEFAULT 1"), ("onboarded", "INTEGER DEFAULT 0"), ("pin_hash", "TEXT DEFAULT ''")],
    "board_items": [("x", "INTEGER DEFAULT -1"), ("y", "INTEGER DEFAULT -1"), ("w", "INTEGER DEFAULT 240"), ("h", "INTEGER DEFAULT 170"), ("z", "INTEGER DEFAULT 1")],
    # a manual within-column order for every kanban-enabled module, so cards can be dragged into a custom
    # order inside one column (not just dragged between columns) - see kanban() / m_reorder() in views.py
    **{k: [("sort_order", "INTEGER DEFAULT 0")] for k in
       ("launch_checklist", "content_items", "campaigns", "influencers", "leads", "tasks", "creators", "content_orders", "promotions", "events", "pitches", "accounts")},
}


def init_schema(modules):
    pk = _pk()
    core = [
        f"CREATE TABLE IF NOT EXISTS users (id {pk}, email TEXT UNIQUE NOT NULL, name TEXT DEFAULT '', password_hash TEXT NOT NULL, email_verified INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login TIMESTAMP, totp_secret TEXT DEFAULT '', totp_on INTEGER DEFAULT 0, totp_last INTEGER DEFAULT 0, recovery TEXT DEFAULT '', digest INTEGER DEFAULT 1, onboarded INTEGER DEFAULT 0)",
        f"CREATE TABLE IF NOT EXISTS workspaces (id {pk}, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, plan TEXT DEFAULT 'trial', plan_status TEXT DEFAULT 'trialing', trial_ends TEXT DEFAULT '', period_end TEXT DEFAULT '', rzp_subscription_id TEXT DEFAULT '', pending_plan TEXT DEFAULT '', cancel_at_period_end INTEGER DEFAULT 0, owner_id INTEGER, industry TEXT DEFAULT 'general', ics_key TEXT DEFAULT '', hook_key TEXT DEFAULT '', brand_color TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS memberships (id {pk}, workspace_id INTEGER NOT NULL, user_id INTEGER NOT NULL, role TEXT NOT NULL, client_name TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(workspace_id, user_id))",
        f"CREATE TABLE IF NOT EXISTS invites (id {pk}, workspace_id INTEGER NOT NULL, email TEXT NOT NULL, role TEXT NOT NULL, token_hash TEXT NOT NULL, client_name TEXT DEFAULT '', accepted INTEGER DEFAULT 0, expires TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS ai_usage (id {pk}, workspace_id INTEGER NOT NULL, user_id INTEGER, task TEXT, credits INTEGER DEFAULT 1, month TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS audit_log (id {pk}, workspace_id INTEGER, user_id INTEGER, action TEXT, detail TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS webhook_events (id {pk}, event_id TEXT UNIQUE, type TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS comments (id {pk}, workspace_id INTEGER NOT NULL, module TEXT NOT NULL, record_id INTEGER NOT NULL, user_id INTEGER, body TEXT NOT NULL, client_visible INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS notifications (id {pk}, workspace_id INTEGER NOT NULL, user_id INTEGER NOT NULL, kind TEXT DEFAULT '', message TEXT NOT NULL, link TEXT DEFAULT '', is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS api_keys (id {pk}, workspace_id INTEGER NOT NULL, user_id INTEGER, name TEXT DEFAULT '', prefix TEXT DEFAULT '', key_hash TEXT UNIQUE NOT NULL, scope TEXT DEFAULT 'read', last_used TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS feedback (id {pk}, workspace_id INTEGER, user_id INTEGER, kind TEXT DEFAULT 'idea', page TEXT DEFAULT '', message TEXT NOT NULL, resolved INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS pulse_runs (id {pk}, workspace_id INTEGER NOT NULL, payload TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS boards (id {pk}, workspace_id INTEGER NOT NULL DEFAULT 0, name TEXT, description TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS board_items (id {pk}, workspace_id INTEGER NOT NULL DEFAULT 0, board_id INTEGER, kind TEXT, content TEXT, caption TEXT DEFAULT '', x INTEGER DEFAULT -1, y INTEGER DEFAULT -1, w INTEGER DEFAULT 240, h INTEGER DEFAULT 170, z INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    ]
    with engine.begin() as c:
        if IS_PG:
            c.exec_driver_sql("SELECT pg_advisory_xact_lock(727272)")  # avoid races when several workers boot
        for ddl in core:
            c.exec_driver_sql(ddl)
        for key, m in modules.items():
            cols = ",".join(f"{qi(f[0])} TEXT DEFAULT ''" for f in m["fields"])
            c.exec_driver_sql(f"CREATE TABLE IF NOT EXISTS {key} (id {pk}, workspace_id INTEGER NOT NULL DEFAULT 0, {cols}, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    insp = inspect(engine)
    with engine.begin() as c:  # additive migrations: new fields in code become new columns
        for key, m in modules.items():
            have = {col["name"] for col in insp.get_columns(key)}
            for f in m["fields"]:
                if f[0] not in have:
                    c.exec_driver_sql(f"ALTER TABLE {key} ADD COLUMN {qi(f[0])} TEXT DEFAULT ''")
        for table, cols in EXTRA_COLUMNS.items():          # columns added to core tables after the first release
            have_cols = {col["name"] for col in insp.get_columns(table)}
            for col, ddl in cols:
                if col not in have_cols:
                    c.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        for t in list(modules) + ["boards", "board_items", "memberships", "ai_usage", "audit_log", "comments", "notifications", "api_keys", "pulse_runs"]:
            col = "workspace_id"
            c.exec_driver_sql(f"CREATE INDEX IF NOT EXISTS ix_{t}_ws ON {t} ({col})")
        c.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_members_user ON memberships (user_id)")
        c.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_comments_rec ON comments (workspace_id, module, record_id)")
        c.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_notif_user ON notifications (user_id, is_read)")
