"""Hubs: eleven short sidebar entries, each one a set of tabs over the existing pages.

Nothing here owns data or routes. A hub is only a way of grouping pages that already exist, so every
feature, URL, role rule and plan lock keeps working. A tab is shown only when the page it points to is
already in the user's own navigation (role, industry and plan are decided there, not here)."""

# (label, endpoint, url_for kwargs, extra path prefixes that belong to this tab, "visible like" endpoint/key override)
HUBS = [
    dict(key="content", icon="✍️", label="Content & Calendar", lv=1, tabs=[
        ("📅 Posts", "calendar_view", {}, ["/m/content_items", "/kanban/content_items"], None),
        ("🎬 Create", "studio.studio", {}, ["/grid"], None),
        ("📲 Publishing", "social.publishing", {}, [], "mgr"),
        ("🗓️ Key dates", "m_list", {"key": "key_dates"}, [], None),
        ("📚 Library", "m_list", {"key": "assets"}, [], None)]),
    dict(key="brand", icon="🎨", label="Brand & Ideas", lv=1, tabs=[
        ("🖼️ Mood boards", "moodboards", {}, [], None),
        ("🎨 Brand kit", "m_list", {"key": "brand_kit"}, [], None)]),
    dict(key="tasks", icon="✅", label="Tasks & Campaigns", lv=1, tabs=[
        ("✅ Tasks", "m_list", {"key": "tasks"}, [], None),
        ("📣 Campaigns", "campaigns_all", {}, ["/m/campaigns", "/kanban/campaigns", "/m/promotions", "/m/events"], "camp")]),
    dict(key="news", icon="🤖", label="AI & Market News", lv=1, tabs=[
        ("🤖 AI Studio", "ai_studio", {}, [], None),
        ("💡 Ideas", "ideas", {}, [], None),
        ("🧩 Templates", "templates_gallery", {}, [], "mgr"),
        ("📡 Live news", "pulse_page", {}, [], None)]),
    dict(key="plan", icon="🧭", label="Launch playbook", lv=1, tabs=[
        ("🎁 Launch deck", "studio.launch_deck", {}, ["/launch-deck"], None),
        ("🚀 Launch plans", "m_list", {"key": "gtm_plans"}, [], None),
        ("🎯 Ideal customers", "m_list", {"key": "personas"}, [], None),
        ("🕵️ Competitors", "m_list", {"key": "competitors"}, [], None),
        ("✅ Launch checklist", "m_list", {"key": "launch_checklist"}, [], None)]),
    dict(key="sales", icon="🧲", label="Leads & Clients", lv=2, tabs=[
        ("🧲 Leads", "m_list", {"key": "leads"}, ["/bio"], None),
        ("🤝 Clients", "m_list", {"key": "clients"}, [], None),
        ("⭐ Reviews", "bio.reviews", {}, [], "mgr")]),
    dict(key="results", icon="📈", label="Results & Insights", lv=2, tabs=[
        ("📈 Numbers", "analytics", {}, ["/m/kpis"], None),
        ("🎯 Results log", "m_list", {"key": "kpis"}, [], "hid"),
        ("📑 Report", "report", {}, ["/report"], "rep"),
        ("🎁 Wrapped", "deb.wrapped", {}, [], None),
        ("🏷️ Trackable links", "utm", {}, ["/utm"], None),
        ("🔎 Search keywords", "m_list", {"key": "keywords"}, [], None)]),
    dict(key="people", icon="🤳", label="Influencers & PR", lv=3, tabs=[
        ("🤳 Influencers", "m_list", {"key": "influencers"}, ["/outreach"], None),
        ("🔭 Find influencers", "discover", {}, [], None),
        ("📰 PR & media", "m_list", {"key": "pr_contacts"}, [], None),
        ("✉️ Outreach templates", "m_list", {"key": "outreach_templates"}, [], None)]),
    dict(key="money", icon="💸", label="Freelancers & Payments", lv=3, tabs=[
        ("📊 Creator overview", "content_ops", {}, [], None),
        ("✍️ Freelance creators", "m_list", {"key": "creators"}, [], None),
        ("🧾 Invoices & payouts", "m_list", {"key": "payments"}, [], None),
        ("📦 Content orders", "m_list", {"key": "content_orders"}, [], None),
        ("💳 Rate card", "m_list", {"key": "rate_card"}, [], None)]),
    dict(key="team", icon="👥", label="Team", lv=3, tabs=[
        ("✅ Approvals", "tm.approvals", {}, [], None),
        ("💬 Chat", "tm.chat", {}, ["/chat"], None),
        ("👑 Team hub", "team_hub", {}, ["/kudos"], "mgr"),
        ("🔒 Page access", "tm.access", {}, [], "mgr"),
        ("👥 Team & roles", "ws.team", {}, [], "mgr"),
        ("🕘 Activity", "ws.activity", {}, [], "mgr"),
        ("🎉 Team cheers", "kudos", {}, [], "nc")]),
]

# Default sidebar order: a day's work first, then planning and launching, then growing, then people.
ORDER = ["content", "tasks", "brand", "plan", "people", "sales", "money", "results", "team", "news"]      # AI help and market news come last: useful, not daily
HUBS.sort(key=lambda x: ORDER.index(x["key"]))


# What people say they want to do -> which hubs to show first. Content and Tasks are always shown.
# Hubs left out are not removed: they sit under "More tools" and the person can add them any time.
FOCUS = [
    ("content", "✍️", "Plan and post content", ["content", "brand", "tasks"]),
    ("launch", "🧭", "Launch a product or campaign", ["plan", "tasks"]),
    ("results", "📈", "See what is working", ["results"]),
    ("sales", "🧲", "Track leads and clients", ["sales"]),
    ("reach", "🤳", "Work with influencers and PR", ["people", "money"]),
    ("ai", "🤖", "AI help and market news", ["news"]),
    ("team", "👥", "Run a team", ["team"]),
]
ALWAYS = {"content", "tasks", "plan"}


def focus_keys(csv):
    """(hub keys to show, show "More tools") for a saved menu string. Empty = every hub, no "More tools".
    Tokens: "h:<hub>" a hub the person ticked, "more" the All tools entry; older saves hold the goal names above."""
    toks = [x for x in (csv or "").split(",") if x]
    if not toks:
        return None, False
    out = set(ALWAYS)
    for t in toks:
        if t.startswith("h:"):
            out.add(t[2:])
    for k, _i, _l, hubs in FOCUS:
        if k in toks:
            out.update(hubs)
    return out, "more" in toks


def goals_to_focus(goals):
    """Signup goals ("Plan and post content", ...) -> the hubs those goals need, as a saved menu string."""
    keys = set(ALWAYS)
    for k, _i, _l, hubs in FOCUS:
        if k in set(goals):
            keys.update(hubs)
    return clean_focus(keys)


def clean_focus(hub_keys, more=False):
    ok = {h["key"] for h in HUBS}
    out = ["h:" + k for k in ORDER if k in set(hub_keys) and k in ok]
    if more:
        out.append("more")
    return ",".join(out)


# Niche tools: not shown in any hub. They stay under "More tools" (same URLs, roles and plan locks) so a new person sees only what a typical marketer uses.
PRO_TABS = {("m_list", "pr_contacts")}

# Tabs shown under a quiet "More" chip so every hub opens with 2 to 4 clear choices. Nothing is removed: these pages keep their URLs, search entries and role rules.
MORE_TABS = {("m_list", "launch_checklist"), ("utm", None), ("m_list", "keywords"), ("m_list", "outreach_templates"),
             ("m_list", "content_orders"), ("m_list", "rate_card"),
             ("m_list", "key_dates"), ("m_list", "assets"),
             ("m_list", "events"), ("m_list", "pr_contacts"),
             ("m_list", "creators"),
             ("ws.activity", None), ("kudos", None),
             ("studio.grid", None), ("ideas", None)}   # fewer tabs on show; the rest sit under "More"


# Pages of one kind share ONE tab. The tab opens the first page and a small switch under the tab bar moves between them, so each hub shows 1 to 4 choices.
# Nothing is merged in the data: every page keeps its URL, search entry, role rule and plan lock.
GROUPS = [
    ("📅 Calendar", [("calendar_view", None), ("m_list", "key_dates")]),
    ("🤖 AI & ideas", [("ai_studio", None), ("ideas", None)]),
    ("🎨 Brand", [("moodboards", None), ("m_list", "brand_kit")]),
    ("📈 Results", [("analytics", None), ("m_list", "kpis"), ("report", None), ("deb.wrapped", None)]),
    ("🔗 Tracking & SEO", [("utm", None), ("m_list", "keywords")]),
    ("📡 News", [("pulse_page", None)]),
    ("🧭 Strategy", [("m_list", "gtm_plans"), ("m_list", "personas"), ("m_list", "competitors"), ("m_list", "launch_checklist")]),
    ("📣 Campaigns", [("campaigns_all", None)]),
    ("🤳 Influencers & PR", [("m_list", "influencers"), ("discover", None), ("m_list", "pr_contacts"), ("m_list", "outreach_templates")]),
    ("💸 Creators & pay", [("content_ops", None), ("m_list", "creators"), ("m_list", "payments"), ("m_list", "content_orders"), ("m_list", "rate_card")]),
    ("💬 Chat & approvals", [("tm.chat", None), ("tm.approvals", None)]),
    ("👑 Team hub", [("team_hub", None)]),
    ("👥 People & activity", [("ws.team", None), ("tm.access", None), ("ws.activity", None)]),
]

# Pages that no longer have a menu entry of their own: they are one button away from the page they belong to, and stay in search.
FOLDED = [("m_list", "promotions"), ("m_list", "events"),      # Launch plans has its own home in Launch playbook
          
          ("ws.activity", None), ("kudos", None), ("discover", None), ("studio.grid", None)]
