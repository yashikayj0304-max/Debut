"""Which screens people actually open.

Debut has ten sections and about fifty screens, and the honest answer to "is any of this
redundant?" is not an opinion - it is a count. This keeps one, as cheaply as it can:

  * one row per person per screen per day, incremented, never appended
  * only logged-in GETs of real pages, so no form posts, no assets, no API calls
  * the endpoint name only - never the URL, so record ids and search text are not stored
  * counting failures are swallowed; a statistic is never worth a broken page

What it deliberately does NOT do is track individuals. The display rolls up to "how many
people" and "how many opens", because the question is which features earn their place, not
who looked at what.
"""
import datetime as dt

import hubs
from db import IS_PG, ex, q

# Screens that say nothing about whether a feature is wanted.
SKIP = {"static", "health", "healthz", "robots", "landing", "pricing", "terms", "privacy", "about",
        "features", "demo", "changelog", "data_deletion", "bio.public", "bio.go", "bio.qr",
        "bio.review_go", "bio.review_qr", "board_public", "board_public_img", "survey.public",
        "auth.login", "auth.signup", "auth.logout", "auth.forgot", "auth.reset", "auth.verify",
        "auth.invite", "auth.login_pin", "auth.login_2fa", "auth.demo_exit", "notif_count", "ping"}


# A few endpoints serve a whole family of screens - /m/<key> alone is about twenty-five of them.
# Counting them under one name would credit every module with every other module's opens, so the
# key travels with the endpoint.
MANY = ("m_list", "kanban", "m_new", "m_edit")


def name_for(endpoint, view_args=None):
    """The name a screen is counted under. `m_list` plus its module, everything else as it is."""
    if endpoint in MANY and (view_args or {}).get("key"):
        return f"{endpoint}:{view_args['key']}"
    return endpoint


def record(wid, uid, endpoint, view_args=None):
    """Count one page view. Called from after_request, so it must be fast and silent."""
    if not (wid and uid and endpoint) or endpoint in SKIP:
        return
    endpoint = name_for(endpoint, view_args)
    day = dt.date.today().isoformat()
    try:
        if IS_PG:
            ex("INSERT INTO feature_hits (workspace_id, user_id, endpoint, day, n) VALUES (?,?,?,?,1) "
               "ON CONFLICT (workspace_id, user_id, endpoint, day) DO UPDATE SET n = feature_hits.n + 1",
               (wid, uid, endpoint[:120], day))
        else:
            if not ex("UPDATE feature_hits SET n = n + 1 WHERE workspace_id=? AND user_id=? AND endpoint=? AND day=?",
                      (wid, uid, endpoint[:120], day)):
                ex("INSERT OR IGNORE INTO feature_hits (workspace_id, user_id, endpoint, day, n) VALUES (?,?,?,?,1)",
                   (wid, uid, endpoint[:120], day))
    except Exception:
        pass        # a count is never worth a 500


def _screens():
    """Every screen Debut offers, as (hub label, hub icon, screen label, endpoint)."""
    out = []
    for hub in hubs.HUBS:
        for label, endpoint, kw, _extra, _gate in hub["tabs"]:
            name = label
            endpoint = name_for(endpoint, kw)        # m_list serves many screens; keep them apart
            out.append((hub["label"], hub["icon"], name, endpoint))
    return out


def _counts(wid, days):
    since = (dt.date.today() - dt.timedelta(days=days - 1)).isoformat()
    rows = q("SELECT endpoint, SUM(n) AS opens, COUNT(DISTINCT user_id) AS people, MAX(day) AS last "
             "FROM feature_hits WHERE workspace_id=? AND day>=? GROUP BY endpoint", (wid, since))
    return {r["endpoint"]: dict(opens=int(r["opens"] or 0), people=int(r["people"] or 0), last=r["last"]) for r in rows}


def report(wid, days=30):
    """Sections and screens, busiest first, with the untouched ones named plainly.

    `m_list` screens are recorded under one endpoint, so a module's own key is appended when
    there is one. Anything recorded that no longer maps to a screen is ignored rather than shown
    as a mystery row.
    """
    hits = _counts(wid, days)
    recorded = sum(v["opens"] for v in hits.values())
    sections, order, claimed = {}, [], set()
    for hub_label, icon, name, endpoint in _screens():
        h = hits.get(endpoint) or {}
        if h:
            claimed.add(endpoint)
        if hub_label not in sections:
            sections[hub_label] = dict(label=hub_label, icon=icon, opens=0, people=set(), screens=[])
            order.append(hub_label)
        s = sections[hub_label]
        s["screens"].append(dict(name=name, opens=h.get("opens", 0), last=h.get("last", "")))
        s["opens"] += h.get("opens", 0)
        if h.get("people"):
            s["people"].add(h["people"])
    out = []
    in_menu = sum(sections[k]["opens"] for k in order)
    for key in order:
        s = sections[key]
        s["people"] = max(s["people"]) if s["people"] else 0
        s["screens"].sort(key=lambda x: -x["opens"])
        s["share"] = round(100 * s["opens"] / in_menu) if in_menu else 0
        s["unused"] = [x["name"] for x in s["screens"] if not x["opens"]]
        out.append(s)
    out.sort(key=lambda s: -s["opens"])
    # Opens on screens that are not in the menu at all - the dashboard, settings, this page.
    # They belong in the total or the maths looks wrong, but they say nothing about a feature.
    other = recorded - in_menu
    return dict(days=days, total=in_menu, other=max(0, other), recorded=recorded, sections=out,
                enough=recorded >= 40,
                dead=[s["label"] for s in out if not s["opens"]])
