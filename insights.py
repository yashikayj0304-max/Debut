"""What Instagram actually reported, turned into things worth saying.

Debut already pulls real numbers from Instagram - followers, reach, and per-post reach, likes,
comments, saves and shares. The trouble was that they were *measured* and then shown in one
place: the edit screen of a single post. Everywhere a person makes a decision - the dashboard,
the calendar, the list of posts, the Create studio - they were still guessing.

So this is the one place those numbers are read and interpreted, and every screen asks it rather
than doing its own arithmetic. Three rules it keeps:

  1. **Say how much it is based on.** "Reels beat photos" off three posts is noise. Every finding
     carries the number of posts behind it, and below `ENOUGH` the honest answer is "not yet".
  2. **Never invent a number.** If Instagram has not reported reach for a post, that post is not
     counted in a reach average - it is not a zero.
  3. **One comparison at a time.** Format against format, weekday against weekday. No composite
     "engagement score" that nobody can check.

What the owner says about a post (learn.py, three taps three days later) stays separate on
purpose: it covers posts that never went out through Debut, and it is the only signal there is
before an account is connected.
"""
import datetime as dt

import services as S
from db import q

ENOUGH = 4              # below this many measured posts, a comparison is not worth making
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
# Saves and shares say "this was worth keeping" far more than a like does, so they count for more.
WEIGHTS = dict(reach=1.0, saves=12.0, shares=10.0, comments=6.0, likes=1.0)


def _posts(ws_id, days=90):
    """Every post Instagram has reported on, with the date it went out and what it was."""
    since = (S.today() - dt.timedelta(days=days)).isoformat()
    return q("""SELECT s.*, c.title, c.format, c.channel, c.publish_date
                FROM post_stats s LEFT JOIN content_items c ON c.id = s.content_id
                WHERE s.workspace_id=? AND (c.publish_date IS NULL OR c.publish_date='' OR c.publish_date >= ?)
                ORDER BY s.id DESC""", (ws_id, since))


def _score(r):
    """One number for "did people care", built only from what Instagram reported."""
    return sum(w * float(r[k] or 0) for k, w in WEIGHTS.items() if k in r.keys())


def _avg(rows, key):
    vals = [float(r[key] or 0) for r in rows if (key in r.keys() and r[key] not in (None, ""))]
    return round(sum(vals) / len(vals)) if vals else None


def _compare(rows, bucket_of, least=2):
    """Group the posts and rank the groups by average reach. Groups too small to mean anything
    are dropped rather than shown with a caveat nobody reads."""
    buckets = {}
    for r in rows:
        k = bucket_of(r)
        if k:
            buckets.setdefault(k, []).append(r)
    out = []
    for k, rs in buckets.items():
        if len(rs) < least:
            continue
        reach = _avg(rs, "reach")
        out.append(dict(name=k, n=len(rs), reach=reach or 0, score=round(sum(_score(r) for r in rs) / len(rs))))
    out.sort(key=lambda x: -x["score"])
    return out


def _weekday(r):
    try:
        return DAYS[dt.date.fromisoformat((r["publish_date"] or "")[:10]).weekday()]
    except (ValueError, TypeError):
        return ""


def summary(ws_id, days=28):
    """The headline: followers now, how reach is going, and the post that did best.

    `followers` and its change come from the Results Log, where the daily pull writes them, so
    the number is whatever Instagram last said rather than a running total Debut kept itself.
    """
    rows = q("""SELECT period, value FROM kpis WHERE workspace_id=? AND metric='Followers'
                AND channel='Instagram' ORDER BY period DESC LIMIT 60""", (ws_id,))
    followers = gain = None
    if rows:
        try:
            followers = int(float(rows[0]["value"]))
            then = (dt.date.fromisoformat(rows[0]["period"]) - dt.timedelta(days=days)).isoformat()
            older = [r for r in rows if r["period"] <= then] or ([rows[-1]] if len(rows) > 1 else [])
            if older:
                gain = followers - int(float(older[0]["value"]))
        except (ValueError, TypeError):
            followers = gain = None
    posts = _posts(ws_id, days)
    best = max(posts, key=_score) if posts else None
    return dict(followers=followers, gain=gain, days=days, n=len(posts),
                reach=_avg(posts, "reach"), likes=_avg(posts, "likes"), saves=_avg(posts, "saves"),
                best=best, live=bool(posts or followers is not None))


def what_works(ws_id, days=90):
    """Which format and which day did better, from measured posts only."""
    rows = _posts(ws_id, days)
    measured = [r for r in rows if (r["reach"] or 0) > 0]
    out = dict(n=len(measured), enough=len(measured) >= ENOUGH, days=days,
               formats=[], weekdays=[], top=[], avg_reach=_avg(measured, "reach"))
    if not out["enough"]:
        return out
    out["formats"] = _compare(measured, lambda r: (r["format"] or "").strip())[:4]
    out["weekdays"] = _compare(measured, _weekday)[:3]
    out["top"] = sorted(measured, key=_score, reverse=True)[:5]
    return out


def suggestions(ws_id, days=90):
    """Things worth doing next, each one traceable to a number on this account.

    Every line says what it is based on. A suggestion the owner cannot check is just an opinion
    with a chart next to it.
    """
    w = what_works(ws_id, days)
    out = []
    if not w["enough"]:
        left = ENOUGH - w["n"]
        return [dict(text=f"Publish {left} more post{'s' if left != 1 else ''} through Debut and it can tell you "
                          f"what works for this account instead of guessing.",
                     why=f"Instagram has reported on {w['n']} so far.", kind="wait")]
    fm = w["formats"]
    if len(fm) >= 2 and fm[0]["reach"] and fm[-1]["reach"] and fm[0]["reach"] >= fm[-1]["reach"] * 1.4:
        out.append(dict(text=f"Make more {fm[0]['name']}s.", kind="format",
                        why=f"{fm[0]['name']}s reached about {fm[0]['reach']:,} people on average "
                            f"({fm[0]['n']} posts), against {fm[-1]['reach']:,} for {fm[-1]['name']}s "
                            f"({fm[-1]['n']} posts)."))
    if w["weekdays"] and len(w["weekdays"]) >= 2:
        d = w["weekdays"][0]
        out.append(dict(text=f"{d['name']} is your strongest day - put the post you care about most there.",
                        kind="day",
                        why=f"{d['n']} posts on {d['name']}s averaged {d['reach']:,} reach, the best of any day."))
    saves = [r for r in w["top"] if (r["saves"] or 0) > 0]
    if saves:
        out.append(dict(text=f"“{(saves[0]['title'] or 'That post')[:48]}” was saved "
                             f"{saves[0]['saves']} times. Do that subject again, differently.",
                        kind="repeat",
                        why="A save means someone wanted it later, which is the strongest signal Instagram gives you."))
    if w["avg_reach"]:
        out.append(dict(text=f"Your average post reaches about {w['avg_reach']:,} people. "
                             f"Anything well under that is worth a second look rather than a repeat.",
                        kind="baseline", why=f"Across {w['n']} measured posts in the last {days} days."))
    return out[:4]


def for_item(ws_id, content_id):
    """One post's own numbers, and how it did against this account's average.

    Returning the comparison here rather than in a template means every screen that shows a
    post's reach says the same thing about it.
    """
    rows = q("SELECT * FROM post_stats WHERE workspace_id=? AND content_id=? ORDER BY id DESC LIMIT 1",
             (ws_id, content_id))
    if not rows:
        return None
    r = rows[0]
    avg = _avg([x for x in _posts(ws_id, 90) if (x["reach"] or 0) > 0], "reach")
    reach = int(r["reach"] or 0)
    verdict = ""
    if avg and reach:
        if reach >= avg * 1.3:
            verdict = f"above your average of {avg:,}"
        elif reach <= avg * 0.7:
            verdict = f"below your average of {avg:,}"
        else:
            verdict = f"about your average of {avg:,}"
    return dict(row=r, reach=reach, likes=int(r["likes"] or 0), comments=int(r["comments"] or 0),
                saves=int(r["saves"] or 0), shares=int(r["shares"] or 0), views=int(r["views"] or 0),
                permalink=r["permalink"] or "", fetched_at=r["fetched_at"] or "",
                avg=avg, verdict=verdict)


def for_items(ws_id, content_ids):
    """The numbers for a whole page of posts in one query, so a list does not make one per row."""
    ids = [int(i) for i in content_ids if i]
    if not ids:
        return {}
    marks = ",".join("?" for _ in ids)
    rows = q(f"""SELECT content_id, MAX(reach) reach, MAX(likes) likes, MAX(saves) saves,
                        MAX(comments) comments, MAX(permalink) permalink
                 FROM post_stats WHERE workspace_id=? AND content_id IN ({marks})
                 GROUP BY content_id""", tuple([ws_id] + ids))
    return {int(r["content_id"]): dict(reach=int(r["reach"] or 0), likes=int(r["likes"] or 0),
                                       saves=int(r["saves"] or 0), comments=int(r["comments"] or 0),
                                       permalink=r["permalink"] or "") for r in rows}


def headline(ws_id):
    """One sentence for the dashboard, or "" when there is nothing honest to say yet."""
    s = summary(ws_id)
    if not s["live"]:
        return ""
    bits = []
    if s["followers"] is not None:
        bits.append(f"{s['followers']:,} followers" + (
            f" ({'+' if s['gain'] > 0 else ''}{s['gain']} in {s['days']} days)" if s["gain"] else ""))
    if s["reach"]:
        bits.append(f"{s['reach']:,} reach per post")
    return "From Instagram: " + ", ".join(bits) + "." if bits else ""
