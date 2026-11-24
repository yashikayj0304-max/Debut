"""Templates the business writes for itself, sitting next to the eight that ship with Debut.

The gallery was eight fixed campaigns in `playbooks.py`. They are good starting points, but a
sweet shop's Raksha Bandhan run and a gym's January push are nothing like each other, and the
thing a business repeats every month is the thing most worth having a template for.

So an owner or manager can write their own here. A saved template is the same shape as a
built-in one, which is the point: `templates_use` does not know or care which kind it was given,
so one tap puts a campaign, its dated posts and its tasks on the calendar either way.

Stored as one row per template with its steps as JSON, rather than a table of steps. A template
is edited and used as a whole; splitting it across two tables would buy nothing and cost a join
on every page that lists them.
"""
import json

import services as S
from db import ex, ins, q

KINDS = (("post", "A post"), ("task", "A job to do"))
MAX_STEPS = 40                  # a template longer than this is a project, not a template


def _steps(raw):
    """Parse stored steps, and never let a bad row take down the gallery."""
    try:
        got = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []
    out = []
    for s in got if isinstance(got, list) else []:
        try:
            out.append((int(s["day"]), str(s.get("kind") or "post"), str(s.get("title") or "")[:200],
                        str(s.get("channel") or ""), str(s.get("format") or "")))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def as_playbook(row):
    """One saved template in exactly the shape `templates_use` already understands."""
    return dict(key=f"own-{row['id']}", icon=row["icon"] or "🧩", title=row["name"],
                tag=row["tag"] or "Yours", desc=row["notes"] or "", anchor=row["anchor"] or "The day it centres on",
                items=_steps(row["steps"]), own=True, id=row["id"])


def all_for(ws_id):
    """Every template this workspace wrote, newest first."""
    return [as_playbook(r) for r in
            q("SELECT * FROM own_templates WHERE workspace_id=? ORDER BY id DESC", (ws_id,))]


def by_key(ws_id, key):
    if not str(key).startswith("own-"):
        return None
    try:
        rid = int(str(key)[4:])
    except ValueError:
        return None
    rows = q("SELECT * FROM own_templates WHERE workspace_id=? AND id=?", (ws_id, rid))
    return as_playbook(rows[0]) if rows else None


def parse_form(form):
    """Read the builder form into (fields, steps, error).

    The steps arrive as parallel lists - day[], kind[], title[], channel[], format[] - which is
    what a table of rows posts. A row with no title is an empty row the person left behind, not
    an error worth stopping them for.
    """
    name = S.clean_text(form.get("name"), 80)
    if not name:
        return None, None, "Give the template a name - something you will recognise next year."
    steps, days = [], form.getlist("day")
    kinds, titles = form.getlist("kind"), form.getlist("title")
    chans, fmts = form.getlist("channel"), form.getlist("format")
    for i, title in enumerate(titles):
        t = S.clean_text(title, 200)
        if not t:
            continue
        try:
            day = int(str(days[i] if i < len(days) else 0).strip() or 0)
        except ValueError:
            return None, None, f"“{t[:40]}” needs a whole number of days, like -7 or 0 or 3."
        if not -365 <= day <= 365:
            return None, None, "Days have to be within a year either side of the main date."
        kind = (kinds[i] if i < len(kinds) else "post")
        kind = kind if kind in dict(KINDS) else "post"
        steps.append(dict(day=day, kind=kind, title=t,
                          channel=S.clean_text(chans[i] if i < len(chans) else "", 40),
                          format=S.clean_text(fmts[i] if i < len(fmts) else "", 40)))
    if not steps:
        return None, None, "Add at least one post or job, with a title."
    if len(steps) > MAX_STEPS:
        return None, None, f"That is more than {MAX_STEPS} steps. Split it into two templates."
    steps.sort(key=lambda s: s["day"])
    fields = dict(name=name, icon=S.clean_text(form.get("icon"), 4) or "🧩",
                  tag=S.clean_text(form.get("tag"), 24) or "Yours",
                  anchor=S.clean_text(form.get("anchor"), 60) or "The day it centres on",
                  notes=S.clean_text(form.get("notes"), 300))
    return fields, steps, ""


def save(ws_id, user_id, fields, steps, rid=0):
    payload = json.dumps(steps)
    if rid:
        ex("""UPDATE own_templates SET name=?, icon=?, tag=?, anchor=?, notes=?, steps=?
              WHERE workspace_id=? AND id=?""",
           (fields["name"], fields["icon"], fields["tag"], fields["anchor"], fields["notes"],
            payload, ws_id, rid))
        S.audit("template_edited", fields["name"])
        return rid
    new = ins("own_templates", dict(workspace_id=ws_id, created_by=user_id, steps=payload, **fields))
    S.audit("template_saved", fields["name"])
    return new


def delete(ws_id, rid):
    ex("DELETE FROM own_templates WHERE workspace_id=? AND id=?", (ws_id, rid))
    S.audit("template_deleted", f"own_templates#{rid}")


def from_month(ws_id, year, month):
    """Turn what is already on the calendar for one month into a template.

    This is the quickest way anyone will ever make one: the month that worked is already typed
    in, and the only thing missing is the offsets. The earliest post becomes day 0, so the
    template can be dropped onto any date later.
    """
    import calendar as pycal
    last = pycal.monthrange(year, month)[1]
    rows = q("""SELECT title, channel, format, publish_date FROM content_items
                WHERE workspace_id=? AND publish_date>=? AND publish_date<=? AND title<>''
                ORDER BY publish_date""",
             (ws_id, f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last:02d}"))
    if not rows:
        return None
    import datetime as dt
    base = dt.date.fromisoformat(rows[0]["publish_date"][:10])
    steps = []
    for r in rows[:MAX_STEPS]:
        try:
            day = (dt.date.fromisoformat(r["publish_date"][:10]) - base).days
        except ValueError:
            continue
        steps.append(dict(day=day, kind="post", title=r["title"][:200],
                          channel=r["channel"] or "", format=r["format"] or ""))
    return steps or None
