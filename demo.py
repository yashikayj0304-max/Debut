"""A read-only sample brand ("Chai & Co") that visitors can open before signing up. Re-seeded fresh every day."""
import datetime as dt
import secrets
from werkzeug.security import generate_password_hash
from db import q, ex, ins
import services as S

DEMO_EMAIL = "demo@demo.debut.invalid"
OWNER_EMAIL = "demo-owner@demo.debut.invalid"
SLUG = "chai-and-co-demo"


def is_demo_user(user):
    return bool(user) and (user["email"] or "").endswith("@demo.debut.invalid")


def _user(email, name):
    u = q("SELECT id FROM users WHERE email=?", (email,), one=True)
    return u["id"] if u else ins("users", dict(email=email, name=name, password_hash=generate_password_hash(secrets.token_urlsafe(24)), email_verified=1, onboarded=1))


def _seed(wid):
    t = S.today()
    d = lambda n: (t + dt.timedelta(days=n)).isoformat()
    posts = [("Monsoon chai-and-pakoda reel", "Instagram", "Reel / Short", "Scheduled", 1), ("Kulhad gift box teaser", "Instagram", "Carousel", "Planned", 3),
             ("Founder story: why we blend our own", "LinkedIn", "Article", "Draft", 5), ("Diwali hamper launch email", "Email", "Newsletter", "In review", 7),
             ("Behind the brew: masala chai", "YouTube", "Video", "Planned", 9), ("Weekend flash sale story", "Instagram", "Story", "Scheduled", 2),
             ("Customer review roundup", "Facebook", "Post", "Published", -2), ("New flavour poll", "Instagram", "Story", "Published", -4),
             ("Tea-time WhatsApp broadcast", "WhatsApp", "Post", "Planned", 11), ("Chai-lover creator collab", "Instagram", "Reel / Short", "Draft", 14)]
    for title, ch, fmt, st, off in posts:
        ins("content_items", dict(workspace_id=wid, title=title, channel=ch, format=fmt, status=st, publish_date=d(off), copy="Sample copy for the demo.", owner="Asha"))
    for title, who, off, pr, st in [("Brief the hamper photographer", "Asha", 0, "High", "To do"), ("Approve Diwali email copy", "Ravi", 0, "High", "In progress"), ("Book creator for reel", "Asha", 4, "Medium", "To do"),
                                    ("Update price list", "Ravi", -1, "Low", "Done"), ("Send monsoon sale report", "Asha", 6, "Medium", "To do")]:
        ins("tasks", dict(workspace_id=wid, title=title, assignee=who, due_date=d(off), priority=pr, status=st))
    for n, c, stg, v in [("Meera Kapoor", "Brew Cafe Chain", "Proposal", 120000), ("Jay Shah", "Gift Studio", "New", 45000), ("Nisha Rao", "Office Pantry Co", "Won", 80000), ("Kabir Singh", "Wedding Planners", "Contacted", 60000)]:
        ins("leads", dict(workspace_id=wid, name=n, company=c, stage=stg, value=v, source="Instagram"))
    for m, v, tg in [("Instagram reach", 42000, 50000), ("Email open rate %", 31, 35), ("Orders", 380, 400), ("Website visits", 12800, 15000)]:
        ins("kpis", dict(workspace_id=wid, metric=m, channel="All", period=t.strftime("%Y-%m"), value=v, target=tg))
    ins("campaigns", dict(workspace_id=wid, name="Diwali gifting 2026", objective="Sales", channel="Instagram", start_date=d(-3), end_date=d(25), budget=60000, spent=18000, status="Live", owner="Asha"))
    bid = ins("boards", dict(workspace_id=wid, name="Monsoon chai mood", description="Warm, rainy-window, steam and clay cups."))
    items = [("color", "#8B4A2B", "Clay brown"), ("color", "#E9B44C", "Saffron"), ("color", "#2F4858", "Rain-cloud blue"), ("color", "#F6E8D0", "Cream"),
             ("note", "Tone: cosy, a little witty. One line, one emoji max.", "Tone"), ("note", "Shots: steam close-ups, hands round a kulhad, rain on glass.", "Shot list")]
    x = 20
    for kind, content, cap in items:
        ins("board_items", dict(workspace_id=wid, board_id=bid, kind=kind, content=content, caption=cap, x=x % 700, y=20 + (x // 700) * 190, w=220, h=150, z=1))
        x += 240


def ensure_demo():
    """Returns (demo_user_id, workspace_id), creating or refreshing the sample brand when it is missing or from an earlier day."""
    owner = _user(OWNER_EMAIL, "Chai & Co")
    viewer = _user(DEMO_EMAIL, "Demo visitor")
    ws = q("SELECT * FROM workspaces WHERE slug=?", (SLUG,), one=True)
    today = S.today().isoformat()
    if not ws:
        wid = ins("workspaces", dict(name="Chai & Co (demo)", slug=SLUG, plan="team", plan_status="active", industry="fmcg", owner_id=owner, ics_key=secrets.token_hex(6), hook_key=secrets.token_hex(12), period_end=today))
        ins("memberships", dict(workspace_id=wid, user_id=owner, role="owner"))
        ins("memberships", dict(workspace_id=wid, user_id=viewer, role="viewer"))
        S.seed_workspace(wid, "fmcg", False)
        _seed(wid)
    else:
        wid = ws["id"]
        if (ws["period_end"] or "") != today:
            S.wipe_workspace_data(wid, keep_members=True)
            S.seed_workspace(wid, "fmcg", False)
            _seed(wid)
            ex("UPDATE workspaces SET period_end=?, plan='team', plan_status='active' WHERE id=?", (today, wid))
        if not q("SELECT id FROM memberships WHERE workspace_id=? AND user_id=?", (wid, viewer), one=True):
            ins("memberships", dict(workspace_id=wid, user_id=viewer, role="viewer"))
    return viewer, wid
