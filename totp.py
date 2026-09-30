"""Time-based one-time passwords (RFC 6238) for two-factor login. Compatible with Google Authenticator, Microsoft Authenticator, Authy, 1Password."""
import base64, hashlib, hmac, secrets, struct, time
from urllib.parse import quote

ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _hotp(secret, counter, digits=6):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    h = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = h[-1] & 15
    return str((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 10 ** digits).zfill(digits)


def step_now(t=None):
    return int((time.time() if t is None else t) // 30)


def code_at(secret, step):
    return _hotp(secret, step)


def verify(secret, code, last_step=0, window=1, t=None):
    """Returns the matched time-step (store it to block replays) or None."""
    code = (code or "").strip().replace(" ", "")
    if not (code.isdigit() and len(code) == 6):
        return None
    now = step_now(t)
    for s in range(now - window, now + window + 1):
        if s > last_step and hmac.compare_digest(_hotp(secret, s), code):
            return s
    return None


def uri(secret, email, issuer):
    return f"otpauth://totp/{quote(issuer)}:{quote(email)}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"


def new_recovery_codes(n=8):
    return ["".join(secrets.choice(ALPHABET) for _ in range(10)) for _ in range(n)]
