import os
from typing import Any


def keys_configured() -> bool:
    kid = os.getenv("RAZORPAY_KEY_ID", "")
    sec = os.getenv("RAZORPAY_KEY_SECRET", "")
    if not kid or not sec:
        return False
    if "replace" in kid.lower() or "replace" in sec.lower() or "xxxx" in kid:
        return False
    if not kid.startswith("rzp_"):
        return False
    return True


def create_payment_link(
    amount_paise: int,
    payment_id: str,
    email: str | None,
    description: str,
) -> dict[str, Any]:
    """Test-mode Payment Link. Never SMS. Email only for non-sim addresses."""
    if not keys_configured():
        return {
            "id": f"plink_stub_{payment_id}",
            "short_url": None,
            "stub": True,
            "reason": "razorpay keys missing or placeholder",
        }
    import razorpay

    client = razorpay.Client(
        auth=(os.environ["RAZORPAY_KEY_ID"], os.environ["RAZORPAY_KEY_SECRET"])
    )
    fake = (email or "").endswith(".test") or (email or "").endswith("example.com")
    payload: dict[str, Any] = {
        "amount": int(amount_paise),
        "currency": "INR",
        "accept_partial": False,
        "description": (description or "Reviva recovery")[:200],
        "notify": {"sms": False, "email": bool(email) and not fake},
        "reminder_enable": False,
        "notes": {"reviva": "recovery", "failed_payment_id": payment_id},
    }
    if email and not fake:
        payload["customer"] = {"email": email}
    created = client.payment_link.create(payload)
    return {
        "id": created.get("id"),
        "short_url": created.get("short_url"),
        "stub": False,
    }
