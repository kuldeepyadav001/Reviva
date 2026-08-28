from dataclasses import dataclass

from reviva_shared import gates
from reviva_shared.human import PLAYBOOKS, gate_text


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
        return PolicyDecision("none", "blocked", g.reason, gate_text(g.reason))
    g = gates.attempt_cap(redis, customer_ref, now=now)
    if not g.allowed:
        return PolicyDecision("none", "blocked", g.reason, gate_text(g.reason))
    g = gates.quiet_hours(now=now)
    if not g.allowed:
        return PolicyDecision("none", "blocked", g.reason, gate_text(g.reason))
    g = gates.high_value(amount_paise)
    if not g.allowed:
        return PolicyDecision("none", "pending_approval", g.reason, gate_text(g.reason))
    if root_cause not in PLAYBOOKS:
        return PolicyDecision(
            "hold_manual_review",
            "pending_approval",
            "unmapped_cause",
            gate_text("unmapped_cause"),
        )
    action, why = PLAYBOOKS[root_cause]
    if action in ("send_payment_link", "send_single_reminder_link"):
        g = gates.duplicate_link(redis, customer_ref, amount_paise)
        if not g.allowed:
            return PolicyDecision("none", "blocked", g.reason, gate_text(g.reason))
    status = "scheduled" if action.startswith("schedule_") else "execute"
    if action == "hold_manual_review":
        status = "pending_approval"
    return PolicyDecision(action, status, None, why)
