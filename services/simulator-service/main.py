import os

import httpx
from fastapi import FastAPI, HTTPException
from reviva_shared.batch_spec import build_specs
from reviva_shared.health import service_health

app = FastAPI(title="reviva-simulator")

INGEST_URL = os.getenv("INGEST_URL", "http://ingest-service:8000")


@app.get("/health")
def health():
    return service_health("simulator-service")


def post_event(client: httpx.Client, spec: dict) -> dict:
    payload = {
        "event": "payment.failed",
        "source": "sim",
        "razorpay_payment_id": spec["razorpay_payment_id"],
        "amount_paise": spec["amount_paise"],
        "customer_email": spec["customer_email"],
        "customer_ref": spec["customer_email"],
        "error_code": spec["error_code"],
        "error_reason": spec["error_reason"],
        "error_description": spec["error_description"],
        "ground_truth": spec["ground_truth"],
    }
    r = client.post(f"{INGEST_URL}/internal/events", json=payload, timeout=10.0)
    r.raise_for_status()
    body = r.json()
    body["ground_truth"] = spec["ground_truth"]
    return body


@app.post("/run-batch")
@app.post("/run-batch/")
@app.post("/api/simulator/run-batch")
def run_batch(n: int = 100):
    if n < 1 or n > 500:
        raise HTTPException(400, "n must be 1..500")
    specs = build_specs(n)
    results = []
    with httpx.Client() as client:
        for spec in specs:
            results.append(post_event(client, spec))
    counts: dict[str, int] = {}
    for s in specs:
        counts[s["ground_truth"]] = counts.get(s["ground_truth"], 0) + 1
    return {
        "ok": True,
        "batch": len(results),
        "by_ground_truth": counts,
        "note": "Labels are evaluation harness ground truth, not live Razorpay.",
        "events": results,
    }
