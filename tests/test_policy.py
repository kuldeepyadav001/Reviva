from datetime import datetime
from zoneinfo import ZoneInfo

from reviva_shared.gates import MemoryRedis
from reviva_shared.policy import decide

IST = ZoneInfo("Asia/Kolkata")


def _day():
    return datetime(2026, 8, 27, 14, 0, tzinfo=IST)


def test_bank_downtime_schedules_backoff():
    d = decide(
        redis=MemoryRedis(),
        merchant_id="m",
        customer_ref="c",
        amount_paise=100,
        root_cause="bank_downtime",
        now=_day(),
    )
    assert d.status == "scheduled"
    assert d.action_type == "schedule_retry_backoff"


def test_quiet_hours_block():
    night = datetime(2026, 8, 27, 22, 0, tzinfo=IST)
    d = decide(
        redis=MemoryRedis(),
        merchant_id="m",
        customer_ref="c",
        amount_paise=100,
        root_cause="auth_failure",
        now=night,
    )
    assert d.status == "blocked"
    assert d.block_reason == "quiet_hours_ist_2100_0900"


def test_high_value_approval():
    d = decide(
        redis=MemoryRedis(),
        merchant_id="m",
        customer_ref="c",
        amount_paise=1_200_000,
        root_cause="auth_failure",
        now=_day(),
    )
    assert d.status == "pending_approval"


def test_fourth_attempt_blocked():
    r = MemoryRedis()
    for _ in range(3):
        r.incr("attempts:c:2026-08-27")
    d = decide(
        redis=r,
        merchant_id="m",
        customer_ref="c",
        amount_paise=100,
        root_cause="auth_failure",
        now=_day(),
    )
    assert d.block_reason == "max_3_attempts_per_customer_day"


def test_kill_switch():
    d = decide(
        redis=MemoryRedis(),
        merchant_id="m",
        customer_ref="c",
        amount_paise=100,
        root_cause="auth_failure",
        env_kill=True,
        now=_day(),
    )
    assert d.block_reason == "env_kill_switch"


def test_policy_http():
    from fastapi.testclient import TestClient
    from tests.conftest import load_service

    app = load_service("policy-service")
    c = TestClient(app.app)
    assert c.get("/health").json()["service"] == "policy-service"
    r = c.post(
        "/decide",
        json={
            "customer_ref": "u1",
            "amount_paise": 50000,
            "root_cause": "auth_failure",
            "env_kill": True,
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"
