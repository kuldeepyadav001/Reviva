import os

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient
from tests.conftest import load_service

ex = load_service("executor-service")
client = TestClient(ex.app)


def test_executor_health():
    assert client.get("/health").json()["service"] == "executor-service"


def test_blocked_still_audited():
    r = client.post(
        "/execute",
        json={
            "event_id": 1,
            "payment_id": "pay_x",
            "customer_ref": "c1",
            "amount_paise": 10000,
            "action_type": "none",
            "status": "blocked",
            "block_reason": "quiet_hours_ist_2100_0900",
            "decision_source": "gate",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"
    chain = client.get("/audit/1")
    assert chain.status_code == 200
    assert len(chain.json()) >= 1


def test_execute_link_and_metrics():
    r = client.post(
        "/execute",
        json={
            "event_id": 2,
            "payment_id": "pay_y",
            "customer_ref": "c2",
            "amount_paise": 50000,
            "action_type": "send_payment_link",
            "status": "execute",
            "decision_source": "rule:R_AUTH",
            "playbook": "fresh link",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "executed"
    assert r.json()["razorpay_ref"]
    m = client.get("/metrics").json()
    assert m["actions_taken"] >= 1
def test_clear_resets_ids():
    client.post("/ops/clear")
    r = client.post(
        "/execute",
        json={
            "event_id": 1,
            "payment_id": "pay_after_clear",
            "customer_ref": "c9",
            "amount_paise": 1000,
            "action_type": "none",
            "status": "blocked",
            "block_reason": "quiet_hours_ist_2100_0900",
        },
    )
    assert r.status_code == 200
    assert r.json()["action_id"] == 1
