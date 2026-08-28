GATES = {
    "quiet_hours_ist_2100_0900": "Night in India (9pm–9am). We do not ping customers then.",
    "max_3_attempts_per_customer_day": "This customer already had 3 recovery tries today. We stop.",
    "duplicate_payment_link_guard": "A link for this amount was already created. We will not send another.",
    "amount_gt_10000_needs_approval": "Over ₹10,000. A person must approve before any link or retry.",
    "env_kill_switch": "Kill switch is on. All recovery is frozen.",
    "redis_kill_switch": "Kill switch is on. All recovery is frozen.",
    "merchant_kill_switch": "This merchant paused the agent.",
    "unmapped_cause": "We do not have a playbook for this cause.",
}

PLAYBOOKS = {
    "bank_downtime": (
        "schedule_retry_backoff",
        "The bank or switch looks down. Retrying now would fail again. We wait, then retry.",
    ),
    "insufficient_funds": (
        "schedule_retry_balance_window",
        "The account likely had too little money. We wait for a typical top-up window instead of nagging now.",
    ),
    "auth_failure": (
        "send_payment_link",
        "PIN or 3DS failed. They need a fresh checkout session — a new Payment Link, not a silent debit.",
    ),
    "abandonment": (
        "send_single_reminder_link",
        "They left checkout. One reminder link only. If they ignore it, we stop.",
    ),
    "manual_review": (
        "hold_manual_review",
        "We are not sure enough to touch the customer. Nothing was sent.",
    ),
}


def gate_text(code: str | None) -> str:
    if not code:
        return ""
    return GATES.get(code, code.replace("_", " "))


def source_text(src: str | None) -> str:
    if not src:
        return "Unknown"
    if src.startswith("rule:"):
        return f"Known Razorpay error — rules matched {src[5:]}. The model was not used."
    if src == "llm_error":
        return (
            "The error text was unfamiliar, so we asked the local model. "
            "Ollama did not answer (not running, or qwen2.5:1.5b not pulled in this container). "
            "We refused to guess, so nobody was contacted."
        )
    if src == "llm_low_confidence":
        return "The local model was unsure (confidence under 60%). We held the case."
    if src == "llm_fallback":
        return "The model returned unusable JSON. We held the case."
    if src.startswith("llm"):
        return "Unfamiliar error text — local model classified it."
    if src == "simulator":
        return "Seeded test outcome for the batch. Not money in a bank."
    if src == "gate":
        return "A stopping rule blocked this before any customer message."
    return src
