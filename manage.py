"""Ops commands:  python manage.py init-db | list | verify-user <email> | reset-2fa <email> | send-digests | refresh-pulse | set-plan <slug> <plan> | extend-trial <slug> <days>"""
import sys, datetime as dt
from app import create_app
import services as S
import config as C
from db import q, ex

app = create_app(init=True)
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
with app.app_context():
    if cmd == "init-db":
        print("schema ready")
    elif cmd == "list":
        for w in q("SELECT * FROM workspaces ORDER BY id"):
            print(w["id"], w["slug"], w["plan"], w["plan_status"], "trial_ends=" + (w["trial_ends"] or "-"))
    elif cmd == "refresh-pulse":
        n = 0
        for w in q("SELECT * FROM workspaces ORDER BY id LIMIT 500"):
            plan = S.plan_of(w)
            last = S.latest_pulse(w["id"])
            if q("SELECT 1 FROM watchlist WHERE workspace_id=? LIMIT 1", (w["id"],), one=True) and (not last or S.pulse_age_minutes(last) > C.PULSE_CACHE_MINUTES):
                try:
                    S.run_pulse(w["id"], w["industry"], plan)
                    n += 1
                except Exception as e:
                    print("pulse failed for", w["slug"], type(e).__name__)
        print("pulse refreshed for", n, "workspace(s)")
    elif cmd == "send-digests":
        print("digests sent:", S.send_digests())
    elif cmd == "reset-2fa" and len(sys.argv) == 3:
        n = ex("UPDATE users SET totp_on=0, totp_secret='', recovery='', totp_last=0 WHERE email=?", (sys.argv[2].strip().lower(),))
        print("2FA reset" if n else "no such user")
    elif cmd == "verify-user" and len(sys.argv) == 3:
        n = ex("UPDATE users SET email_verified=1 WHERE email=?", (sys.argv[2].strip().lower(),))
        print("verified" if n else "no such user")
    elif cmd == "set-plan" and len(sys.argv) == 4:
        assert sys.argv[3] in C.PAID_PLANS, f"plan must be one of {C.PAID_PLANS}"
        ex("UPDATE workspaces SET plan=?, plan_status='active', period_end=? WHERE slug=?", (sys.argv[3], (S.today() + dt.timedelta(days=3650)).isoformat(), sys.argv[2]))
        print("updated")
    elif cmd == "extend-trial" and len(sys.argv) == 4:
        ex("UPDATE workspaces SET trial_ends=? WHERE slug=?", ((S.today() + dt.timedelta(days=int(sys.argv[3]))).isoformat(), sys.argv[2]))
        print("updated")
    else:
        print(__doc__)
