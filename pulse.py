"""Market Pulse: live market signals for a workspace's industry, competitors and keywords.
Every fetcher goes through services.safe_get (public URLs only, size and time limits) and returns a list of plain dicts, so the
whole thing can be tested with recorded responses. A failing source never breaks the page: its error is reported next to the results."""
import json, re, html, datetime as dt
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse
from xml.etree import ElementTree as ET
import config as C
import services as S

REGIONS = {"India": dict(hl="en-IN", gl="IN", ceid="IN:en", code="IN", name="India"), "Global": dict(hl="en-US", gl="US", ceid="US:en", code="US", name="Global")}
TECH_INDUSTRIES = {"saas", "startup", "b2b", "fintech", "agency", "personal_brand"}
STOP = set("""a about above after again against all also am an and any are as at be because been before being below between both but by can could did do does doing down during each few for from further had has have having he her here hers him his how i if in into is it its just me more most my no nor not of off on once only or other our out over own same she should so some such than that the their them then there these they this those through to too under until up us very was we were what when where which while who whom why will with would you your
says say said new news today week year years 2024 2025 2026 amid after over per via vs one two three top best latest live update updates report reports india indian global world market markets company companies business inc ltd pvt""".split())


def _clean(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def _safe_url(u):
    u = (u or "").strip()
    return u if re.match(r"^https?://[^\s]+$", u, re.I) and len(u) < 1000 else ""


def _ts(raw):
    try:
        return parsedate_to_datetime(raw).timestamp()
    except Exception:
        try:
            return dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0


def mk(title, url, source, ts, kind, extra=""):
    return dict(title=_clean(title)[:220], url=_safe_url(url), source=_clean(source)[:80], ts=float(ts or 0), kind=kind, extra=_clean(extra)[:120],
                date=dt.datetime.fromtimestamp(ts).strftime("%d %b") if ts else "")


# ------------------------------------------------------------------ news
def _rss_items(xml, kind, limit):
    root = ET.fromstring(xml)
    out = []
    for it in root.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"):
            continue
        d = {c.tag.split("}")[-1]: c for c in it}
        link = (d["link"].get("href") or d["link"].text or "") if d.get("link") is not None else ""
        src = d["source"].text if d.get("source") is not None else ""
        title = (d["title"].text or "") if d.get("title") is not None else ""
        if kind == "news" and not src and " - " in title:                 # Google News appends " - Publisher" to the headline
            title, src = title.rsplit(" - ", 1)
        elif kind == "news" and src and title.endswith(" - " + src):
            title = title[: -len(src) - 3]
        raw = next((d[k].text for k in ("pubDate", "published", "updated") if d.get(k) is not None and d[k].text), "")
        out.append(mk(title, link.strip(), src, _ts(raw), kind))
    return out[:limit]


def google_news(term, region, days=7, limit=8):
    r = REGIONS[region]
    q = quote_plus(f"{term} when:{days}d")
    return _rss_items(S.safe_get(f"https://news.google.com/rss/search?q={q}&hl={r['hl']}&gl={r['gl']}&ceid={r['ceid']}"), "news", limit)


def gnews_api(term, region, limit=8):
    r = REGIONS[region]
    d = json.loads(S.safe_get(f"https://gnews.io/api/v4/search?q={quote_plus(term)}&lang=en&country={r['code'].lower()}&max={limit}&sortby=publishedAt&apikey={quote_plus(C.GNEWS_API_KEY)}"))
    return [mk(a.get("title"), a.get("url"), (a.get("source") or {}).get("name"), _ts(a.get("publishedAt")), "news") for a in d.get("articles", [])][:limit]


def newsdata_api(term, region, limit=8):
    r = REGIONS[region]
    d = json.loads(S.safe_get(f"https://newsdata.io/api/1/news?apikey={quote_plus(C.NEWSDATA_API_KEY)}&q={quote_plus(term)}&country={r['code'].lower()}&language=en"))
    return [mk(a.get("title"), a.get("link"), a.get("source_name") or a.get("source_id"), _ts(a.get("pubDate")), "news") for a in d.get("results", [])][:limit]


def news(term, region):
    p = C.NEWS_PROVIDER
    if p == "gnews" and C.GNEWS_API_KEY:
        return gnews_api(term, region)
    if p == "newsdata" and C.NEWSDATA_API_KEY:
        return newsdata_api(term, region)
    return google_news(term, region)


# ------------------------------------------------------------------ other sources
def hacker_news(term, limit=6):
    since = int((dt.datetime.now() - dt.timedelta(days=30)).timestamp())
    d = json.loads(S.safe_get(f"https://hn.algolia.com/api/v1/search?query={quote_plus(term)}&tags=story&numericFilters=created_at_i>{since}&hitsPerPage={limit}"))
    return [mk(h.get("title"), h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}", "Hacker News", h.get("created_at_i"), "hn",
               f"{h.get('points', 0)} points, {h.get('num_comments', 0)} comments") for h in d.get("hits", []) if h.get("title")][:limit]


def reddit(sub, limit=8):
    if not re.match(r"^[A-Za-z0-9_]{2,30}$", sub):
        raise ValueError("not a valid subreddit name")
    return _rss_items(S.safe_get(f"https://www.reddit.com/r/{sub}/top/.rss?t=week"), "reddit", limit)


def youtube(term, region, limit=6):
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = REGIONS[region]
    d = json.loads(S.safe_get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&order=viewCount&maxResults={limit}&q={quote_plus(term)}&regionCode={r['code']}&publishedAfter={since}&key={quote_plus(C.YOUTUBE_API_KEY)}"))
    vids = [(i["id"]["videoId"], i["snippet"]) for i in d.get("items", []) if i.get("id", {}).get("videoId")]
    views = {}
    if vids:
        try:
            st = json.loads(S.safe_get(f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={','.join(v for v, _ in vids)}&key={quote_plus(C.YOUTUBE_API_KEY)}"))
            views = {x["id"]: int(x.get("statistics", {}).get("viewCount", 0)) for x in st.get("items", [])}
        except Exception:
            pass
    return [mk(sn.get("title"), f"https://www.youtube.com/watch?v={vid}", sn.get("channelTitle"), _ts(sn.get("publishedAt")), "youtube", f"{views[vid]:,} views" if vid in views else "") for vid, sn in vids]


def trends_now(geo, limit=12):
    """Google's public 'trending now' feed for a country: what people are searching for today."""
    root = ET.fromstring(S.safe_get(f"https://trends.google.com/trending/rss?geo={quote_plus(geo)}"))
    out = []
    for it in root.iter("item"):
        d = {c.tag.split("}")[-1]: c for c in it}
        t = d["title"].text if d.get("title") is not None else ""
        traffic = d["approx_traffic"].text if d.get("approx_traffic") is not None else ""
        news_t = ""
        for c in it:
            if c.tag.split("}")[-1] == "news_item":
                nt = {x.tag.split("}")[-1]: x for x in c}
                news_t = (nt["news_item_title"].text if nt.get("news_item_title") is not None else "")
                break
        out.append(dict(term=_clean(t)[:80], traffic=_clean(traffic)[:20], context=_clean(news_t)[:160]))
    return [o for o in out if o["term"]][:limit]


def public_holidays(country, year):
    d = json.loads(S.safe_get(f"https://date.nager.at/api/v3/PublicHolidays/{int(year)}/{quote_plus(country.upper())}"))
    return [dict(name=h.get("name") or h.get("localName"), date=h.get("date")) for h in d if h.get("date")]


# ------------------------------------------------------------------ analysis
def top_terms(titles, exclude=(), n=12):
    """Words and two-word phrases that keep showing up across headlines (a simple, transparent trend signal)."""
    skip = {w for x in exclude for w in re.findall(r"[a-z][a-z'\-]+", x.lower())}
    uni, bi = Counter(), Counter()
    for t in titles:
        words = [w for w in re.findall(r"[a-z][a-z'\-]{2,}", t.lower())]
        keep = [w if w not in STOP and w not in skip else None for w in words]
        for w in keep:
            if w:
                uni[w] += 1
        for a, b in zip(keep, keep[1:]):
            if a and b:
                bi[f"{a} {b}"] += 1
    ranked = [(k, c) for k, c in bi.most_common(40) if c >= 2] + [(k, c) for k, c in uni.most_common(60) if c >= 2]
    out, seen = [], set()
    for k, c in ranked:
        if any(k in o or o in k for o in seen):
            continue
        seen.add(k)
        out.append((k, c))
        if len(out) >= n:
            break
    return out


def collect(watch, industry, geo=("IN", "US")):
    """watch: list of dicts(term, type, region). Returns the snapshot stored and shown on the Pulse page."""
    jobs = []                                                     # (group_index, label, fn)
    groups = []
    for w in watch:
        gi = len(groups)
        groups.append(dict(term=w["term"], type=w["type"], region=w["region"], items=[], errors=[]))
        regs = ["India", "Global"] if w["region"] == "Both" else [w["region"]]
        if w["type"] == "Subreddit":
            if C.PULSE_REDDIT:
                jobs.append((gi, "Reddit", lambda t=w["term"]: reddit(t)))
            else:
                groups[gi]["errors"].append("Reddit is switched off (PULSE_REDDIT=0)")
            continue
        for r in regs:
            jobs.append((gi, f"News ({r})", lambda t=w["term"], r=r: news(t, r)))
        if C.PULSE_HN and industry in TECH_INDUSTRIES and "Global" in regs:
            jobs.append((gi, "Hacker News", lambda t=w["term"]: hacker_news(t)))
        if C.YOUTUBE_API_KEY:
            jobs.append((gi, "YouTube", lambda t=w["term"], r=regs[0]: youtube(t, r)))
    tjobs = []
    if C.PULSE_TRENDS:
        for name, g in zip(("India", "Global"), geo):
            tjobs.append((name, lambda g=g: trends_now(g)))

    def run(job):
        try:
            return job[0], job[1], job[2](), None
        except Exception as e:
            return job[0], job[1], [], f"{job[1]}: {type(e).__name__}"

    def runt(job):
        try:
            return job[0], job[1](), None
        except Exception as e:
            return job[0], [], f"Trending searches ({job[0]}): {type(e).__name__}"

    errors, trends = [], {}
    with ThreadPoolExecutor(8) as pool:
        for gi, label, items, err in pool.map(run, jobs):
            if err:
                groups[gi]["errors"].append(err)
                errors.append(f"{groups[gi]['term']}: {err}")
            groups[gi]["items"] += items
        for name, items, err in pool.map(runt, tjobs):
            trends[name] = items
            if err:
                errors.append(err)
    for g in groups:                                              # newest first, no duplicate links, at most 10 per term
        seen, uniq = set(), []
        for it in sorted(g["items"], key=lambda x: -x["ts"]):
            key = it["url"] or it["title"]
            if key not in seen:
                seen.add(key)
                uniq.append(it)
        g["items"] = uniq[:10]
    titles = [i["title"] for g in groups for i in g["items"] if i["kind"] != "youtube"]
    terms = top_terms(titles, exclude=[g["term"] for g in groups])
    return dict(generated=dt.datetime.now().isoformat(timespec="minutes"), groups=groups, trends=trends, terms=terms, errors=errors, sources=sorted({j[1].split(" (")[0] for j in jobs}))
