from conftest import signup
import re
def test_probe(app):
    o = signup(app, "pr@x.com")
    r = o.post("/m/tasks/new", data=dict(title="ProbeTask", status="To do"), follow_redirects=True)
    h = r.data.decode()
    print("TASKS list has title:", "ProbeTask" in h)
    print("edit links:", re.findall(r'href="(/m/tasks/\d+[^"]*)"', h)[:3])
    rid = re.search(r'/m/tasks/(\d+)', h)
    if rid:
        e = o.get(f"/m/tasks/{rid.group(1)}/edit"); print("edit status", e.status_code)
    r = o.post("/m/launch_checklist/new", data=dict(item="ProbeItem", phase="Pre-launch", status="To do"), follow_redirects=True)
    h = r.data.decode(); print("CHK after save has item:", "ProbeItem" in h)
    h2 = o.get("/m/launch_checklist").data.decode(); print("CHK list has item:", "ProbeItem" in h2, "rows", h2.count("<tr"), "page?", re.findall(r'page=\d+', h2)[:3])
    h3 = o.get("/m/launch_checklist?page=2").data.decode(); print("page2 has item:", "ProbeItem" in h3)
