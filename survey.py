"""Stand-alone feedback survey: public page + submit endpoint, owner-only results (ADMIN_EMAILS).
The page has no link to the app and is never linked from it; share the /survey URL yourself."""
import json, os
from flask import Blueprint, request, jsonify, Response, abort, g
import services as S
from db import q, ins
from extensions import csrf, limiter

bp = Blueprint("survey", __name__)
csrf.exempt(bp)  # public form posts from anonymous visitors (no cookies/session involved); size- and rate-limited below
_HERE = os.path.join(os.path.dirname(__file__), "survey_page", "survey.html")
SHIM = """<script>(function(){var A=%s;function uid(){try{var u=localStorage.getItem("sv_uid");if(!u){u=Math.random().toString(36).slice(2);localStorage.setItem("sv_uid",u)}return u}catch(e){return"anon"}}
window.claude={use:async function(n){
if(n==="user")return{id:async function(){return uid()},isOwner:async function(){return A}};
if(n==="db")return{collection:function(){var c={doc:function(){return{set:async function(a){var r=await fetch("/survey/submit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(a)});if(!r.ok)throw 0}}},orderBy:function(){return c},limit:function(){return c},
onSnapshot:function(ok,bad){fetch("/admin/survey/data",{credentials:"same-origin"}).then(function(r){return r.ok?r.json():Promise.reject()}).then(function(rows){ok({docs:rows.map(function(d){return{data:function(){return d}}})})},bad)}};return c}};
if(n==="downloads")return{save:async function(o){var u=URL.createObjectURL(o.data),a=document.createElement("a");a.href=u;a.download=o.filename;document.body.appendChild(a);a.click();a.remove()}};
return null}}})();</script>"""


def _page(admin):
    with open(_HERE, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("<!--SHIM-->", SHIM % ("true" if admin else "false"), 1)
    r = Response(html, mimetype="text/html")
    r.headers["X-Robots-Tag"] = "noindex, nofollow"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Cache-Control"] = "no-store" if admin else "no-cache"
    return r


@bp.route("/survey")
def public():
    return _page(False)


@bp.route("/survey/submit", methods=["POST"])
@limiter.limit("30 per hour")
def submit():
    raw = request.get_data(cache=False)
    if len(raw) > 60000:
        abort(413)
    try:
        a = json.loads(raw)
    except ValueError:
        abort(400)
    if not isinstance(a, dict) or not a:
        abort(400)
    ins("survey_responses", {"data": json.dumps(a, ensure_ascii=False)})
    return jsonify(ok=True)


def _admin_only():
    if not S.is_platform_admin(g.get("user")):
        abort(404)


@bp.route("/admin/survey")
def admin_page():
    _admin_only()
    return _page(True)


@bp.route("/admin/survey/data")
def admin_data():
    _admin_only()
    rows = q("SELECT data, created_at FROM survey_responses ORDER BY id DESC LIMIT 1000")
    out = []
    for r in rows:
        try:
            d = json.loads(r["data"])
        except ValueError:
            continue
        d.setdefault("at", str(r["created_at"]))
        d["at"] = d["at"] if isinstance(d["at"], (int, float)) else d["at"]
        out.append(d)
    resp = jsonify(out)
    resp.headers["Cache-Control"] = "no-store"
    return resp
