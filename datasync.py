"""Read the report a platform lets you export (Meta Ads / Instagram Insights, Google Ads, GA4, a Sheets download)
and turn it into dated results. No account connection and no API keys: the person downloads the report, drops it here."""
import csv, io, re

DATE_HEADS = ("date", "day", "week", "month", "reporting starts", "reporting ends", "start date", "period", "nth day", "published", "time")
SKIP_HEADS = ("id", "name", "campaign", "ad set", "ad name", "account", "currency", "status", "delivery", "objective", "url", "link",
              "title", "post", "description", "type", "source", "medium", "country", "city", "device", "page", "age", "gender", "bid", "budget type")
NICE = {"impr": "Impressions", "impr.": "Impressions", "avg. cpc": "CPC", "avg. cost": "CPC", "cost per result": "Cost per result", "imp.": "Impressions", "impressions": "Impressions", "reach": "Reach", "clicks": "Clicks", "link clicks": "Link clicks",
        "ctr": "CTR %", "cpc": "CPC", "cpm": "CPM", "cost": "Spend", "amount spent": "Spend", "spend": "Spend", "cost (inr)": "Spend",
        "conv.": "Conversions", "conversions": "Conversions", "results": "Results", "purchases": "Purchases", "roas": "ROAS", "sessions": "Sessions",
        "users": "Users", "active users": "Active users", "new users": "New users", "views": "Views", "engagement rate": "Engagement rate %",
        "followers": "Followers", "likes": "Likes", "comments": "Comments", "shares": "Shares", "saves": "Saves", "profile visits": "Profile visits"}


def _num(v):
    s = str(v or "").strip()
    if not s or s in ("-", "--", "—", "N/A", "n/a"):
        return None
    pct = s.endswith("%")
    s = re.sub(r"[₹$€£,\s%]|Rs\.?|INR|USD", "", s)
    if re.fullmatch(r"\(.*\)", s):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


def guess_channel(filename, headers):
    t = (filename + " " + " ".join(headers)).lower()
    for words, ch in ((("google ads", "adwords", "impr.", "avg. cpc"), "Google Ads"), (("ga4", "analytics", "sessions", "engaged sessions", "active users"), "Website"),
                      (("instagram", "ig ", "profile visits", "reels"), "Instagram"), (("facebook", "meta", "amount spent", "reporting starts"), "Meta Ads"),
                      (("linkedin",), "LinkedIn"), (("youtube",), "YouTube")):
        if any(w in t for w in words):
            return ch
    return "Other"


def read_export(text, filename="", channel="", norm=lambda v: v):
    """Returns (rows, info). rows = [{metric, channel, period, value}], info = {channel, columns, skipped}."""
    text = text.lstrip("﻿")
    lines = [l for l in text.splitlines()]
    delim = "\t" if sum(l.count("\t") for l in lines[:20]) > sum(l.count(",") for l in lines[:20]) else ","
    grid = [r for r in csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)]
    hi = None
    for i, r in enumerate(grid[:40]):
        cells = [c.strip() for c in r if c.strip()]
        if len(cells) >= 2 and not cells[0].startswith("#") and sum(_num(c) is None for c in cells) >= max(2, len(cells) - 1):
            hi = i
            break
    if hi is None:
        return [], {"error": "Could not find a header row. Export the report as CSV with column names on top."}
    head = [h.strip() for h in grid[hi]]
    di = next((j for j, h in enumerate(head) if h.lower() in DATE_HEADS or h.lower().startswith(("date", "day", "week", "month"))), None)
    cols = []
    for j, h in enumerate(head):
        if j == di or not h:
            continue
        hl = h.lower()
        if any(hl == s or hl.startswith(s + " ") and hl in ("campaign name", "ad set name", "ad name") for s in SKIP_HEADS) or hl in SKIP_HEADS:
            continue
        base = re.sub(r"\s*\(.*?\)", "", hl).strip()
        cols.append((j, NICE.get(hl) or NICE.get(base) or (base.title() if h.islower() else re.sub(r"\s*\(.*?\)", "", h).strip())))
    ch = channel or guess_channel(filename, head)
    out, skipped = [], 0
    for r in grid[hi + 1:]:
        if not any(c.strip() for c in r):
            continue
        per = norm(r[di]) if di is not None and di < len(r) else ""
        if di is not None and not per:
            skipped += 1      # totals rows, notes, or dates that can't be read
            continue
        for j, name in cols:
            if j >= len(r):
                continue
            v = _num(r[j])
            if v is None:
                continue
            out.append(dict(metric=name[:80], channel=ch, period=per, value=v))
    names = []
    for _, n in cols:
        if n not in names and any(x["metric"] == n for x in out):
            names.append(n)
    return out, {"channel": ch, "columns": names, "skipped": skipped, "dated": di is not None}
