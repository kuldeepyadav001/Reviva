import hashlib
import hmac


def razorpay_webhook_signature(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def verify_razorpay_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if not secret or not signature:
        return False
    expected = razorpay_webhook_signature(raw_body, secret)
    return hmac.compare_digest(expected, signature)
