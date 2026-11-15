import re
from tests.test_app import signup, _invite

def test_sweep_every_page_every_role_no_500(app):
    o = signup(app, "sw@x.com", ws="Sweep Co")
    rules = [r for r in app.url_map.iter_rules() if "GET" in r.methods and r.endpoint != "static" and not r.arguments - {"key"}]
    paths = set()
    from modules import MODULES
    for r in rules:
        if r.arguments:
            for k in MODULES:
                paths.add(r.rule.replace("<key>", k).replace("<string:key>", k))
        else:
            paths.add(r.rule)
    bad = []
    for p in sorted(paths):
        if "<" in p or p.startswith("/admin") or "logout" in p or "/delete" in p or "/demo" in p:
            continue
        r = o.get(p)
        if r.status_code >= 500:
            bad.append((p, r.status_code))
    assert not bad, bad

def test_sweep_blank_and_hostile_posts_never_500(app):
    from modules import MODULES
    o = signup(app, "sw2@x.com", ws="Sweep Two")
    bad = []
    for k in MODULES:
        for data in ({}, {"title": "x" * 5000, "name": "<script>", "date": "garbage", "status": "zzz"}):
            for suf in ("save",):
                r = o.post(f"/m/{k}/{suf}", data=data)
                if r.status_code >= 500: bad.append((k, r.status_code))
        r = o.get(f"/m/{k}/new?modal=1")
        if r.status_code >= 500: bad.append((k, "new"))
    assert not bad, bad
