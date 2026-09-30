from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["2000 per day", "600 per hour"])


@limiter.request_filter
def _skip_static():
    return request.endpoint in ("static", "health")
