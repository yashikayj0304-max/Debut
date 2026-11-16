"""Real photo search for mood boards. Pexels or Unsplash when you add a free key, otherwise Openverse (no key, openly licensed photos)."""
import requests
import config as C

UA = {"User-Agent": "Debut/1.0 (mood board photo search)"}


def _pexels(qs, n):
    r = requests.get("https://api.pexels.com/v1/search", params={"query": qs, "per_page": n, "orientation": "landscape"}, headers={**UA, "Authorization": C.PEXELS_KEY}, timeout=8)
    r.raise_for_status()
    return [dict(thumb=p["src"]["medium"], full=p["src"]["large"], credit=f"Photo by {p.get('photographer', '')} on Pexels", link=p.get("url", "")) for p in r.json().get("photos", [])]


def _unsplash(qs, n):
    r = requests.get("https://api.unsplash.com/search/photos", params={"query": qs, "per_page": n, "orientation": "landscape"}, headers={**UA, "Authorization": "Client-ID " + C.UNSPLASH_KEY}, timeout=8)
    r.raise_for_status()
    return [dict(thumb=p["urls"]["small"], full=p["urls"]["regular"], credit=f"Photo by {p['user']['name']} on Unsplash", link=p["links"]["html"]) for p in r.json().get("results", [])]


def _openverse(qs, n):
    r = requests.get("https://api.openverse.org/v1/images/", params={"q": qs, "page_size": n, "license_type": "commercial", "mature": "false", "extension": "jpg"}, headers=UA, timeout=10)
    r.raise_for_status()
    out = []
    for p in r.json().get("results", []):
        if not p.get("url", "").startswith("https://"):
            continue
        out.append(dict(thumb=p.get("thumbnail") or p["url"], full=p["url"], credit=f"{p.get('title') or 'Photo'} by {p.get('creator') or 'unknown'} ({(p.get('license') or '').upper()} {p.get('license_version') or ''}) via Openverse".replace("  ", " "), link=p.get("foreign_landing_url", "")))
    return out


def search(qs, n=18):
    """List of {thumb, full, credit, link}. Raises when the provider is unreachable; the caller shows a friendly message."""
    if C.PEXELS_KEY:
        return _pexels(qs, n)
    if C.UNSPLASH_KEY:
        return _unsplash(qs, n)
    return _openverse(qs, n)


def provider():
    return "Pexels" if C.PEXELS_KEY else "Unsplash" if C.UNSPLASH_KEY else "Openverse"
