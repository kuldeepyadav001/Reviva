import os
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class GateResult:
    allowed: bool
    reason: str


class MemoryRedis:
    def __init__(self):
        self._d: dict[str, str] = {}

    def get(self, key):
        return self._d.get(key)

    def set(self, key, val, nx=False, ex=None):
        if nx and key in self._d:
            return False
        self._d[key] = val
        return True

    def incr(self, key):
        n = int(self._d.get(key) or 0) + 1
        self._d[key] = str(n)
        return n

    def expire(self, key, ttl):
        return True


def quiet_hours(now: datetime | None = None, start: int = 21, end: int = 9) -> GateResult:
    if os.getenv("SKIP_QUIET_HOURS", "").lower() in ("1", "true", "yes"):
        return GateResult(True, "ok")
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    hour = now.astimezone(IST).hour
    if hour >= start or hour < end:
        return GateResult(False, "quiet_hours_ist_2100_0900")
    return GateResult(True, "ok")


def kill_switch(r, merchant_id: str, env_flag: bool = False) -> GateResult:
    if env_flag:
        return GateResult(False, "env_kill_switch")
    if r.get(f"kill:{merchant_id}") == "1":
        return GateResult(False, "redis_kill_switch")
    return GateResult(True, "ok")


def attempt_cap(r, customer_ref: str, now: datetime | None = None, max_n: int = 3) -> GateResult:
    now = now or datetime.now(IST)
    day = now.astimezone(IST).strftime("%Y-%m-%d")
    n = int(r.get(f"attempts:{customer_ref}:{day}") or 0)
    if n >= max_n:
        return GateResult(False, "max_3_attempts_per_customer_day")
    return GateResult(True, "ok")


def bump_attempt(r, customer_ref: str, now: datetime | None = None) -> int:
    now = now or datetime.now(IST)
    day = now.astimezone(IST).strftime("%Y-%m-%d")
    key = f"attempts:{customer_ref}:{day}"
    return r.incr(key)


def duplicate_link(r, customer_ref: str, amount_paise: int) -> GateResult:
    if r.get(f"link:{customer_ref}:{amount_paise}"):
        return GateResult(False, "duplicate_payment_link_guard")
    return GateResult(True, "ok")


def mark_link(r, customer_ref: str, amount_paise: int) -> None:
    r.set(f"link:{customer_ref}:{amount_paise}", "1")


def high_value(amount_paise: int, limit: int = 1_000_000) -> GateResult:
    if amount_paise > limit:
        return GateResult(False, "amount_gt_10000_needs_approval")
    return GateResult(True, "ok")
