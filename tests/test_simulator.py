import os

os.environ["INGEST_URL"] = "http://ingest.test"

from fastapi.testclient import TestClient
import httpx
import respx

from tests.conftest import load_service

sim = load_service("simulator-service")
client = TestClient(sim.app)


def test_simulator_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "simulator-service"


@respx.mock
def test_run_batch_posts_to_ingest():
    route = respx.post("http://ingest.test/internal/events").mock(
        return_value=httpx.Response(200, json={"ok": True, "event_id": 1})
    )
    r = client.post("/run-batch?n=4")
    assert r.status_code == 200
    body = r.json()
    assert body["batch"] == 4
    assert route.call_count == 4
    assert sum(body["by_ground_truth"].values()) == 4
