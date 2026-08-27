"""Happy-path HTTP chain: diagnose → decide → execute (no live network)."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("PIPELINE_ENABLED", "false")

from fastapi.testclient import TestClient
from tests.conftest import load_service

diag = TestClient(load_service("diagnosis-service").app)
pol = TestClient(load_service("policy-service").app)
exe = TestClient(load_service("executor-service").app)


def test_end_to_end_known_auth_failure():
    d = diag.post("/diagnose", json={"error_reason": "authentication_failed"}).json()
    assert d["used_llm"] is False
    assert d["root_cause"] == "auth_failure"
    p = pol.post(
        "/decide",
        json={
            "customer_ref": "chain-user",
            "amount_paise": 19900,
            "root_cause": d["root_cause"],
            "env_kill": True,
        },
    ).json()
    assert p["status"] == "blocked"
    e = exe.post(
        "/execute",
        json={
            "event_id": 99,
            "payment_id": "pay_chain",
            "customer_ref": "chain-user",
            "amount_paise": 19900,
            "action_type": p["action_type"],
            "status": p["status"],
            "block_reason": p["block_reason"],
            "decision_source": d["decision_source"],
        },
    )
    assert e.status_code == 200
    assert e.json()["status"] == "blocked"
    assert exe.get("/audit/99").status_code == 200
