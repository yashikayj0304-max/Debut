"""What actually worked, learnt from this business rather than guessed from its industry.

Two sources, deliberately kept apart:
  * what Instagram reports (post_stats) - true, but only exists once posts publish through Debut
  * what the owner says (post_feedback) - three taps, three days after a post goes out

The second one matters more than it looks. Most small businesses will not connect an API for weeks,
and an owner knows perfectly well whether a post did anything. Three taps a few times a week turns
"best time to post" from an industry guess into this shop's own evidence.
"""
import datetime as dt

import services as S
from db import ex, ins, q

RATINGS = [("flop", "😕 Nothing happened"), ("ok", "😐 It was fine"), ("good", "🔥 It did well")]
SCORE = {"flop": 0, "ok": 1, "good": 2}
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
ENOUGH = 5                      # below this, say so rather than pretending a pattern exists


def rate(ws_id, content_id, rating, user_id=0):
    if rating not in SCORE:
        return False
    ex("DELETE FROM post_feedback WHERE workspace_id=? AND content_id=?", (ws_id, content_id))
    ins("post_feedback", dict(workspace_id=ws_id, content_id=content_id, user_id=user_id or 0, rating=rating))
    S.audit("post_rated", f"content_items#{content_id} → {rating}")
    return True


def rating_of(ws_id, content_id):
    rows = q("SELECT rating FROM post_feedback WHERE workspace_id=? AND content_id=?", (ws_id, content_id))
    return rows[0]["rating"] if rows else ""


def awaiting(ws_id, days=3, limit=5):
    """Posts that went out at least `days` ago and nobody has said how they went."""
    cutoff = (S.today() - dt.timedelta(days=days)).isoformat()
    return q("""SELECT c.id, c.title, c.format, c.channel, c.publish_date FROM content_items c
                WHERE c.workspace_id=? AND c.status='Published' AND c.publish_date<>''
                  AND c.publish_date <= ?
                  AND c.id NOT IN (SELECT content_id FROM post_feedback WHERE workspace_id=?)
                ORDER BY c.publish_date DESC LIMIT ?""", (ws_id, cutoff, ws_id, limit))


def _rated(ws_id):
    return q("""SELECT f.rating, c.format, c.channel, c.publish_date FROM post_feedback f
                JOIN content_items c ON c.id = f.content_id
                WHERE f.workspace_id=? AND c.publish_date <> ''""", (ws_id,))


def _best(rows, key):
    buckets = {}
    for r in rows:
        k = (r[key] or "").strip()
        if k:
            buckets.setdefault(k, []).append(SCORE[r["rating"]])
    scored = [(k, sum(v) / len(v), len(v)) for k, v in buckets.items() if len(v) >= 2]
    scored.sort(key=lambda x: (-x[1], -x[2]))
    return scored


def what_works(ws_id):
    """An honest read of this business's own posts. Says "not enough yet" when that is the truth."""
    rows = _rated(ws_id)
    out = dict(n=len(rows), enough=len(rows) >= ENOUGH, formats=[], channels=[], days=[], liked=0)
    if not rows:
        return out
    out["liked"] = round(100 * sum(1 for r in rows if r["rating"] == "good") / len(rows))
    out["formats"] = _best(rows, "format")[:3]
    out["channels"] = _best(rows, "channel")[:3]
    day_rows = []
    for r in rows:
        try:
            day_rows.append(dict(rating=r["rating"], day=DAYS[dt.date.fromisoformat(r["publish_date"][:10]).weekday()]))
        except ValueError:
            continue
    out["days"] = _best(day_rows, "day")[:3] if day_rows else []
    return out


def headline(ws_id):
    """One sentence for the dashboard, or an empty string when there is nothing honest to say."""
    w = what_works(ws_id)
    if not w["enough"]:
        left = ENOUGH - w["n"]
        return f"Rate {left} more post{'s' if left != 1 else ''} and Debut can tell you what works for you."
    bits = []
    if w["formats"]:
        bits.append(f"{w['formats'][0][0]}s do best")
    if w["days"]:
        bits.append(f"{w['days'][0][0]}s are your strongest day")
    return "From your own posts: " + ", and ".join(bits) + "." if bits else ""
