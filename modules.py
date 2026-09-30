"""Module (table) definitions, seed data and AI task prompts."""
from collections import OrderedDict

PLATFORMS = ["Instagram", "YouTube", "LinkedIn", "X / Twitter", "Facebook", "Threads", "Pinterest", "ShareChat / Moj", "Snapchat",
             "Podcast", "Blog / Website", "Newsletter / Substack", "WhatsApp Channel", "Other"]
SKILLS_HINT = "Blog writer, Copywriter, SEO specialist, Scriptwriter, Video editor, Videographer, Graphic designer, Social media manager, Translator, Editor / proofreader, Voice-over artist, Photographer"
ORDER_TYPES = ["Blog / Article", "Website copy", "Social media pack", "Video script", "Video production", "Email / newsletter", "Whitepaper / ebook",
               "Case study", "Press release", "Design / creatives", "Translation / localisation", "Product descriptions", "Ad copy"]
ORDER_SKILL = {"Blog / Article": "Blog writer", "Website copy": "Copywriter", "Social media pack": "Social media manager", "Video script": "Scriptwriter",
               "Video production": "Video editor", "Email / newsletter": "Copywriter", "Whitepaper / ebook": "Blog writer", "Case study": "Blog writer",
               "Press release": "Copywriter", "Design / creatives": "Graphic designer", "Translation / localisation": "Translator",
               "Product descriptions": "Copywriter", "Ad copy": "Copywriter"}
ORDER_STATUS = ["Brief received", "Assigned", "In draft", "Editing / QA", "Client review", "Revision", "Approved", "Delivered", "Invoiced", "Cancelled"]
DONE_ORDER = ("Approved", "Delivered", "Invoiced")
ONLINE_CHECK = [("Define goal, audience and success metrics", -30), ("Choose platform and test tech (audio, video, streaming)", -21),
    ("Build registration page with UTM tracking", -21), ("Confirm speakers/guests and run-of-show", -14), ("Launch promotion: social, email, WhatsApp, influencers", -14),
    ("Send reminders (7 days, 1 day, 1 hour)", -7), ("Dry run + moderator and Q&A briefing", -2), ("Go live: monitor chat, capture leads", 0),
    ("Send replay + thank-you + offer within 24h", 1), ("Report: attendance, leads, cost per lead, learnings", 5)]
OFFLINE_CHECK = [("Define goal, budget and footfall/lead targets", -45), ("Book venue, permissions and licences", -40), ("Get vendor quotes: setup, branding, POSM, sound", -30),
    ("Design and print collateral, standees, sampling material", -20), ("Recruit and train promoters / brand ambassadors", -14),
    ("Local promotion: influencers, hyperlocal ads, WhatsApp", -14), ("Stock, sample logistics and insurance", -7), ("Site recce, safety and fire compliance", -3),
    ("Event day: setup, live coverage, lead capture", 0), ("Teardown, reconcile spend, thank-you follow-ups", 1), ("Report: footfall, samples, leads, sales lift, ROI", 5)]
OUTREACH = [
 ("Influencer - collab email (first touch)", "Email", "Influencer", "Collab opportunity with {brand}",
  "Hi {name},\n\nI'm {sender} from {brand}. We love your {platform} content, especially how you connect with your audience.\n\nWe're running {campaign} and think you'd be a great fit. We'd like to explore a collaboration (paid or product-led - happy to discuss what works for you).\n\nCould you share your rate card, average reach and best-performing formats? A short call this week works too.\n\nThanks,\n{sender}"),
 ("Influencer - Instagram DM (short)", "Instagram DM", "Influencer", "",
  "Hi {name}! Big fan of your content 🙌 I'm {sender} from {brand}. We have a collab for {campaign} that fits your audience. Can I share the details here or on email?"),
 ("Influencer - follow-up (day 4)", "Email", "Influencer", "Re: Collab opportunity with {brand}",
  "Hi {name},\n\nJust following up on my note about {campaign}. Happy to share the brief and timelines - even a quick 'interested' helps.\n\nThanks,\n{sender}"),
 ("Creator / freelancer - marketplace invite", "Email", "Creator / freelancer", "Write/create for {brand}",
  "Hi {name},\n\nWe're building a vetted creator network at {brand} and your portfolio stood out. We work with briefs across blogs, social, scripts and design, with clear rate cards and timely payouts.\n\nIf interested, please share 2-3 recent samples, your rate per piece/word and availability. A short paid test may follow.\n\nRegards,\n{sender}"),
 ("PR - media pitch", "Email", "PR / Media", "Story idea: {campaign}",
  "Hi {name},\n\nSince you cover this beat, thought this might interest you: {campaign} from {brand}. Happy to share a press note, visuals, and arrange a spokesperson.\n\nBest,\n{sender}"),
 ("Event - guest / speaker invite", "Email", "Event guest", "Invitation: {campaign}",
  "Hi {name},\n\nWe'd love to have you at {campaign}, hosted by {brand}. It's a great way to connect with our community and we'll handle all logistics. Could I share date, format and what we have in mind?\n\nWarm regards,\n{sender}"),
 ("Retail partner - in-store promotion", "WhatsApp", "Retail partner", "",
  "Hi {name}, this is {sender} from {brand}. We're running {campaign} in your area with margins/visibility support. Can I share the scheme details and display material?"),
]

def F(n, l, t="text", o=None):
    return (n, l, t, o or [])

STATUS = ["Idea", "Planned", "In progress", "Review", "Approved", "Scheduled", "Published", "On hold"]
TASK_STATUS = ["Backlog", "To do", "In progress", "Review", "Done"]
PRIORITY = ["Low", "Medium", "High", "Urgent"]
CHANNELS = ["Instagram", "LinkedIn", "X / Twitter", "YouTube", "Facebook", "WhatsApp", "Email",
            "Blog / SEO", "Website", "Paid Social", "Paid Search", "Influencer", "PR",
            "Events / Webinar", "Retail / Trade", "Other"]
FORMATS = ["Post", "Carousel", "Reel / Short", "Video", "Story", "Article", "Newsletter", "Ad",
           "Press release", "Webinar", "Landing page", "Thread"]
PHASES = ["Research", "Positioning", "Product & Pricing", "Channels", "Content",
          "Sales & Enablement", "Launch", "Post-launch"]

MODULES = OrderedDict([
    ("gtm_plans", dict(title="GTM Plans", icon="🚀", group="Strategy", desc="One record per product/launch: goal, market, positioning, pricing, channels, budget.",
        fields=[F("name", "Plan name"), F("product", "Product / offering"), F("stage", "Stage", "select", ["Research", "Planning", "Pre-launch", "Launch", "Post-launch", "Scale"]),
                F("launch_date", "Launch date", "date"), F("goal", "Primary goal & success metric", "textarea"), F("target_market", "Target market / segments", "textarea"),
                F("positioning", "Positioning & value proposition", "textarea"), F("pricing", "Pricing & packaging", "textarea"), F("channels", "Channel mix", "textarea"),
                F("budget", "Budget (total)", "number"), F("owner", "Owner"), F("risks", "Risks & dependencies", "textarea"), F("notes", "Notes", "textarea")],
        cols=["name", "product", "stage", "launch_date", "budget", "owner"], filter="stage")),
    ("personas", dict(title="Personas / ICP", icon="🎯", group="Strategy", desc="Ideal customer profiles and buyer personas.",
        fields=[F("name", "Persona name"), F("role", "Role / who they are"), F("industry", "Industry / segment"), F("company_size", "Company / household size"),
                F("pain_points", "Pain points", "textarea"), F("goals", "Goals / jobs to be done", "textarea"), F("objections", "Objections", "textarea"),
                F("channels", "Where they spend time", "textarea"), F("buying_triggers", "Buying triggers", "textarea")],
        cols=["name", "role", "industry", "channels"])),
    ("competitors", dict(title="Competitors", icon="🕵️", group="Strategy", desc="Competitive intelligence & battlecards.",
        fields=[F("name", "Competitor"), F("website", "Website", "url"), F("positioning", "Positioning", "textarea"), F("strengths", "Strengths", "textarea"),
                F("weaknesses", "Weaknesses", "textarea"), F("pricing", "Pricing"), F("differentiator", "How we win", "textarea"), F("last_checked", "Last checked", "date")],
        cols=["name", "website", "pricing", "last_checked"])),
    ("brand_kit", dict(title="Brand Kit", icon="🎨", group="Strategy", desc="Colours, fonts, voice, logo rules, do's and don'ts.",
        fields=[F("name", "Name"), F("kind", "Kind", "select", ["Colour", "Font", "Voice & tone", "Logo rule", "Guideline", "Tagline", "Other"]),
                F("value", "Value (hex / font / text)"), F("notes", "Notes", "textarea")],
        cols=["name", "kind", "value"], filter="kind")),
    ("launch_checklist", dict(title="Launch Checklist", icon="✅", group="Strategy", desc="Phase-by-phase GTM checklist (pre-loaded).",
        fields=[F("item", "Item"), F("phase", "Phase", "select", PHASES), F("owner", "Owner"), F("due_date", "Due", "date"),
                F("status", "Status", "select", ["To do", "In progress", "Done"]), F("notes", "Notes", "textarea")],
        cols=["item", "phase", "owner", "due_date", "status"], filter="phase", kanban="status")),
    ("content_items", dict(title="Content Items", icon="📝", group="Content", desc="Every post, video, email and article. Appears on the calendar by publish date.",
        fields=[F("title", "Title / hook"), F("channel", "Channel", "select", CHANNELS), F("format", "Format", "select", FORMATS), F("status", "Status", "select", STATUS),
                F("publish_date", "Publish date", "date"), F("campaign", "Campaign"), F("persona", "Target persona"), F("owner", "Owner"), F("client", "Client (shows in that client's portal)"),
                F("copy", "Copy / script", "textarea"), F("cta", "Call to action"), F("hashtags", "Hashtags / keywords"), F("asset_url", "Asset / design link", "url"), F("notes", "Notes", "textarea")],
        cols=["title", "channel", "format", "status", "publish_date", "owner"], filter="status", kanban="status")),
    ("assets", dict(title="Content Library", icon="📚", group="Content", desc="Saved copy, templates and AI outputs.",
        fields=[F("title", "Title"), F("type", "Type"), F("channel", "Channel", "select", CHANNELS), F("status", "Status", "select", ["Draft", "Approved", "Archived"]),
                F("campaign", "Campaign"), F("body", "Content", "textarea")],
        cols=["title", "type", "channel", "status"], filter="status")),
    ("reference_links", dict(title="Reference Links", icon="🔗", group="Content", desc="Inspiration, benchmarks, tools and articles.",
        fields=[F("title", "Title"), F("url", "URL", "url"), F("category", "Category", "select", ["Inspiration", "Competitor", "Benchmark", "Article", "Tool", "Template", "Case study", "Design", "Ad library", "Other"]),
                F("tags", "Tags"), F("notes", "Notes", "textarea"), F("favorite", "Favourite", "select", ["No", "Yes"])],
        cols=["title", "url", "category", "tags", "favorite"], filter="category")),
    ("keywords", dict(title="SEO Keywords", icon="🔎", group="Content", desc="Keyword targets and rank tracking.",
        fields=[F("keyword", "Keyword"), F("volume", "Monthly volume", "number"), F("difficulty", "Difficulty (0-100)", "number"),
                F("intent", "Intent", "select", ["Informational", "Commercial", "Transactional", "Navigational"]), F("target_url", "Target URL", "url"),
                F("position", "Current position", "number"), F("status", "Status", "select", ["Idea", "Targeting", "Ranking", "Won", "Dropped"])],
        cols=["keyword", "volume", "difficulty", "intent", "position", "status"], filter="intent")),
    ("campaigns", dict(title="Campaigns", icon="📣", group="Campaigns", desc="Campaign plans with budget and KPI targets.",
        fields=[F("name", "Campaign"), F("objective", "Objective", "select", ["Awareness", "Consideration", "Leads", "Sales", "Retention", "Advocacy"]),
                F("channel", "Main channel", "select", CHANNELS), F("start_date", "Start", "date"), F("end_date", "End", "date"), F("budget", "Budget", "number"),
                F("spent", "Spent so far", "number"), F("owner", "Owner"), F("client", "Client (shows in that client's portal)"), F("status", "Status", "select", ["Planning", "Live", "Paused", "Completed", "Cancelled"]),
                F("kpi_target", "KPI target"), F("brief", "Brief", "textarea"), F("learnings", "Learnings / post-mortem", "textarea")],
        cols=["name", "objective", "channel", "start_date", "budget", "spent", "status"], filter="status", kanban="status")),
    ("influencers", dict(title="Influencers", icon="🤳", group="Campaigns", desc="Prospective and active influencers across every platform. Use Discover Influencers to find prospects, then Draft outreach from a record.",
        fields=[F("name", "Name"), F("platform", "Platform", "select", PLATFORMS), F("handle", "Handle"), F("profile_url", "Profile URL", "url"),
                F("tier", "Tier", "select", ["Nano (<10k)", "Micro (10k-100k)", "Mid (100k-500k)", "Macro (500k-1M)", "Mega (1M+)"]),
                F("followers", "Followers", "number"), F("engagement_rate", "Engagement %", "number"), F("avg_views", "Avg views / reach", "number"),
                F("niche", "Niche"), F("city", "City"), F("language", "Language"), F("email", "Email (business)"), F("phone", "Phone / WhatsApp"),
                F("rate", "Rate (₹)", "number"), F("past_brand_work", "Past brand work", "textarea"), F("fit_score", "Brand fit (1-10)", "number"),
                F("status", "Status", "select", ["Prospect", "Shortlisted", "Contacted", "Negotiating", "Booked", "Delivered", "Rejected"]),
                F("last_contacted", "Last contacted", "date"), F("next_followup", "Next follow-up", "date"), F("notes", "Notes", "textarea")],
        cols=["name", "platform", "tier", "followers", "engagement_rate", "fit_score", "status", "next_followup"], filter="status", kanban="status")),
    ("pr_contacts", dict(title="PR & Media", icon="📰", group="Campaigns", desc="Journalists, outlets and pitches.",
        fields=[F("name", "Name"), F("outlet", "Outlet"), F("beat", "Beat"), F("email", "Email"), F("last_contacted", "Last contacted", "date"),
                F("status", "Status", "select", ["Cold", "Pitched", "Responded", "Covered", "Do not contact"]), F("notes", "Notes", "textarea")],
        cols=["name", "outlet", "beat", "last_contacted", "status"], filter="status")),
    ("experiments", dict(title="Experiments", icon="🧪", group="Campaigns", desc="A/B tests and growth experiments.",
        fields=[F("hypothesis", "Hypothesis"), F("channel", "Channel", "select", CHANNELS), F("metric", "Success metric"), F("variant_a", "Variant A", "textarea"),
                F("variant_b", "Variant B", "textarea"), F("status", "Status", "select", ["Idea", "Running", "Concluded"]), F("result", "Result / decision", "textarea")],
        cols=["hypothesis", "channel", "metric", "status"], filter="status")),
    ("leads", dict(title="Leads", icon="🧲", group="Growth", desc="Lightweight lead tracker and funnel.",
        fields=[F("name", "Name"), F("company", "Company"), F("email", "Email"), F("phone", "Phone"), F("source", "Source / UTM"),
                F("stage", "Stage", "select", ["New", "MQL", "SQL", "Opportunity", "Won", "Lost"]), F("value", "Deal value", "number"), F("next_step", "Next step"), F("notes", "Notes", "textarea")],
        cols=["name", "company", "source", "stage", "value", "next_step"], filter="stage", kanban="stage")),
    ("kpis", dict(title="KPI Log", icon="📈", group="Growth", desc="Log metrics over time; charts on the Analytics page.",
        fields=[F("metric", "Metric (e.g. Website visits)"), F("channel", "Channel"), F("period", "Date", "date"), F("value", "Actual", "number"),
                F("target", "Target", "number"), F("campaign", "Campaign"), F("notes", "Notes")],
        cols=["metric", "channel", "period", "value", "target", "campaign"])),
    ("tasks", dict(title="Tasks", icon="🗂️", group="Growth", desc="Marketing to-dos with owners and due dates.",
        fields=[F("title", "Task"), F("description", "Description", "textarea"), F("assignee", "Assignee"), F("due_date", "Due", "date"),
                F("priority", "Priority", "select", PRIORITY), F("status", "Status", "select", TASK_STATUS), F("related", "Related to (campaign / plan)")],
        cols=["title", "assignee", "due_date", "priority", "status"], filter="status", kanban="status")),
    ("key_dates", dict(title="Key Dates", icon="🗓️", group="Content", desc="Festivals, industry events and launches shown on the calendar. Verify moving dates.",
        fields=[F("name", "Name"), F("date", "Date", "date"), F("kind", "Type", "select", ["Festival", "Industry event", "Sale / shopping", "Internal", "Awareness day"]), F("notes", "Notes")],
        cols=["name", "date", "kind"], filter="kind")),
    ("feeds", dict(title="News Sources", icon="📡", group="Intelligence", desc="RSS/Atom feeds used on the Latest Updates page. Google News search URLs work too.",
        fields=[F("name", "Name"), F("url", "Feed URL", "url"), F("category", "Category", "select", ["Marketing", "SEO / Search", "Social", "Industry", "Competitors", "FMCG / Retail", "Tech / AI", "Other"])],
        cols=["name", "category", "url"], filter="category")),
    ("clients", dict(title="Clients", icon="🏢", group="Content Ops", desc="Brands / accounts you produce content for.",
        fields=[F("name", "Client / brand"), F("industry", "Industry"), F("contact_person", "Contact person"), F("email", "Email"), F("phone", "Phone"),
                F("plan", "Plan / retainer"), F("monthly_value", "Monthly value (₹)", "number"), F("status", "Status", "select", ["Lead", "Active", "Paused", "Churned"]), F("notes", "Notes", "textarea")],
        cols=["name", "industry", "contact_person", "monthly_value", "status"], filter="status")),
    ("creators", dict(title="Creator Network", icon="✍️", group="Content Ops", desc="Vetted writers, designers, video editors and social managers (your freelancer marketplace). Share the Apply form to onboard.",
        fields=[F("name", "Name"), F("email", "Email"), F("phone", "Phone"), F("skills", "Skills (comma separated: " + SKILLS_HINT + ")"), F("niches", "Niches / industries"),
                F("languages", "Languages"), F("city", "City"), F("portfolio_url", "Portfolio URL", "url"), F("rate", "Rate (₹ per word / piece)"),
                F("turnaround", "Typical turnaround"), F("test_score", "Test score (0-100)", "number"), F("rating", "Avg rating (1-5)", "number"),
                F("status", "Status", "select", ["Applied", "Test sent", "Vetted", "Active", "Paused", "Blacklisted"]), F("notes", "Notes", "textarea")],
        cols=["name", "skills", "languages", "rate", "rating", "status"], filter="status", kanban="status")),
    ("content_orders", dict(title="Content Orders", icon="📦", group="Content Ops", desc="Client content projects from brief to invoice: assign creators, QA, revisions, delivery and margin.",
        fields=[F("title", "Order title"), F("client", "Client"), F("type", "Content type", "select", ORDER_TYPES), F("brief", "Brief", "textarea"), F("keywords", "Keywords / SEO"),
                F("word_count", "Word count / units", "number"), F("tone", "Tone & style guide"), F("creator", "Assigned creator"), F("due_date", "Due date", "date"),
                F("price_client", "Client price (₹)", "number"), F("cost_creator", "Creator cost (₹)", "number"),
                F("status", "Status", "select", ORDER_STATUS), F("revisions", "Revision rounds", "number"), F("quality_score", "Quality score (1-10)", "number"),
                F("delivery_link", "Delivery link", "url"), F("feedback", "QA / client feedback", "textarea")],
        cols=["title", "client", "type", "creator", "due_date", "price_client", "status"], filter="status", kanban="status")),
    ("rate_card", dict(title="Rate Card", icon="💳", group="Content Ops", desc="Your service catalogue and prices for clients.",
        fields=[F("service", "Service"), F("unit", "Unit", "select", ["per word", "per piece", "per 1000 words", "per video", "per month", "per project"]),
                F("price", "Price (₹)", "number"), F("turnaround", "Turnaround"), F("includes", "What's included", "textarea")],
        cols=["service", "unit", "price", "turnaround"])),
    ("payments", dict(title="Invoices & Payouts", icon="🧾", group="Content Ops", desc="Client invoices (money in) and creator/influencer payouts (money out).",
        fields=[F("direction", "Direction", "select", ["Client invoice (in)", "Creator payout (out)", "Influencer payout (out)", "Vendor bill (out)"]),
                F("party", "Client / payee"), F("reference", "Invoice no. / order"), F("amount", "Amount (₹)", "number"), F("issue_date", "Issue date", "date"),
                F("due_date", "Due date", "date"), F("status", "Status", "select", ["Draft", "Sent", "Pending", "Paid", "Overdue"]), F("notes", "Notes (GST, TDS, UTR)", "textarea")],
        cols=["direction", "party", "reference", "amount", "due_date", "status"], filter="status")),
    ("promotions", dict(title="Promotions", icon="🏷️", group="Promotions & Events", desc="Consumer and trade promotions, online and offline: offers, coupons, contests, sampling, schemes. Start/end dates show on the calendar.",
        fields=[F("name", "Promotion"), F("type", "Type", "select", ["Discount / % off", "BOGO", "Combo / bundle", "Cashback", "Coupon code", "Contest / giveaway", "Referral", "Loyalty points", "Sampling", "Free gift", "Flash sale", "Trade scheme", "Festival offer"]),
                F("mode", "Mode", "select", ["Online", "Offline", "Both"]), F("channel", "Where it runs (site, app, marketplace, stores, social)"),
                F("start_date", "Start", "date"), F("end_date", "End", "date"), F("mechanic", "Mechanic (how it works)", "textarea"), F("code", "Coupon code"),
                F("discount_pct", "Discount %", "number"), F("budget", "Budget (₹)", "number"), F("spend", "Spend so far (₹)", "number"), F("target_units", "Target units", "number"),
                F("actual_units", "Actual units", "number"), F("revenue", "Revenue attributed (₹)", "number"), F("terms", "Terms & conditions", "textarea"), F("owner", "Owner"),
                F("status", "Status", "select", ["Idea", "Planned", "Approved", "Live", "Ended"]), F("learnings", "Learnings", "textarea")],
        cols=["name", "type", "mode", "start_date", "end_date", "budget", "revenue", "status"], filter="status", kanban="status")),
    ("events", dict(title="Events", icon="🎪", group="Promotions & Events", desc="Online (webinar, live, AMA) and offline (pop-up, sampling, roadshow, trade show) events. Open an event to auto-add a checklist to Tasks.",
        fields=[F("name", "Event"), F("mode", "Mode", "select", ["Online", "Offline", "Hybrid"]),
                F("type", "Type", "select", ["Webinar", "Instagram / YouTube Live", "X Space / Twitter chat", "AMA", "Podcast episode", "Workshop", "Product launch", "Pop-up store", "Sampling drive", "Roadshow", "Trade show / expo", "Mall activation", "College fest", "Influencer meetup", "Contest / giveaway", "Retail in-store activation"]),
                F("date", "Date", "date"), F("time", "Time"), F("venue", "Venue / city"), F("platform_link", "Platform / registration link", "url"), F("audience", "Target audience"),
                F("expected_attendance", "Expected attendance", "number"), F("registrations", "Registrations", "number"), F("actual_attendance", "Actual attendance", "number"),
                F("budget", "Budget (₹)", "number"), F("actual_cost", "Actual cost (₹)", "number"), F("speakers", "Speakers / guests / influencers"), F("owner", "Owner"),
                F("status", "Status", "select", ["Idea", "Planning", "Confirmed", "Live", "Completed", "Cancelled"]), F("run_of_show", "Run of show", "textarea"),
                F("promo_plan", "Promotion plan", "textarea"), F("leads_generated", "Leads generated", "number"), F("learnings", "Learnings", "textarea")],
        cols=["name", "mode", "type", "date", "venue", "budget", "status"], filter="status", kanban="status")),
    ("outreach_templates", dict(title="Outreach Templates", icon="✉️", group="Campaigns", desc="Message templates. Use {name} {brand} {platform} {campaign} {sender} placeholders.",
        fields=[F("name", "Template name"), F("channel", "Channel", "select", ["Email", "Instagram DM", "LinkedIn", "WhatsApp", "X DM"]),
                F("audience", "Audience", "select", ["Influencer", "Creator / freelancer", "PR / Media", "Event guest", "Retail partner"]), F("subject", "Subject"), F("body", "Body", "textarea")],
        cols=["name", "channel", "audience"], filter="audience")),
    ("utm_links", dict(title="UTM Links", icon="🏷️", group="Campaigns", desc="Saved tracking links (use the UTM Builder to create).",
        fields=[F("name", "Label"), F("base_url", "Base URL", "url"), F("source", "utm_source"), F("medium", "utm_medium"), F("campaign", "utm_campaign"),
                F("term", "utm_term"), F("content", "utm_content"), F("full_url", "Full URL", "url")],
        cols=["name", "campaign", "source", "medium", "full_url"])),
])

CHECKLIST = {
    "Research": ["Define launch goal and success metrics", "Size the market (TAM/SAM/SOM)", "Interview 10+ target customers", "Complete competitor teardown", "Validate problem-solution fit"],
    "Positioning": ["Write positioning statement", "Build messaging house (pillars + proof points)", "Finalise brand name, tagline and voice", "Create persona cards"],
    "Product & Pricing": ["Decide pricing and packaging", "Define launch offer / promo mechanics", "Confirm product readiness and QA sign-off", "Legal, claims and compliance review"],
    "Channels": ["Select channel mix and budget split", "Set up tracking (UTMs, GA4, pixels, CRM)", "Set up landing page and conversion flow", "Set up social, email and ad accounts", "Plan influencer / PR outreach"],
    "Content": ["Build 30-day content calendar", "Create mood board and visual direction", "Produce hero asset (video / key visual)", "Write website, email and ad copy", "Create sales and retail collateral"],
    "Sales & Enablement": ["Train sales / distributor teams", "Create FAQ and objection handling", "Prepare demo / sampling plan"],
    "Launch": ["Internal launch briefing", "Go-live checklist and QA of all links", "Press release and media outreach", "Launch-day social and community plan", "War-room monitoring dashboard"],
    "Post-launch": ["Daily KPI review for first 14 days", "Collect customer feedback and reviews", "Run first A/B experiments", "Launch retrospective and learnings", "Plan scale-up / next phase"],
}
FEEDS = [
    ("Search Engine Land", "https://searchengineland.com/feed", "SEO / Search"),
    ("Marketing Dive", "https://www.marketingdive.com/feeds/news/", "Marketing"),
    ("HubSpot Marketing", "https://blog.hubspot.com/marketing/rss.xml", "Marketing"),
    ("Social Media Today", "https://www.socialmediatoday.com/feeds/news/", "Social"),
    ("Google News: India marketing", "https://news.google.com/rss/search?q=marketing+india+campaign&hl=en-IN&gl=IN&ceid=IN:en", "Industry"),
    ("Google News: FMCG launches", "https://news.google.com/rss/search?q=FMCG+product+launch+india&hl=en-IN&gl=IN&ceid=IN:en", "FMCG / Retail"),
    ("Google News: Instagram / Meta updates", "https://news.google.com/rss/search?q=Instagram+OR+Meta+ads+update&hl=en-IN&gl=IN&ceid=IN:en", "Social"),
    ("Google News: Google Ads / SEO updates", "https://news.google.com/rss/search?q=Google+algorithm+OR+Google+Ads+update&hl=en-IN&gl=IN&ceid=IN:en", "SEO / Search"),
    ("Google News: AI in marketing", "https://news.google.com/rss/search?q=AI+marketing+tools&hl=en-IN&gl=IN&ceid=IN:en", "Tech / AI"),
]
KEY_DATES = [  # fixed-date events; add moving festivals yourself (Diwali, Holi, Eid...)
    ("Valentine's Day", "02-14", "Awareness day"), ("International Women's Day", "03-08", "Awareness day"),
    ("Earth Day", "04-22", "Awareness day"), ("Mother's Day (verify - moves)", "05-10", "Awareness day"),
    ("Independence Day (India)", "08-15", "Festival"), ("Halloween", "10-31", "Awareness day"),
    ("Children's Day (India)", "11-14", "Awareness day"), ("Christmas", "12-25", "Festival"), ("New Year's Eve", "12-31", "Festival"),
    ("Republic Day (India)", "01-26", "Festival"),
]





MODULES["pitches"] = dict(title="Opportunities", icon="🎤", group="Campaigns", desc="Speaking slots, podcasts, guest articles, media features, collaborations and awards: pitch, follow up, track the outcome.",
    fields=[F("name", "Opportunity"), F("type", "Type", "select", ["Speaking", "Podcast", "Guest article", "Media feature", "Collaboration", "Award / list", "Panel / webinar", "Community"]),
            F("host", "Organiser / host"), F("contact", "Contact person"), F("email", "Contact email"), F("status", "Status", "select", ["Idea", "Researching", "Pitched", "In discussion", "Confirmed", "Done", "Declined"]),
            F("date", "Event / publish date", "date"), F("follow_up", "Follow up on", "date"), F("audience", "Audience / reach"), F("link", "Link", "url"), F("pitch", "Angle / pitch", "textarea"), F("outcome", "Outcome & learnings", "textarea")],
    cols=["name", "type", "host", "status", "date", "follow_up"], filter="status", kanban="status")
MODULES["accounts"] = dict(title="Target Accounts", icon="🏛️", group="Growth", desc="Account-based marketing: the companies you want, the people who decide, and the next move for each.",
    fields=[F("company", "Company"), F("industry", "Industry"), F("tier", "Tier", "select", ["Tier 1", "Tier 2", "Tier 3"]),
            F("stage", "Stage", "select", ["Target", "Researching", "Engaged", "Meeting booked", "Proposal", "Won", "Lost", "Nurture"]),
            F("contact_name", "Key contact"), F("contact_role", "Contact role"), F("contact_email", "Contact email"), F("linkedin", "LinkedIn", "url"),
            F("trigger", "Buying trigger", "textarea"), F("potential", "Potential value", "number"), F("next_action", "Next action"), F("next_date", "Next action date", "date"), F("owner", "Owner"), F("notes", "Notes", "textarea")],
    cols=["company", "tier", "stage", "contact_name", "potential", "next_date"], filter="stage", kanban="stage")
MODULES["retail_audits"] = dict(title="Retail Audits", icon="🏪", group="Growth", desc="Store visits: availability, shelf position, POSM, price compliance and competitor activity. Feed your trade and shopper decisions.",
    fields=[F("store", "Store / outlet"), F("city", "City / area"), F("channel", "Channel", "select", ["Kirana / GT", "Modern trade", "Chemist", "Convenience", "E-commerce / Q-comm", "HoReCa", "Other"]),
            F("audit_date", "Audit date", "date"), F("auditor", "Auditor"), F("availability", "Availability", "select", ["In stock", "Low stock", "Out of stock"]),
            F("shelf_position", "Shelf position", "select", ["Eye level", "Mid shelf", "Bottom shelf", "Not visible"]), F("posm", "POSM", "select", ["Present & correct", "Present, damaged", "Missing"]),
            F("price_check", "Price", "select", ["At MRP", "Discounted", "Above MRP"]), F("competitor", "Competitor activity", "textarea"), F("photo_url", "Photo link", "url"), F("actions", "Actions needed", "textarea")],
    cols=["store", "city", "channel", "audit_date", "availability", "posm"], filter="availability")

MODULES["watchlist"] = dict(title="Market Pulse Watchlist", icon="🔭", group="Intelligence", desc="What Market Pulse tracks for you: keywords, brands, competitors and subreddits. Competitors you add under Competitors are tracked automatically.",
    fields=[F("term", "Keyword / brand / subreddit"), F("type", "Type", "select", ["Keyword", "Competitor", "Brand", "Subreddit"]), F("region", "Region", "select", ["India", "Global", "Both"]), F("notes", "Notes", "textarea")],
    cols=["term", "type", "region", "notes"], filter="type")

# --- SaaS wiring: which plan feature unlocks which module, and what the limited "creator" role can touch
MODULE_FEATURE = {"clients": "content_ops", "creators": "content_ops", "content_orders": "content_ops", "rate_card": "content_ops", "payments": "content_ops",
                  "promotions": "promo_events", "events": "promo_events", "influencers": "influencers", "outreach_templates": "influencers", "kpis": "analytics"}
CREATOR_MODULES = {"content_items", "assets", "content_orders", "tasks", "reference_links"}
# money fields freelancers (creator role) never see or change: the agency's margin stays private
HIDDEN_FOR_CREATOR = {"content_orders": {"price_client", "cost_creator"}}
SEED_TABLES = ("launch_checklist", "feeds", "key_dates", "outreach_templates", "rate_card", "watchlist")


SYSTEM = ("You are a senior Head of Marketing / CMO with 15+ years across FMCG, D2C and B2B, fluent in the Indian market. "
          "Produce specific, ready-to-use, professional work: concrete numbers, channel tactics, example copy, and clear next steps. "
          "Avoid generic filler. Use clear headings and bullet points. State assumptions briefly. Never invent statistics; label estimates as estimates.")
AI_TASKS = OrderedDict([
    ("gtm_plan", ("Full GTM plan", "Create a detailed go-to-market plan: goals & KPIs, market & segments, ICP/personas, positioning, pricing & offer, channel strategy with budget split, 90-day phased timeline, team/RACI, risks, and measurement plan.")),
    ("positioning", ("Positioning & messaging house", "Write a positioning statement, value proposition, 3-4 messaging pillars with proof points, taglines (10 options), and elevator pitches (10s, 30s, 60s).")),
    ("personas", ("Buyer personas", "Build 3 detailed personas: demographics/firmographics, goals, pains, objections, triggers, channels, and the messaging angle for each.")),
    ("competitor", ("Competitor analysis & battlecard", "Produce a competitive analysis: landscape map, SWOT for us vs top competitors, positioning gaps, pricing comparison framework, and a sales/marketing battlecard. Mark anything needing verification.")),
    ("calendar", ("Content calendar (imports to Calendar)", "Create a content calendar. Return ONLY a valid JSON array (no prose, no markdown fences). Each element: {\"title\": str, \"channel\": one of [Instagram, LinkedIn, X / Twitter, YouTube, Facebook, WhatsApp, Email, Blog / SEO, Website, Paid Social, Paid Search, Influencer, PR, Events / Webinar, Retail / Trade, Other], \"format\": one of [Post, Carousel, Reel / Short, Video, Story, Article, Newsletter, Ad, Press release, Webinar, Landing page, Thread], \"publish_date\": \"YYYY-MM-DD\", \"copy\": full draft caption/script, \"cta\": str, \"hashtags\": str}. Follow the start date and number of days in the extra instructions; vary formats, mix awareness/consideration/conversion, and include launch-week intensity.")),
    ("social", ("Social posts", "Write 10 platform-native posts for the requested channels with hooks, full captions, CTAs, hashtags, and a visual/creative direction line for each.")),
    ("email", ("Email sequence", "Write a 5-email sequence: purpose, subject line (3 A/B options), preview text, body, CTA, and send timing for each.")),
    ("ad_copy", ("Ad copy (Google & Meta)", "Write Google Search RSA assets (15 headlines <=30 chars, 4 descriptions <=90 chars) and 5 Meta ad variants (primary text, headline, description, creative idea) with different angles.")),
    ("blog", ("SEO blog brief & outline", "Create an SEO content brief: target keyword and secondary keywords, search intent, title options, meta description, H1/H2 outline, FAQs, internal links, and a first draft of the intro and conclusion.")),
    ("press", ("Press release", "Write a press release with headline, sub-head, dateline, body, boilerplate, spokesperson quote placeholders, and a short journalist pitch email.")),
    ("brief", ("Campaign brief", "Write a campaign brief: objective, insight, target, big idea, key message, channel plan, deliverables, timeline, budget split, KPIs, and approvals.")),
    ("video", ("Video / Reel script", "Write 3 short-form video scripts (hook in first 3 seconds, scene-by-scene visuals, voiceover/on-screen text, CTA, music mood).")),
    ("moodboard", ("Mood board & visual direction", "Define a visual direction: 3 mood/theme options, colour palettes with hex codes, typography pairings, photography/illustration style, references to search for (keywords), shot list, and do's/don'ts.")),
    ("landing", ("Landing page copy", "Write landing page copy section by section: hero, sub-hero, benefits, social proof placeholders, how it works, objections/FAQ, offer, CTA variants.")),
    ("influencer", ("Influencer brief", "Write an influencer brief: campaign context, deliverables, key messages, mandatories, do's/don'ts, content ideas, timeline, usage rights, and metrics.")),
    ("budget", ("Budget allocation", "Recommend a marketing budget split by channel and phase with rationale, expected outcomes (labelled as estimates), and a testing reserve.")),
    ("kpi", ("KPI & measurement framework", "Define a KPI tree (north-star, funnel, channel KPIs), tracking setup (UTMs, events), reporting cadence, dashboard layout, and benchmark placeholders.")),
    ("experiments", ("Growth experiments", "Suggest 10 prioritised A/B tests with hypothesis, variants, metric, sample/duration guidance, and ICE score.")),
    ("objections", ("FAQ & objection handling", "Write customer FAQs and sales/retail objection-handling scripts.")),
    ("content_brief", ("Writer brief for a content order", "Write a complete freelancer brief: objective, audience, angle, outline, keywords, tone, do's/don'ts, references to study, word count, deliverable format, deadline and revision policy, and a quality checklist.")),
    ("content_review", ("Editor QA of a draft", "Act as a senior editor. The draft to review is in the extra instructions. Score it 1-10 on structure, accuracy, originality risk, SEO, tone and grammar, list specific fixes, and give a revised intro. Flag any claims needing verification.")),
    ("creator_test", ("Creator screening test & rubric", "Design a paid screening test for the given skill (task, brief, time limit) and a scoring rubric with pass mark, so unsuitable freelancers are filtered without manager time.")),
    ("influencer_discovery", ("Influencer discovery plan (no fake names)", "Build an influencer discovery plan: ideal creator archetypes per platform and tier, selection criteria, red flags, hashtags and search queries to use on each platform, budget ranges to expect (labelled estimates), and a scoring sheet. IMPORTANT: do NOT invent real people, handles, emails or follower counts; describe types and how to find them.")),
    ("outreach", ("Personalised outreach messages", "Write outreach messages (email + short DM + follow-up after 4 days) for the audience described in the extra instructions, personalised, concise, with a clear ask.")),
    ("promo_plan", ("Promotion plan (online + offline)", "Design 5 promotion mechanics for the product, split between online and offline, each with mechanic, target, funding, expected uplift (estimate), risks, T&C essentials, tracking method, and a recommendation on which to run.")),
    ("contest", ("Contest / giveaway mechanics + T&C", "Design a social media contest: mechanic, entry rules, judging, prize structure, timeline, promotion plan, and a plain-language T&C checklist (note: have legal review it; platform rules and local laws apply).")),
    ("event_plan", ("Event plan (online or offline)", "Create a full event plan: objective, concept, agenda / run-of-show, budget breakdown, promotion timeline, staffing, risks, lead-capture method, and post-event follow-up. Cover the mode specified in extra instructions.")),
    ("report", ("Weekly marketing report", "Write a weekly marketing report from the KPI and campaign data provided: highlights, wins, misses, insights, and recommended actions for next week.")),
])


# --- industry-specific AI tasks (shown only for the listed industries; costs in config.AI_COST default to 1 credit)
AI_TASKS["pb_profile"] = ("Personal brand: profile rewrite", "Rewrite my professional profile: 3 LinkedIn headline options, an About section (first-person, story + proof + call to action), featured-section ideas, and a one-line positioning statement. Ask nothing; make sensible assumptions and flag them.")
AI_TASKS["pb_30day"] = ("Personal brand: 30-day content plan", "Create a 30-day personal-brand content plan around 3 content pillars: for each day give platform, format, hook, key points and call to action. Include weekly engagement routines (comments on target accounts) and one lead-magnet idea. Output as a table by week.")
AI_TASKS["pb_bio"] = ("Personal brand: speaker bio & one-sheet", "Write a 50-word, 100-word and 200-word speaker bio in third person, 5 talk titles with 3-line abstracts, and a speaker one-sheet outline (audience takeaways, past proof, topics, tech needs).")
AI_TASKS["pb_pitch"] = ("Personal brand: podcast / speaker pitch", "Write a short, specific pitch email to a podcast host or event organiser: relevance to their audience, 3 topic angles, proof of credibility, and an easy ask. Give 3 subject-line options and a polite follow-up for 5 days later.")
AI_TASKS["b2b_abm"] = ("B2B: account plan (ABM)", "Build an account-based marketing plan for one target account: buying committee and roles, likely pains and triggers, a 60-day multi-channel play (LinkedIn, email, content, events, direct mail), messaging per stakeholder, and success measures.")
AI_TASKS["b2b_sequence"] = ("B2B: outbound sequence", "Write a 5-touch outbound sequence (email + LinkedIn) for the persona described: each touch with subject/opening, value point, proof and a low-friction ask; timing between touches; and 2 reply-handling responses for common objections.")
AI_TASKS["b2b_case_study"] = ("B2B: case study from notes", "Turn the notes provided into a case study: headline with the result, customer snapshot, challenge, solution, implementation, quantified results, a pull-quote placeholder and a call to action. Flag any numbers that need customer approval.")
AI_TASKS["d2c_pdp"] = ("D2C: product page copy", "Write a high-converting product detail page: headline, sub-headline, 5 benefit bullets, ingredient/material story, social-proof section prompts, FAQ (8), guarantee/returns copy, and 3 A/B test ideas.")
AI_TASKS["d2c_ads"] = ("D2C: ad creative concepts", "Produce 10 Meta/Instagram/YouTube ad concepts for the product: hook (first 3 seconds), angle (problem, proof, demo, comparison, UGC, offer), script outline, on-screen text and CTA. Include 5 primary-text variants and 3 headline variants.")
AI_TASKS["d2c_whatsapp"] = ("D2C: WhatsApp / lifecycle flows", "Design WhatsApp and email lifecycle flows: abandoned cart (3 messages), post-purchase (order, usage tips, review ask), replenishment reminder and win-back. Give message copy, timing and template-approval notes for WhatsApp Business.")
AI_TASKS["fmcg_shopper"] = ("FMCG: shopper insight to action", "Turn the shopper findings provided into insight-implication-action: 5 sharp insights, the shopper behaviour behind each, the implication for pack/price/POSM/promo, and a prioritised action list with owner and metric. Note data gaps.")
AI_TASKS["fmcg_trade"] = ("FMCG: trade scheme & retailer pitch", "Draft a retailer/distributor pitch and scheme note: value story, margin and scheme table structure, display and POSM asks, a one-minute salesman script, and a simple ROI illustration for the retailer. Use placeholders for numbers I did not provide.")
AI_TASKS["fmcg_posm"] = ("FMCG: POSM / in-store brief", "Write a POSM and in-store visibility brief: objective, store types, placement rules, format options with dimensions placeholders, messaging hierarchy, compliance audit checklist and measurement plan.")
AI_TASKS["hosp_review"] = ("Hospitality: review replies", "Write professional replies to the guest reviews provided: warm and specific for positive ones, empathetic and solution-focused for negative ones (never defensive, never sharing private details), each under 90 words with a subtle invitation to return.")
AI_TASKS["hosp_menu"] = ("Hospitality: menu / package launch plan", "Create a launch plan for a new menu, package or experience: positioning, pricing bands, 14-day teaser calendar, staff briefing points, partner/creator outreach, offers and measurement (covers, ADR, direct bookings).")
AI_TASK_FOR = {"pb_profile": {"personal_brand", "startup"}, "pb_30day": {"personal_brand", "startup"}, "pb_bio": {"personal_brand"}, "pb_pitch": {"personal_brand", "b2b", "saas", "agency"},
               "b2b_abm": {"b2b", "saas", "agency", "fintech"}, "b2b_sequence": {"b2b", "saas", "agency", "fintech", "startup"}, "b2b_case_study": {"b2b", "saas", "agency", "fintech", "education", "healthcare"},
               "d2c_pdp": {"d2c", "fashion", "retail"}, "d2c_ads": {"d2c", "fashion", "startup"}, "d2c_whatsapp": {"d2c", "fashion", "retail", "hospitality"},
               "fmcg_shopper": {"fmcg", "retail"}, "fmcg_trade": {"fmcg", "retail"}, "fmcg_posm": {"fmcg", "retail"}, "hosp_review": {"hospitality", "healthcare", "retail"}, "hosp_menu": {"hospitality"}}

# --- live web research tasks (use Anthropic's web search tool; answers cite their sources)
AI_TASKS["research_market"] = ("Live research: market & category scan", "Using live web search, produce a market and category scan for the product/brand and audience below: size and growth signals, key players, developments in the last 90 days, customer and consumer trends in India and globally, regulatory notes, and 5 opportunities. Cite sources inline. State the date range you searched and any uncertainty. Never invent numbers or quotes; if you cannot find something, say so.")
AI_TASKS["research_competitor"] = ("Live research: competitor intelligence", "Using live web search, build a competitor intelligence brief for the competitors named below (or, if none, identify the 4-5 most relevant in this category in India): positioning, pricing signals, recent launches and campaigns, social presence, strengths, weaknesses, and gaps we can exploit. Cite sources inline. Only report facts you found; label anything inferred.")
AI_TASKS["research_trends"] = ("Live research: trends & content opportunities", "Using live web search, find what is trending right now in this category in India and globally: content formats, topics, campaigns and brands doing well (only ones you actually found), and seasonal hooks in the next 60 days. End with 10 specific content ideas with channel and hook. Cite sources inline and note the dates.")
AI_TASKS["pulse_brief"] = ("Market Pulse brief", "Turn this week's live market signals into a brief.")
FORCE_RESEARCH = {"research_market", "research_competitor", "research_trends"}
HIDDEN_TASKS = {"pulse_brief"}
