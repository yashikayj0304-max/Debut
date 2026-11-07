"""Run once:  python gen_vapid.py   then add the two lines as environment variables on Render (VAPID_PUBLIC, VAPID_PRIVATE)."""
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization as s
k = ec.generate_private_key(ec.SECP256R1())
b = lambda x: base64.urlsafe_b64encode(x).rstrip(b"=").decode()
pub = k.public_key().public_bytes(s.Encoding.X962, s.PublicFormat.UncompressedPoint)
priv = k.private_numbers().private_value.to_bytes(32, "big")
print("VAPID_PUBLIC=" + b(pub))
print("VAPID_PRIVATE=" + b(priv))
