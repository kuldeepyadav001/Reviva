import json
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["REDIS_URL"] = ""
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "whsec_test"

from fastapi.testclient import TestClient
from reviva_shared.hmac_util import razorpay_webhook_signature

# import after env
from importlib import import_module
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "ingest-service"))
import main as ingest  # noqa: E402

client = TestClient(ingest.app)

FAILED = {
    "event": "payment.failed",
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_test_1",
                "amount": 50000,
                "email": "a@b.test",
                "error": {"reason": "insufficient_funds", "description": "nsf"},
            }
        }
    },
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "ingest-service"


def test_webhook_hmac_and_dedup():
    body = json.dumps(FAILED).encode()
    sig = razorpay_webhook_signature(body, "whsec_test")
    r1 = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    assert r1.status_code == 200
    assert r1.json()["deduped"] is False
    r2 = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    assert r2.status_code == 200
    assert r2.json()["deduped"] is True


def test_bad_hmac_rejected():
    body = json.dumps(FAILED).encode()
    r = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": "deadbeef"})
    assert r.status_code == 400
