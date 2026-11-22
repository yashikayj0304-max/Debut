"""Read-only sample brands that visitors can open before signing up. Everything is seeded relative to today (IST), so it never looks stale, and re-seeded each day."""
import base64
import datetime as dt
import io
import secrets
from werkzeug.security import generate_password_hash
from db import q, ex, ins
import services as S

DEMO_EMAIL = "demo@demo.debut.invalid"
OWNER_EMAIL = "demo-owner@demo.debut.invalid"
SLUG = "chai-and-co-demo"

VARIANTS = {
    "chai": dict(slug=SLUG, name="Chai & Co (demo)", industry="d2c", label="Chai & Co", blurb="a D2C tea brand"),
    "neon": dict(slug="studio-neon-demo", name="Studio Neon (demo)", industry="agency", label="Studio Neon", blurb="a small marketing agency"),
    "riya": dict(slug="riya-creates-demo", name="Riya Creates (demo)", industry="personal_brand", label="Riya Creates", blurb="a solo creator"),
}


def is_demo_user(user):
    return bool(user) and (user["email"] or "").endswith("@demo.debut.invalid")


def _user(email, name):
    u = q("SELECT id FROM users WHERE email=?", (email,), one=True)
    return u["id"] if u else ins("users", dict(email=email, name=name, password_hash=generate_password_hash(secrets.token_urlsafe(24)), email_verified=1, onboarded=1))


def _img(c1, c2, label=""):
    """A small real picture (soft diagonal gradient with a few shapes) as a data URI, so mood boards show images with no network."""
    from PIL import Image, ImageDraw
    w, h = 320, 220
    im = Image.new("RGB", (w, h), c1)
    px = im.load()
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    for y in range(h):
        for x in range(w):
            t = (x / w + y / h) / 2
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    dr = ImageDraw.Draw(im, "RGBA")
    dr.ellipse((w * .55, h * .1, w * .95, h * .75), fill=(255, 255, 255, 46))
    dr.ellipse((w * .08, h * .5, w * .42, h * 1.1), fill=(0, 0, 0, 38))
    dr.rounded_rectangle((w * .3, h * .38, w * .62, h * .8), 18, fill=(255, 255, 255, 70))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ------------------------------------------------------------------ Chai & Co
CHAI_POSTS = [
    # title, channel, format, status, day offset
    ("Winter kulhad chai reel", "Instagram", "Reel / Short", "Published", -12), ("Customer review roundup", "Facebook", "Post", "Published", -9),
    ("Diwali hamper thank-you story", "Instagram", "Story", "Published", -7), ("Founder note: our Diwali, in numbers", "LinkedIn", "Article", "Published", -5),
    ("Winter masala chai poll", "Instagram", "Story", "Published", -3), ("Brew-at-home guide email", "Email", "Newsletter", "Published", -2),
    ("Children's Day tea-time story", "Instagram", "Story", "Scheduled", 0), ("Shaadi gift box reel", "Instagram", "Reel / Short", "In review", 1),
    ("Kulhad gift box carousel", "Instagram", "Carousel", "Planned", 2), ("Dev Diwali diya + chai post", "Facebook", "Post", "Planned", 3),
    ("Weekend winter-chai flash sale", "WhatsApp", "Post", "Scheduled", 4), ("Behind the brew: masala chai", "YouTube", "Video", "Planned", 6),
    ("Black Friday early-access email", "Email", "Newsletter", "Draft", 9), ("Founder story: why we blend our own", "LinkedIn", "Article", "Draft", 8),
    ("Black Friday countdown reel", "Instagram", "Reel / Short", "Planned", 11), ("Cyber Monday last-call story", "Instagram", "Story", "Planned", 16),
    ("Winter gifting guide", "YouTube", "Video", "Planned", 18), ("Chai-lover creator collab", "Instagram", "Reel / Short", "Draft", 21),
    ("Secret Santa tea hamper post", "Facebook", "Post", "Planned", 24), ("Christmas morning chai story", "Instagram", "Story", "Planned", 41),
    ("Year-in-chai recap email", "Email", "Newsletter", "Planned", 44), ("New Year resolution: slow mornings reel", "Instagram", "Reel / Short", "Planned", 48),
    ("Sankranti til-chai special", "WhatsApp", "Post", "Planned", 60),
]
CHAI_TASKS = [
    ("Approve the Shaadi gift box reel", "Asha", 0, "High", "In progress", "Final cut is in the review folder. Check subtitles and the offer line."),
    ("Brief the hamper photographer", "Asha", 0, "High", "To do", ""), ("Approve Black Friday email copy", "Ravi", 1, "High", "To do", ""),
    ("Book creator for the winter reel", "Asha", 4, "Medium", "To do", ""), ("Send Diwali results to the founders", "Ravi", 3, "Medium", "In progress", ""),
    ("Reorder kulhad stock", "Ravi", 6, "Medium", "To do", ""), ("Plan the Sankranti til-chai post", "Asha", 12, "Low", "To do", ""),
] + [(t, w, o, "Medium", "Done", "") for t, w, o in [
    ("Update price list", "Ravi", -1), ("Shoot Diwali hamper photos", "Asha", -2), ("Publish Diwali gifting landing page", "Ravi", -3), ("Collect customer testimonials", "Asha", -4),
    ("Write Diwali email series", "Asha", -5), ("Set up Diwali UTM links", "Ravi", -6), ("Brief the gifting creators", "Asha", -7), ("Approve hamper packaging", "Ravi", -8),
    ("Schedule the Diwali countdown", "Asha", -9), ("Audit last month's results", "Ravi", -11), ("Pick Diwali hamper SKUs", "Asha", -14), ("Refresh Instagram highlights", "Asha", -16), ("Order sample boxes", "Ravi", -18)]]
CHAI_LEADS = [("Meera Kapoor", "Brew Cafe Chain", "Opportunity", 120000, "Instagram", "Send the wholesale price sheet"), ("Jay Shah", "Gift Studio", "MQL", 45000, "Instagram", "Share the sample box"),
              ("Nisha Rao", "Office Pantry Co", "Won", 80000, "Referral", "Schedule onboarding"), ("Kabir Singh", "Wedding Planners", "SQL", 60000, "Website", "Call about Shaadi boxes"),
              ("Tanvi Joshi", "Corporate Gifting Hub", "New", 95000, "LinkedIn", "Reply to enquiry"), ("Arjun Mehta", "Cafe Mocha", "Opportunity", 38000, "WhatsApp", "Confirm first order"),
              ("Sana Iqbal", "Studio Cafe", "Lost", 25000, "Instagram", "")]
CHAI_INFL = [("Pooja Sharma", "Instagram", "pooja.eats", "Micro (10k-100k)", "48000", "5.8", "Food", "Delivered"), ("Rohan Verma", "YouTube", "rohanbrews", "Mid (100k-500k)", "210000", "3.9", "Lifestyle", "Negotiating"),
              ("Ishita Nair", "Instagram", "ishita.slowmornings", "Nano (<10k)", "8500", "7.2", "Wellness", "Shortlisted")]
CHAI_KPIS = [  # metric, base, weekly growth, target, dip multiplier at week index 5 (the Diwali rush week made reach jump, then a quiet dip)
    ("Instagram reach", 30000, 1500, 50000), ("Email open rate %", 24, .7, 35), ("Orders", 220, 14, 400), ("Website visits", 8200, 460, 15000)]
CHAI_DATES = [("Dev Diwali", "11-24", "Festival"), ("Black Friday", "11-27", "Sale"), ("Cyber Monday", "11-30", "Sale"),
              ("Christmas", "12-25", "Festival"), ("New Year's Eve", "12-31", "Festival"), ("Makar Sankranti", "01-14", "Festival")]


def _kpi_series(wid, rows, t, weeks=11, dip_at=5):
    for metric, base, step, target in rows:
        for k in range(weeks):
            wk = weeks - 1 - k                       # weeks ago
            v = base + step * k
            if k == dip_at:
                v = v * .86                           # the quiet week after the festival: an honest dip
            if k == dip_at + 1:
                v = v * 1.06
            ins("kpis", dict(workspace_id=wid, metric=metric, channel="All", period=(t - dt.timedelta(days=7 * wk)).isoformat(), value=round(v, 1) if v < 100 else int(v), target=target))


def _activity(wid, uid, t, counts):
    """Audit trail for the demo visitor: gives a 12-day streak and real 'made' counts on the Recap page."""
    ex("DELETE FROM audit_log WHERE workspace_id=?", (wid,))
    for back in range(12):
        day = (t - dt.timedelta(days=back)).isoformat()
        ins("audit_log", dict(workspace_id=wid, user_id=uid, action="login", detail="", created_at=f"{day} 10:00:00"))
    for mod, n in counts.items():
        for i in range(n):
            day = (t - dt.timedelta(days=i % 28)).isoformat()
            ins("audit_log", dict(workspace_id=wid, user_id=uid, action="create", detail=f"{mod}#{i}", created_at=f"{day} 11:00:00"))


def _boards(wid, specs):
    for name, desc, imgs, colors, notes in specs:
        bid = ins("boards", dict(workspace_id=wid, name=name, description=desc))
        x = 20
        for (c1, c2), cap in imgs:
            ins("board_items", dict(workspace_id=wid, board_id=bid, kind="image", content=_img(c1, c2), caption=cap, x=x % 700, y=20 + (x // 700) * 190, w=220, h=150, z=1))
            x += 240
        for hexv, cap in colors:
            ins("board_items", dict(workspace_id=wid, board_id=bid, kind="color", content=hexv, caption=cap, x=x % 700, y=20 + (x // 700) * 190, w=140, h=120, z=1))
            x += 160
        for text, cap in notes:
            ins("board_items", dict(workspace_id=wid, board_id=bid, kind="note", content=text, caption=cap, x=x % 700, y=20 + (x // 700) * 190, w=220, h=150, z=1))
            x += 240


def _dates(wid, t, rows):
    ex("DELETE FROM key_dates WHERE workspace_id=? AND date<?", (wid, t.isoformat()))      # a busy brand looks ahead, not back
    horizon = (t + dt.timedelta(days=400)).isoformat()
    for name, md, kind in rows:
        for yy in (t.year, t.year + 1):
            ds = f"{yy}-{md}"
            if t.isoformat() <= ds <= horizon and not q("SELECT 1 FROM key_dates WHERE workspace_id=? AND name=? AND date=?", (wid, name, ds), one=True):
                ins("key_dates", dict(workspace_id=wid, name=name, date=ds, kind=kind))
                break


def _seed_chai(wid, viewer):
    t = S.today()
    d = lambda n: (t + dt.timedelta(days=n)).isoformat()
    for title, ch, fmt, st, off in CHAI_POSTS:
        ins("content_items", dict(workspace_id=wid, title=title, channel=ch, format=fmt, status=st, publish_date=d(off), owner="Asha" if off % 2 == 0 else "Ravi",
                                  copy="A warm winter-evening line, one emoji, ends with the shop link.", cta="Shop the winter blends", hashtags="#chai #winterchai #kulhad",
                                  campaign="Winter chai subscription" if off > -6 else "Diwali gifting 2026"))
    for title, who, off, pr, st, desc in CHAI_TASKS:
        ins("tasks", dict(workspace_id=wid, title=title, assignee=who, due_date=d(off), priority=pr, status=st, description=desc))
    for n, c, stg, v, src, nxt in CHAI_LEADS:
        ins("leads", dict(workspace_id=wid, name=n, company=c, stage=stg, value=v, source=src, next_step=nxt))
    for n, plat, h, tier, f, er, niche, st in CHAI_INFL:
        ins("influencers", dict(workspace_id=wid, name=n, platform=plat, handle=h, tier=tier, followers=f, engagement_rate=er, niche=niche, city="Mumbai", language="Hinglish", status=st,
                                fit_score="8", next_followup=d(5) if st != "Delivered" else ""))
    _kpi_series(wid, CHAI_KPIS, t)
    ins("campaigns", dict(workspace_id=wid, name="Diwali gifting 2026", objective="Sales", channel="Instagram", start_date=d(-40), end_date=d(-6), budget=60000, spent=58200, status="Completed", owner="Asha",
                          kpi_target="Orders 400", learnings="Reels beat static posts 3 to 1. Emails sent after 7pm opened best. Next year: book creators 3 weeks earlier."))
    ins("campaigns", dict(workspace_id=wid, name="Winter chai subscription", objective="Retention", channel="Email", start_date=d(-12), end_date=d(30), budget=40000, spent=14500, status="Live", owner="Ravi", kpi_target="150 subscribers"))
    ins("campaigns", dict(workspace_id=wid, name="Shaadi season gift boxes", objective="Awareness", channel="Instagram", start_date=d(10), end_date=d(45), budget=75000, spent=0, status="Planning", owner="Asha", kpi_target="60 wedding-planner leads"))
    ins("gtm_plans", dict(workspace_id=wid, name="Diwali gifting hampers", product="Kulhad gift hamper (3 sizes)", stage="Post-launch", launch_date=d(-40), budget=60000, owner="Asha",
                          goal="400 hamper orders in 4 weeks", target_market="Gifting buyers, 25 to 45, metros", positioning="Hand-blended chai in a kulhad box people keep",
                          pricing="₹649 / ₹999 / ₹1,499", channels="Instagram reels, WhatsApp, email", notes="Hit 412 orders."))
    ins("gtm_plans", dict(workspace_id=wid, name="Winter chai subscription", product="Monthly masala chai box", stage="Launch", launch_date=d(-12), budget=40000, owner="Ravi",
                          goal="150 subscribers by 15 December", target_market="Home chai drinkers, 28 to 50", positioning="Fresh-blended chai, delivered before you run out",
                          pricing="₹499 a month", channels="Email, Instagram, WhatsApp"))
    ex("UPDATE gtm_plans SET stage='Scale' WHERE workspace_id=? AND name='Diwali gifting hampers'", (wid,))
    _boards(wid, [
        ("Winter kulhad chai", "Steam, clay cups, fog on the window.", [(("#8B4A2B", "#E9B44C"), "Golden hour steam"), (("#2F4858", "#8FB8C9"), "Rain-cloud morning"), (("#C77D4B", "#F6E8D0"), "Kulhad close-up")],
         [("#8B4A2B", "Clay brown"), ("#E9B44C", "Saffron")], [("Tone: cosy, a little witty. One line, one emoji.", "Tone")]),
        ("Winter gifting", "Hampers, ribbons, handwritten notes.", [(("#7A1F3D", "#E8A5B5"), "Berry ribbon"), (("#1F3D2B", "#C9D8A8"), "Pine green box"), (("#3D2B1F", "#D9B38C"), "Kraft wrap")],
         [("#7A1F3D", "Berry"), ("#F6E8D0", "Cream")], [("Every box gets a handwritten card.", "Detail")]),
        ("Shaadi season", "Gold, marigold and mehendi green.", [(("#B8860B", "#FFE08A"), "Marigold"), (("#2E5339", "#A8D5A2"), "Mehendi green"), (("#9C2A2A", "#F2B8A0"), "Red and gold")],
         [("#B8860B", "Gold"), ("#9C2A2A", "Wedding red")], [("Boxes of 10 to 50 for sangeet and return gifts.", "Offer")]),
    ])
    _dates(wid, t, CHAI_DATES)
    _activity(wid, viewer, t, {"content_items": 14, "tasks": 14, "leads": 4, "campaigns": 3})


# ------------------------------------------------------------------ Studio Neon (agency)
def _seed_neon(wid, viewer):
    t = S.today()
    d = lambda n: (t + dt.timedelta(days=n)).isoformat()
    ins("gtm_plans", dict(workspace_id=wid, name="Retainer package launch", product="Monthly content retainer (3 tiers)", stage="Launch", launch_date=d(-10), budget=50000, owner="Neon team",
                          goal="6 new retainer clients in 8 weeks", target_market="D2C founders, 10 to 50 people", positioning="A content team you do not have to manage",
                          pricing="₹45k / ₹80k / ₹1.4L a month", channels="LinkedIn, email, referrals"))
    for title, ch, fmt, st, off, client in [
            ("Launch teaser for Kesari Sweets", "Instagram", "Reel / Short", "In review", 0, "Kesari Sweets"), ("Diwali recap post for Kesari Sweets", "Instagram", "Carousel", "Published", -6, "Kesari Sweets"),
            ("Black Friday ads for Urban Loom", "Facebook", "Post", "Planned", 12, "Urban Loom"), ("Monthly newsletter for Urban Loom", "Email", "Newsletter", "Scheduled", 3, "Urban Loom"),
            ("Case study: FitFuel +38% signups", "LinkedIn", "Article", "Draft", 5, ""), ("Founder interview for FitFuel", "YouTube", "Video", "Planned", 9, "FitFuel"),
            ("Winter menu stories for Brew Lane", "Instagram", "Story", "Planned", 2, "Brew Lane"), ("Christmas offer for Brew Lane", "Instagram", "Post", "Planned", 30, "Brew Lane"),
            ("Year-end results deck", "LinkedIn", "Post", "Planned", 40, "")]:
        ins("content_items", dict(workspace_id=wid, title=title, channel=ch, format=fmt, status=st, publish_date=d(off), client=client, owner="Neha", copy="Draft copy ready for client review."))
    for title, who, off, pr, st in [("Send Kesari approval link", "Neha", 0, "High", "In progress"), ("Share Urban Loom ad budget", "Dev", 1, "High", "To do"), ("Prepare FitFuel monthly report", "Neha", 4, "Medium", "To do")] + \
            [(f"Task done {i}", "Dev" if i % 2 else "Neha", -i, "Medium", "Done") for i in range(1, 13)]:
        ins("tasks", dict(workspace_id=wid, title=title if not title.startswith("Task done") else ["Client call notes", "Invoice sent", "Reel edit", "Ad creatives", "Report draft", "Moodboard shared"][int(title.split()[-1]) % 6], assignee=who, due_date=d(off), priority=pr, status=st))
    for n, ind_, plan, val in [("Kesari Sweets", "Food", "Retainer", 85000), ("Urban Loom", "Fashion", "Retainer", 60000), ("FitFuel", "Health", "Retainer", 70000), ("Brew Lane", "Cafe", "Project", 30000)]:
        ins("clients", dict(workspace_id=wid, name=n, industry=ind_, plan=plan, monthly_value=val, status="Active", contact_person="Owner"))
    for n, c, stg, v in [("Rhea Kapoor", "Spice Route", "Opportunity", 90000), ("Imran Qureshi", "Fit Studio", "MQL", 55000), ("Pooja Rao", "Bloom Florist", "New", 30000), ("Dev Patel", "Home Needs", "SQL", 65000)]:
        ins("leads", dict(workspace_id=wid, name=n, company=c, stage=stg, value=v, source="Referral"))
    _kpi_series(wid, [("Client retainers (₹k)", 190, 11, 300), ("Pitch win rate %", 18, 1.4, 35), ("Posts delivered", 40, 3, 80)], t)
    ins("campaigns", dict(workspace_id=wid, name="Kesari Diwali launch", objective="Sales", channel="Instagram", start_date=d(-35), end_date=d(-6), budget=120000, spent=114000, status="Completed", client="Kesari Sweets", owner="Neha"))
    ins("campaigns", dict(workspace_id=wid, name="Urban Loom winter sale", objective="Sales", channel="Facebook", start_date=d(-5), end_date=d(25), budget=80000, spent=22000, status="Live", client="Urban Loom", owner="Dev"))
    ins("campaigns", dict(workspace_id=wid, name="Brew Lane Christmas", objective="Awareness", channel="Instagram", start_date=d(20), end_date=d(45), budget=40000, spent=0, status="Planning", client="Brew Lane", owner="Neha"))
    _boards(wid, [("Kesari festive", "Sweet boxes and diyas.", [(("#C2410C", "#FDBA74"), "Diya glow"), (("#7C2D12", "#FCD34D"), "Sweet box")], [("#C2410C", "Orange")], [("Warm and traditional.", "Tone")]),
                  ("Urban Loom winter", "Layers and earthy tones.", [(("#3F3F46", "#A1A1AA"), "Wool grey"), (("#7C2D12", "#FDBA74"), "Rust knit")], [("#3F3F46", "Charcoal")], [("Street-style shots.", "Direction")]),
                  ("Studio pitch deck look", "Our own look.", [(("#4C1D95", "#C4B5FD"), "Violet"), (("#0F766E", "#99F6E4"), "Teal")], [("#4C1D95", "Violet")], [("Bold type, lots of space.", "Style")])])
    _dates(wid, t, CHAI_DATES[:6])
    _activity(wid, viewer, t, {"content_items": 12, "tasks": 14, "leads": 4, "campaigns": 3})


# ------------------------------------------------------------------ Riya Creates (solo creator)
def _seed_riya(wid, viewer):
    t = S.today()
    d = lambda n: (t + dt.timedelta(days=n)).isoformat()
    ins("gtm_plans", dict(workspace_id=wid, name="Creator workshop launch", product="Live 4-week workshop", stage="Launch", launch_date=d(-8), budget=20000, owner="Riya",
                          goal="60 seats sold", target_market="Early-career creators, 20 to 30", positioning="Learn to earn from content, with live feedback",
                          pricing="₹4,999 per seat", channels="Instagram, newsletter, WhatsApp community"))
    for title, ch, fmt, st, off in [
            ("Get ready with me: winter wedding guest", "Instagram", "Reel / Short", "Scheduled", 0), ("Thrift haul: 5 sweaters under ₹500", "YouTube", "Video", "Planned", 3),
            ("Brand collab: Nykaa-style skincare reel", "Instagram", "Reel / Short", "In review", 1), ("Weekly newsletter: what I wore", "Email", "Newsletter", "Planned", 4),
            ("Winter skincare routine carousel", "Instagram", "Carousel", "Published", -4), ("Q&A story: your styling doubts", "Instagram", "Story", "Published", -2),
            ("Black Friday picks list", "Instagram", "Carousel", "Planned", 12), ("Christmas outfit ideas", "YouTube", "Video", "Planned", 28), ("Year in review reel", "Instagram", "Reel / Short", "Planned", 46),
            ("LinkedIn: how I price brand deals", "LinkedIn", "Post", "Draft", 6)]:
        ins("content_items", dict(workspace_id=wid, title=title, channel=ch, format=fmt, status=st, publish_date=d(off), owner="Riya", copy="Hook first, then the story.", cta="Link in bio"))
    for title, off, pr, st in [("Send invoice to skincare brand", 0, "High", "To do"), ("Edit thrift haul video", 2, "Medium", "In progress"), ("Reply to 3 brand enquiries", 1, "High", "To do")] + [(x, -i - 1, "Medium", "Done") for i, x in enumerate(
            ["Shoot reel b-roll", "Update media kit", "Pitch winter collab", "Post carousel", "Reply to comments", "Plan the month", "Book photographer", "Log October numbers", "Order props", "Update link in bio", "Film intro", "Edit GRWM"])]:
        ins("tasks", dict(workspace_id=wid, title=title, assignee="Riya", due_date=d(off), priority=pr, status=st))
    for n, c, stg, v in [("Glow Lab", "Skincare brand", "Opportunity", 45000), ("Thread & Co", "Fashion brand", "SQL", 30000), ("Urban Nest", "Home decor", "MQL", 25000), ("Zesty Snacks", "Food brand", "New", 20000)]:
        ins("leads", dict(workspace_id=wid, name=n, company=c, stage=stg, value=v, source="Instagram DM"))
    _kpi_series(wid, [("Followers", 41000, 650, 55000), ("Reel views", 120000, 7000, 200000), ("Brand deals (₹k)", 25, 3.5, 80)], t)
    ins("campaigns", dict(workspace_id=wid, name="Diwali outfit series", objective="Awareness", channel="Instagram", start_date=d(-30), end_date=d(-7), budget=0, spent=0, status="Completed", owner="Riya"))
    ins("campaigns", dict(workspace_id=wid, name="Winter styling series", objective="Awareness", channel="Instagram", start_date=d(-8), end_date=d(28), budget=0, spent=0, status="Live", owner="Riya"))
    ins("campaigns", dict(workspace_id=wid, name="Glow Lab paid collab", objective="Sales", channel="Instagram", start_date=d(6), end_date=d(20), budget=45000, spent=0, status="Planning", owner="Riya"))
    for n, plat, h, tier, f, st in [("Glow Lab", "Instagram", "glowlab.in", "Mid (100k-500k)", "180000", "Negotiating"), ("Thread & Co", "Instagram", "threadandco", "Micro (10k-100k)", "52000", "Contacted"), ("Studio Pixel", "YouTube", "studiopixel", "Micro (10k-100k)", "36000", "Shortlisted")]:
        ins("influencers", dict(workspace_id=wid, name=n, platform=plat, handle=h, tier=tier, followers=f, status=st, city="Delhi"))
    _boards(wid, [("Winter wardrobe", "Layers, textures, warm neutrals.", [(("#78350F", "#FCD34D"), "Camel coat"), (("#3F3F46", "#D4D4D8"), "Grey knit")], [("#78350F", "Camel")], [("Soft light, slow movement.", "Mood")]),
                  ("Brand deck look", "Media kit style.", [(("#BE185D", "#FBCFE8"), "Rose"), (("#4C1D95", "#DDD6FE"), "Plum")], [("#BE185D", "Rose")], [("Short, warm, direct.", "Voice")]),
                  ("Thrift haul set", "Colourful and cheap.", [(("#0F766E", "#99F6E4"), "Teal sweater"), (("#B45309", "#FDE68A"), "Mustard cardigan")], [("#0F766E", "Teal")], [("Show the price tags.", "Tip")])])
    _dates(wid, t, CHAI_DATES[:6])
    _activity(wid, viewer, t, {"content_items": 12, "tasks": 14, "leads": 4, "campaigns": 3})


SEEDERS = {"chai": _seed_chai, "neon": _seed_neon, "riya": _seed_riya}


def industry_variant(key):
    """A live sample workspace for any industry, so the landing page can show the visitor their own kind of business."""
    import industries as IND
    d = IND.INDUSTRIES.get(key)
    if not d or key == "general":
        return None
    label = d["label"].split(" (")[0].split(" / ")[0]
    return dict(slug=f"{key}-demo", name=f"Sample {label} (demo)", industry=key, label=f"Sample {label}", blurb=d.get("blurb", ""))


def _seed_industry(wid, viewer, key):
    import industries as IND
    t = S.today()
    d = lambda n: (t + dt.timedelta(days=n)).isoformat()
    ideas = (IND.INDUSTRIES[key].get("ideas") or [])[:9]
    sts = ["Published", "Published", "Scheduled", "In review", "Planned", "Planned", "Planned", "Draft", "Planned"]
    for i, idea in enumerate(ideas):
        _kind, title, ch, fmt = (list(idea) + ["", "", "Instagram", "Post"])[:4] if len(idea) < 4 else idea[:4]
        ins("content_items", dict(workspace_id=wid, title=str(title)[:120], channel=ch, format=fmt, status=sts[i], publish_date=d(i * 2 - 4), owner="You", copy="Hook first, then the story.", cta="Learn more"))
    for i, (title, off, pr, st) in enumerate([("Approve this week's posts", 0, "High", "To do"), ("Brief the designer", 1, "Medium", "In progress"), ("Check last week's numbers", 2, "Medium", "To do"), ("Reply to comments", -1, "Low", "Done")]):
        ins("tasks", dict(workspace_id=wid, title=title, assignee="You", due_date=d(off), priority=pr, status=st))
    _kpi_series(wid, [("Reach", 20000, 1100, 36000), ("Leads", 40, 4, 90), ("Engagement %", 3.1, .15, 5)], t)
    _activity(wid, viewer, t, {"content_items": 8, "tasks": 10, "leads": 3})


def ensure_demo(variant="chai"):
    """Returns (demo_user_id, workspace_id), creating or refreshing the chosen sample brand when it is missing or from an earlier day."""
    v = VARIANTS.get(variant) or industry_variant(variant) or VARIANTS["chai"]
    key = variant if (variant in VARIANTS or v is not VARIANTS["chai"]) else "chai"
    seed = SEEDERS.get(key) or (lambda wid, viewer, _k=key: _seed_industry(wid, viewer, _k))
    owner = _user(OWNER_EMAIL, v["label"])
    viewer = _user(DEMO_EMAIL, "Demo visitor")
    ws = q("SELECT * FROM workspaces WHERE slug=?", (v["slug"],), one=True)
    today = S.today().isoformat()
    if not ws:
        wid = ins("workspaces", dict(name=v["name"], slug=v["slug"], plan="team", plan_status="active", industry=v["industry"], owner_id=owner, ics_key=secrets.token_hex(6), hook_key=secrets.token_hex(12), period_end=today,
                                       review_url="https://g.page/r/demo-review-link/review"))
        ins("memberships", dict(workspace_id=wid, user_id=owner, role="owner"))
        ins("memberships", dict(workspace_id=wid, user_id=viewer, role="viewer"))
        S.seed_workspace(wid, v["industry"], False)
        seed(wid, viewer)
    else:
        wid = ws["id"]
        if (ws["period_end"] or "") != today:
            S.wipe_workspace_data(wid, keep_members=True)
            S.seed_workspace(wid, v["industry"], False)
            seed(wid, viewer)
            # A review link so the Reviews page shows its filled-in state rather than an empty form
            ex("UPDATE workspaces SET period_end=?, plan='team', plan_status='active', review_url=? WHERE id=?",
               (today, "https://g.page/r/demo-review-link/review", wid))
        if not q("SELECT id FROM memberships WHERE workspace_id=? AND user_id=?", (wid, viewer), one=True):
            ins("memberships", dict(workspace_id=wid, user_id=viewer, role="viewer"))
    return viewer, wid
