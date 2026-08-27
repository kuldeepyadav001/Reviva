from dataclasses import dataclass


@dataclass(frozen=True)
class RuleHit:
    root_cause: str
    retry_class: str
    rule_id: str
    reasoning: str
    confidence: float = 1.0


REASON_MAP: dict[str, RuleHit] = {
    "insufficient_funds": RuleHit(
        "insufficient_funds", "hard", "R_IF_REASON",
        "Razorpay reason insufficient_funds.",
    ),
    "payment_timed_out": RuleHit(
        "bank_downtime", "soft", "R_TIMEOUT",
        "Timeout — treat as transient infrastructure.",
    ),
    "gateway_error": RuleHit(
        "bank_downtime", "soft", "R_GATEWAY",
        "Gateway/issuer error — backoff, never instant retry.",
    ),
    "server_error": RuleHit(
        "bank_downtime", "soft", "R_SERVER",
        "Acquirer/server error.",
    ),
    "authentication_failed": RuleHit(
        "auth_failure", "session", "R_AUTH",
        "Auth/3DS failed — new session, not silent debit.",
    ),
    "incorrect_pin": RuleHit(
        "auth_failure", "session", "R_PIN",
        "Incorrect PIN — customer-present retry.",
    ),
}

DESC_NEEDLES: list[tuple[str, RuleHit]] = [
    ("insufficient fund", REASON_MAP["insufficient_funds"]),
    ("z9", REASON_MAP["insufficient_funds"]),
    ("bank is down", REASON_MAP["gateway_error"]),
    ("u28", REASON_MAP["gateway_error"]),
    ("timeout", REASON_MAP["payment_timed_out"]),
    ("timed out", REASON_MAP["payment_timed_out"]),
    ("3ds", REASON_MAP["authentication_failed"]),
    ("authentication", REASON_MAP["authentication_failed"]),
    ("incorrect pin", REASON_MAP["incorrect_pin"]),
    ("abandoned", RuleHit("abandonment", "abandon", "R_ABANDON", "Checkout abandonment.")),
    ("user dropped", RuleHit("abandonment", "abandon", "R_DROP", "User dropped.")),
]


def classify_rules(
    error_reason: str | None,
    error_code: str | None,
    error_description: str | None,
    event_type: str | None = None,
) -> RuleHit | None:
    reason = (error_reason or "").strip().lower()
    if reason in REASON_MAP:
        return REASON_MAP[reason]
    blob = " ".join(x for x in [error_reason, error_code, error_description, event_type] if x).lower()
    for needle, hit in DESC_NEEDLES:
        if needle in blob:
            return hit
    return None
