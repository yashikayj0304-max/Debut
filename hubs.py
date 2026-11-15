"""Hubs: eleven short sidebar entries, each one a set of tabs over the existing pages.

Nothing here owns data or routes. A hub is only a way of grouping pages that already exist, so every
feature, URL, role rule and plan lock keeps working. A tab is shown only when the page it points to is
already in the user's own navigation (role, industry and plan are decided there, not here)."""

# (label, endpoint, url_for kwargs, extra path prefixes that belong to this tab, "visible like" endpoint/key override)
HUBS = [
    dict(key="content", icon="✍️", label="Content & Calendar", lv=1, tabs=[
        ("📅 Posts", "calendar_view", {}, ["/m/content_items", "/kanban/content_items"], None),
        ("🎬 Create", "studio.studio", {}, [], None),
        ("🎯 Promo ideas", "studio.promos", {}, [], None),
        ("📡 Radar", "deb.radar", {}, [], None),
        ("🧩 Grid", "studio.grid", {}, [], None),
        ("💡 Idea bank", "ideas", {}, [], None),
        ("🗓️ Key dates", "m_list", {"key": "key_dates"}, [], None),
        ("📚 Library", "m_list", {"key": "assets"}, [], None)]),
    dict(key="brand", icon="🎨", label="Brand & Ideas", lv=1, tabs=[
        ("🖼️ Mood boards", "moodboards", {}, [], None),
        ("🎨 Brand kit", "m_list", {"key": "brand_kit"}, [], None),
        ("📎 References", "m_list", {"key": "reference_links"}, [], None),
        ("🔗 Link in bio", "bio.edit", {}, [], None)]),
    dict(key="tasks", icon="✅", label="Tasks", lv=1, tabs=[
        ("✅ Tasks", "m_list", {"key": "tasks"}, [], None)]),
    dict(key="news", icon="🤖", label="AI & Market News", lv=1, tabs=[
        ("🤖 AI Studio", "ai_studio", {}, [], None),
        ("📡 Live news", "pulse_page", {}, [], None)]),
    dict(key="plan", icon="🧭", label="Strategy & Launch", lv=2, tabs=[
        ("🚀 Launch plans", "m_list", {"key": "gtm_plans"}, [], None),
        ("🎯 Ideal customers", "m_list", {"key": "personas"}, [], None),
        ("🕵️ Competitors", "m_list", {"key": "competitors"}, [], None)]),
    dict(key="campaigns", icon="📣", label="Campaigns", lv=2, tabs=[
        ("📣 Campaigns", "campaigns_all", {}, ["/m/campaigns", "/kanban/campaigns", "/m/promotions", "/m/events", "/m/gtm_plans"], "camp")]),
    dict(key="sales", icon="🧲", label="Leads & Clients", lv=2, tabs=[
        ("🧲 Leads", "m_list", {"key": "leads"}, [], None),
        ("🤝 Clients", "m_list", {"key": "clients"}, [], None)]),
    dict(key="results", icon="📈", label="Results & Insights", lv=2, tabs=[
        ("📈 Numbers", "analytics", {}, ["/m/kpis"], None),
        ("🎯 Results log", "m_list", {"key": "kpis"}, [], "hid"),
        ("📑 Report", "report", {}, ["/report"], "rep"),
        ("🎁 Wrapped", "deb.wrapped", {}, [], None)]),
    dict(key="people", icon="🤳", label="Influencers & PR", lv=3, tabs=[
        ("🤳 Influencers", "m_list", {"key": "influencers"}, ["/outreach"], None),
        ("🔭 Find influencers", "discover", {}, [], None),
        ("📰 PR & media", "m_list", {"key": "pr_contacts"}, [], None)]),
    dict(key="money", icon="💸", label="Creators & Payments", lv=3, tabs=[
        ("📊 Creator overview", "content_ops", {}, [], None),
        ("✍️ Creators", "m_list", {"key": "creators"}, [], None),
        ("🧾 Invoices & payouts", "m_list", {"key": "payments"}, [], None)]),
    dict(key="team", icon="👥", label="Team", lv=3, tabs=[
        ("✅ Approvals", "tm.approvals", {}, [], None),
        ("💬 Chat", "tm.chat", {}, ["/chat"], None),
        ("👑 Team hub", "team_hub", {}, [], "mgr"),
        ("🔒 Page access", "tm.access", {}, [], "mgr"),
        ("👥 Team & roles", "ws.team", {}, [], "mgr"),
        ("🕘 Activity", "ws.activity", {}, [], "mgr"),
        ("🎉 Team cheers", "kudos", {}, [], "nc")]),
]

# Default sidebar order: a day's work first, then planning and launching, then growing, then people.
ORDER = ["content", "tasks", "brand", "plan", "campaigns", "people", "sales", "money", "results", "news", "team"]
HUBS.sort(key=lambda x: ORDER.index(x["key"]))


# What people say they want to do -> which hubs to show first. Content and Tasks are always shown.
# Hubs left out are not removed: they sit under "More tools" and the person can add them any time.
FOCUS = [
    ("content", "✍️", "Plan and post content", ["content", "brand", "tasks"]),
    ("launch", "🧭", "Launch a product or campaign", ["plan", "campaigns"]),
    ("results", "📈", "See what is working", ["results"]),
    ("sales", "🧲", "Track leads and clients", ["sales"]),
    ("reach", "🤳", "Work with influencers and PR", ["people", "money"]),
    ("ai", "🤖", "AI help and market news", ["news"]),
    ("team", "👥", "Run a team", ["team"]),
]
ALWAYS = {"content", "tasks"}


def focus_keys(csv):
    """The hub keys to show first for a saved focus string ("" = show everything)."""
    pick = [x for x in (csv or "").split(",") if x]
    if not pick:
        return None
    out = set(ALWAYS)
    for k, _i, _l, hubs in FOCUS:
        if k in pick:
            out.update(hubs)
    return out


def clean_focus(vals):
    ok = {k for k, *_ in FOCUS}
    return ",".join(k for k, *_ in FOCUS if k in set(vals) and k in ok)


# Niche tools: not shown in any hub. They stay under "More tools" (same URLs, roles and plan locks) so a new person sees only what a typical marketer uses.
PRO_TABS = {("utm", None),
            ("m_list", "pr_contacts")}

# Tabs shown under a quiet "More" chip so every hub opens with 2 to 4 clear choices. Nothing is removed: these pages keep their URLs, search entries and role rules.
MORE_TABS = {("m_list", "key_dates"), ("m_list", "assets"),
             ("m_list", "events"), ("m_list", "pr_contacts"),
             ("m_list", "creators"),
             ("ws.activity", None), ("kudos", None),
             ("studio.grid", None), ("ideas", None), ("m_list", "reference_links")}   # fewer tabs on show; the rest sit under "More"


# Pages of one kind share ONE tab. The tab opens the first page and a small switch under the tab bar moves between them, so each hub shows 1 to 4 choices.
# Nothing is merged in the data: every page keeps its URL, search entry, role rule and plan lock.
GROUPS = [
    ("📅 Calendar", [("calendar_view", None), ("m_list", "key_dates")]),
    ("🎬 Create", [("studio.studio", None), ("studio.promos", None), ("deb.radar", None), ("studio.grid", None)]),
    ("💡 Ideas & library", [("ideas", None), ("m_list", "assets")]),
    ("🎨 Brand", [("moodboards", None), ("m_list", "brand_kit"), ("m_list", "reference_links"), ("bio.edit", None)]),
    ("📈 Results", [("analytics", None), ("report", None), ("deb.wrapped", None)]),
    ("📡 News", [("pulse_page", None)]),
    ("🧭 Strategy", [("m_list", "gtm_plans"), ("m_list", "personas"), ("m_list", "competitors")]),
    ("📣 Campaigns", [("campaigns_all", None)]),
    ("🧲 Leads & clients", [("m_list", "leads"), ("m_list", "clients")]),
    ("🤳 Influencers & PR", [("m_list", "influencers"), ("discover", None), ("m_list", "pr_contacts")]),
    ("💸 Creators & pay", [("content_ops", None), ("m_list", "creators"), ("m_list", "payments")]),
    ("👥 Team", [("tm.approvals", None), ("tm.chat", None), ("team_hub", None), ("tm.access", None), ("ws.team", None), ("ws.activity", None), ("kudos", None)]),
]

# Pages that no longer have a menu entry of their own: they are one button away from the page they belong to, and stay in search.
FOLDED = [("m_list", "promotions"), ("m_list", "events"), ("m_list", "gtm_plans"),
          ("ws.activity", None), ("kudos", None), ("discover", None)]
