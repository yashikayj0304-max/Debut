# Debut: marketing operating system (SaaS edition)

GTM plans, content calendar (drag & drop, ICS feed), drag-to-reorder boards and lists with sort + group-by, mood boards, a library for copy and links, latest-news aggregator, campaigns, KPIs, UTM builder,
creator network + content orders + invoices (Content Ops), influencer discovery & outreach, promotions & events (with auto-checklists),
live Market Pulse (news, trends, videos, competitors) and AI web research, AI Studio, global search, CSV import/export, and full multi-tenant SaaS plumbing: accounts, workspaces, roles, invites, a **Free forever plan** plus paid subscriptions, usage limits, group mode with a Team Lead role, 14 industry modes (personal brand, B2B, D2C, FMCG, startup, hospitality and more), comments and notifications, a REST API, two-factor login, client reports and an installable mobile app and a platform-owner admin console.

## What Debut does now (November 2026)

**It posts for you.** Connect Instagram, Facebook or LinkedIn once; schedule a post and Debut sends it
at the time you picked. Until the platform approves your app, a scheduled post still reaches you as a
reminder with the caption ready to copy, so nothing is blocked while you wait. See DEPLOY.md.

**It brings the numbers back.** Followers, reach, and per-post reach/likes/saves/shares land in the
Results Log by themselves, once a day.

**It learns what works for you.** Three taps a few days after a post ("nothing happened / it was fine /
it did well") and the Numbers page tells you your best format and your best day — from your own posts,
not an industry average. Below five ratings it says so rather than inventing a pattern.

**It plans.** Eight campaign templates (Diwali, launch, sale weekend, reels batch, creator collab,
newsletter, shop opening, win-back) build the real posts and tasks around a date you pick. "Plan my
month" fills the calendar from the Idea Bank. "Do this again" repeats any post next week, month or year.

**It helps you shoot.** Reels get a shoot sheet with timings, a cover frame, five alternative hooks, and
pre-publish checks for the caption hook, hashtags, the ask and the file. One post becomes a carousel,
a story, a LinkedIn post or a newsletter in a tap.

**It brings people through the door.** A link page for your Instagram bio (visits and taps counted, with
enquiries landing in Leads) and a review-asking link plus a QR code for the counter.

**It fits how Indian small businesses work.** ₹ formatting, festival dates, industry-specific wording,
news in ten Indian languages, a Hindi interface for the menu and main actions, a printable month for the
wall, and drafts that survive a bad connection.

- Local: run **Launch Debut.bat** (Windows) or `pip install -r requirements.txt && python app.py` → http://127.0.0.1:8001
- Production: read **DEPLOY.md**
- Tests: `python -m pytest tests`
- Handy shortcuts in the app: **Ctrl/⌘+K** jumps to the search box, **＋ Create** menu, and a bottom bar on phones.

**User manual:** in the app at `/manual` (public, also linked from the sign-up page, Help and the footer) and as `docs/Debut-User-Manual.pdf`. Update `templates/manual.html`, then regenerate the PDF (see `DEVELOPER_GUIDE.md`, “Keeping the manual current”).

**Docs (folder `docs/`):** `Debut-User-Manual.pdf` (start here, 7 Nov 2026), `Debut-Launch-Playbook.pdf` (who you need and what to do before, during and after launch), `Debut-Developer-Deployment-Guide.md` for the developer, `Debut-Guide-Personal-Branding.pdf` and `Debut-Guide-Agencies-and-Teams.pdf` for customers, and `Debut-Visual-Tour.pdf` (real screenshots of every screen and role).

**Handing this to a developer? Give them `DEVELOPER_GUIDE.md`** (step-by-step deployment, configuration, Razorpay, email, backups, smoke tests, troubleshooting).
