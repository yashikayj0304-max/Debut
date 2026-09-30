"""REST API (Team / Agency plans). Authenticate with a workspace API key:  Authorization: Bearer gtm_xxxxx
Generic CRUD over every module, e.g.  GET/POST /api/v1/leads   GET/PATCH/DELETE /api/v1/leads/12   POST /api/v1/kpis (push analytics from Zapier/Make/scripts)."""
import re
from flask import Blueprint, g, request, jsonify, abort
import config as C
import services as S
import views
from db import q, ex, ins, qi
from extensions import csrf, limiter
from modules import MODULES, MODULE_FEATURE

bp = Blueprint("api", __name__, url_prefix="/api/v1")
csrf.exempt(bp)                                   # bearer-token API: no cookies, so no CSRF surface
limiter.limit("300 per minute", key_func=lambda: request.headers.get("Authorization", "")[-20:] or request.remote_addr)(bp)


def err(msg, code):
    return jsonify(error=msg), code


@bp.before_request
def authenticate():
    h = request.headers.get("Authorization", "")
    if not h.startswith("Bearer ") or len(h) > 200:
        return err("Send your API key as 'Authorization: Bearer <key>'.", 401)
    k = q("SELECT * FROM api_keys WHERE key_hash=?", (S.sha(h[7:].strip()),), one=True)
    ws = q("SELECT * FROM workspaces WHERE id=?", (k["workspace_id"],), one=True) if k else None
    if not ws:
        return err("Invalid or revoked API key.", 401)
    g.ws, g.api_key, g.user, g.role = ws, k, None, None
    g.plan_key = S.plan_key(ws)
    g.plan = C.PLANS[g.plan_key]
    if "api" not in g.plan["features"]:
        return err("API access is included in the Team and Agency plans.", 403)
    today = S.today().isoformat()
    if (k["last_used"] or "") != today:
        ex("UPDATE api_keys SET last_used=? WHERE id=?", (today, k["id"]))


def module_or_err(name):
    if name not in MODULES:
        abort(404)
    feat = MODULE_FEATURE.get(name)
    if feat and feat not in g.plan["features"]:
        abort(403)
    return MODULES[name]


def need_write():
    if g.api_key["scope"] != "write":
        abort(403)


def out(row):
    return {k: (v if isinstance(v, (str, int, float, type(None))) else str(v)) for k, v in dict(row).items() if k != "workspace_id"}


def body():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        abort(400)
    return d


@bp.errorhandler(400)
def _400(e):
    return err("Send a JSON object.", 400)


@bp.errorhandler(403)
def _403(e):
    return err("Not allowed for this key, plan or module.", 403)


@bp.errorhandler(404)
def _404(e):
    return err("Not found.", 404)


@bp.route("/")
def index():
    return jsonify(workspace=g.ws["slug"], scope=g.api_key["scope"],
                   modules={k: [dict(name=f[0], label=f[1], type=f[2], options=f[3] or None) for f in m["fields"]] for k, m in MODULES.items() if not MODULE_FEATURE.get(k) or MODULE_FEATURE[k] in g.plan["features"]})


@bp.route("/<module>", methods=["GET"])
def list_records(module):
    m = module_or_err(module)
    limit = min(S.to_int(request.args.get("limit"), 50), 200)
    offset = min(S.to_int(request.args.get("offset"), 0), 1_000_000)
    where, args = ["workspace_id=?"], [g.ws["id"]]
    for f in m["fields"]:
        if f[0] in request.args:
            where.append(f"{qi(f[0])}=?")
            args.append(S.clean_text(request.args.get(f[0]), 300))
    term = S.clean_text(request.args.get("q"), 100).lower()
    if term:
        where.append("(" + " OR ".join(f"LOWER({qi(f[0])}) LIKE ?" for f in m["fields"]) + ")")
        args += [f"%{term}%"] * len(m["fields"])
    total = q(f"SELECT COUNT(*) c FROM {module} WHERE " + " AND ".join(where), args, one=True)["c"]
    rows = q(f"SELECT * FROM {module} WHERE " + " AND ".join(where) + f" ORDER BY id DESC LIMIT {limit} OFFSET {offset}", args)
    return jsonify(total=total, limit=limit, offset=offset, data=[out(r) for r in rows])


@bp.route("/<module>/<int:rid>", methods=["GET"])
def get_record(module, rid):
    module_or_err(module)
    r = q(f"SELECT * FROM {module} WHERE id=? AND workspace_id=?", (rid, g.ws["id"]), one=True) or abort(404)
    return jsonify(out(r))


@bp.route("/<module>", methods=["POST"])
def create_record(module):
    m = module_or_err(module)
    need_write()
    if S.record_count(g.ws["id"]) >= g.plan["records"]:
        return err(f"Record limit reached for the {g.plan['name']} plan.", 403)
    data = views.clean_fields(m, body(), quiet=True)
    data["workspace_id"] = g.ws["id"]
    rid = ins(module, data)
    S.audit("api_create", f"{module}#{rid}", wid=g.ws["id"], uid=g.api_key["user_id"])
    return jsonify(id=rid), 201


@bp.route("/<module>/<int:rid>", methods=["PATCH", "PUT"])
def update_record(module, rid):
    m = module_or_err(module)
    need_write()
    q(f"SELECT 1 FROM {module} WHERE id=? AND workspace_id=?", (rid, g.ws["id"]), one=True) or abort(404)
    data = views.clean_fields(m, body(), quiet=True, partial=True)
    if data:
        ex(f"UPDATE {module} SET " + ",".join(f"{qi(n)}=?" for n in data) + " WHERE id=? AND workspace_id=?", list(data.values()) + [rid, g.ws["id"]])
        S.audit("api_update", f"{module}#{rid}", wid=g.ws["id"], uid=g.api_key["user_id"])
    return jsonify(ok=True)


@bp.route("/<module>/<int:rid>", methods=["DELETE"])
def delete_record(module, rid):
    module_or_err(module)
    need_write()
    n = ex(f"DELETE FROM {module} WHERE id=? AND workspace_id=?", (rid, g.ws["id"]))
    if not n:
        abort(404)
    S.audit("api_delete", f"{module}#{rid}", wid=g.ws["id"], uid=g.api_key["user_id"])
    return jsonify(ok=True)
