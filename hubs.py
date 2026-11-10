"""Hubs: eleven short sidebar entries, each one a set of tabs over the existing pages.

Nothing here owns data or routes. A hub is only a way of grouping pages that already exist, so every
feature, URL, role rule and plan lock keeps working. A tab is shown only when the page it points to is
already in the user's own navigation (role, industry and plan are decided there, not here)."""

# (label, endpoint, url_for kwargs, extra path prefixes that belong to this tab, "visible like" endpoint/key override)
HUBS = [
    dict(key="content", icon="✍️", label="Content & Calendar", lv=1, tabs=[
        ("📅 Calendar", "calendar_view", {}, [], None),
        ("🗂️ Board", "kanban", {"key": "content_items"}, [], None),
        ("📋 List", "m_list", {"key": "content_items"}, [], None),
        ("🗓️ Key dates", "m_list", {"key": "key_dates"}, [], None),
        ("📚 Library", "m_list", {"key": "assets"}, [], None),
        ("🔎 Keywords", "m_list", {"key": "keywords"}, [], None)]),
    dict(key="ideas", icon="💡", label="Idea Bank", lv=1, tabs=[
        ("💡 Idea bank", "ideas", {}, [], None)]),
    dict(key="brand", icon="🎨", label="Brand & Ideas", lv=1, tabs=[
        ("🖼️ Mood boards", "moodboards", {}, [], None),
        ("🎨 Brand kit", "m_list", {"key": "brand_kit"}, [], None),
        ("🔗 References", "m_list", {"key": "reference_links"}, [], None)]),
    dict(key="tasks", icon="✅", label="Tasks", lv=1, tabs=[
        ("✅ Tasks", "m_list", {"key": "tasks"}, [], None)]),
    dict(key="news", icon="🤖", label="AI & Market News", lv=1, tabs=[
        ("🤖 AI Studio", "ai_studio", {}, [], None),
        ("📡 Live news", "pulse_page", {}, [], None),
        ("⚡ Updates", "updates", {}, [], None),
        ("📰 Sources", "m_list", {"key": "feeds"}, [], None)]),
    dict(key="plan", icon="🧭", label="Strategy & Launch", lv=2, tabs=[
        ("🚀 Launch plans (GTM)", "m_list", {"key": "gtm_plans"}, [], None),
        ("🎯 Ideal customers", "m_list", {"key": "personas"}, [], None),
        ("🕵️ Competitors", "m_list", {"key": "competitors"}, [], None),
        ("✅ Launch checklist", "m_list", {"key": "launch_checklist"}, [], None)]),
    dict(key="campaigns", icon="📣", label="Campaigns & Events", lv=2, tabs=[
        ("📣 Campaigns", "m_list", {"key": "campaigns"}, [], None),
        ("🎪 Promotions", "m_list", {"key": "promotions"}, [], None),
        ("🎟️ Events", "m_list", {"key": "events"}, [], None),
        ("🧪 Experiments", "m_list", {"key": "experiments"}, [], None),
        ("🏷️ Trackable links", "utm", {}, ["/utm"], None)]),
    dict(key="sales", icon="🧲", label="Leads & Clients", lv=2, tabs=[
        ("🧲 Leads", "m_list", {"key": "leads"}, [], None),
        ("🏛️ Target companies", "m_list", {"key": "accounts"}, [], None),
        ("🤝 Clients", "m_list", {"key": "clients"}, [], None),
        ("🛒 Retail audits", "m_list", {"key": "retail_audits"}, [], None),
        ("📑 Client report", "report", {}, ["/report"], "rep")]),
    dict(key="results", icon="📈", label="Results & Insights", lv=2, tabs=[
        ("📈 Analytics", "analytics", {}, [], None),
        ("🎯 Results log", "m_list", {"key": "kpis"}, [], None),
        ("🩺 Marketing health", "marketing_health", {}, [], None),
        ("✨ Recap", "recap", {}, [], None)]),
    dict(key="people", icon="🤳", label="Influencers & PR", lv=3, tabs=[
        ("🤳 Influencers", "m_list", {"key": "influencers"}, ["/outreach"], None),
        ("🔭 Find influencers", "discover", {}, [], None),
        ("📰 PR & media", "m_list", {"key": "pr_contacts"}, [], None),
        ("🎤 Opportunities", "m_list", {"key": "pitches"}, [], None),
        ("✉️ Outreach templates", "m_list", {"key": "outreach_templates"}, [], None)]),
    dict(key="money", icon="💸", label="Creators & Payments", lv=3, tabs=[
        ("📊 Ops dashboard", "content_ops", {}, [], None),
        ("✍️ Creators", "m_list", {"key": "creators"}, [], None),
        ("📦 Orders", "m_list", {"key": "content_orders"}, [], None),
        ("💳 Rate card", "m_list", {"key": "rate_card"}, [], None),
        ("🧾 Invoices & payouts", "m_list", {"key": "payments"}, [], None)]),
    dict(key="team", icon="👥", label="Team", lv=3, tabs=[
        ("👑 Team hub", "team_hub", {}, [], "mgr"),
        ("👥 Team & roles", "ws.team", {}, [], "mgr"),
        ("🕘 Activity", "ws.activity", {}, [], "mgr"),
        ("🎉 Kudos wall", "kudos", {}, [], "nc")]),
]

# Default sidebar order: a day's work first, then planning and launching, then growing, then people.
ORDER = ["content", "tasks", "ideas", "brand", "plan", "campaigns", "people", "sales", "money", "results", "news", "team"]
HUBS.sort(key=lambda x: ORDER.index(x["key"]))
