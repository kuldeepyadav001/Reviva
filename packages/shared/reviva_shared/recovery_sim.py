import hashlib
import random

SIM_P = {
    "schedule_retry_backoff": 0.70,
    "schedule_retry_balance_window": 0.35,
    "send_payment_link": 0.45,
    "send_single_reminder_link": 0.22,
    "hold_manual_review": 0.0,
    "none": 0.0,
}


def seeded_recover(payment_id: str, action_type: str) -> bool:
    h = int(hashlib.sha256(f"{payment_id}:{action_type}".encode()).hexdigest(), 16)
    return random.Random(h).random() < SIM_P.get(action_type, 0.0)
