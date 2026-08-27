from dataclasses import dataclass

from reviva_shared import gates

PLAYBOOKS = {
    "bank_downtime": ("schedule_retry_backoff", "soft failure: exponential backoff"),
    "insufficient_funds": ("schedule_retry_balance_window", "next IST morning window or one link"),
    "auth_failure": ("send_payment_link", "fresh Payment Link session"),
    "abandonment": ("send_single_reminder_link", "exactly one reminder then stop"),
    "manual_review": ("hold_manual_review", "human"),
}


@dataclass
class PolicyDecision:
    action_type: str
    status: str
    block_reason: str | None
    playbook: str


def decide(
    *,
    redis,
    merchant_id: str,
    customer_ref: str,
    amount_paise: int,
    root_cause: str,
    env_kill: bool = False,
    now=None,
) -> PolicyDecision:
    g = gates.kill_switch(redis, merchant_id, env_kill)
    if not g.allowed:
        return PolicyDecision("none", "blocked", g.reason, "gate")
    g = gates.attempt_cap(redis, customer_ref, now=now)
    if not g.allowed:
        return PolicyDecision("none", "blocked", g.reason, "gate")
    g = gates.quiet_hours(now=now)
    if not g.allowed:
        return PolicyDecision("none", "blocked", g.reason, "gate")
    g = gates.high_value(amount_paise)
    if not g.allowed:
        return PolicyDecision("none", "pending_approval", g.reason, "gate")
    if root_cause not in PLAYBOOKS:
        return PolicyDecision("hold_manual_review", "pending_approval", "unmapped_cause", "fallback")
    action, why = PLAYBOOKS[root_cause]
    if action in ("send_payment_link", "send_single_reminder_link"):
        g = gates.duplicate_link(redis, customer_ref, amount_paise)
        if not g.allowed:
            return PolicyDecision("none", "blocked", g.reason, "gate")
    status = "scheduled" if action.startswith("schedule_") else "execute"
    if action == "hold_manual_review":
        status = "pending_approval"
    return PolicyDecision(action, status, None, why)
