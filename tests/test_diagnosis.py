import httpx
import respx
from fastapi.testclient import TestClient

from tests.conftest import load_service

diag = load_service("diagnosis-service")
client = TestClient(diag.app)


def test_diagnosis_health():
    r = client.get("/health")
    assert r.json()["service"] == "diagnosis-service"


def test_rules_path_does_not_call_ollama():
    with respx.mock:
        route = respx.post("http://ollama:11434/api/chat").mock(
            return_value=httpx.Response(500)
        )
        r = client.post("/diagnose", json={"error_reason": "insufficient_funds"})
        assert r.status_code == 200
        body = r.json()
        assert body["used_llm"] is False
        assert body["root_cause"] == "insufficient_funds"
        assert body["decision_source"].startswith("rule:")
        assert route.call_count == 0


def test_unknown_uses_llm(monkeypatch):
    monkeypatch.setattr(diag, "OLLAMA_BASE_URL", "http://ollama.test")
    with respx.mock:
        respx.post("http://ollama.test/api/chat").mock(
            return_value=httpx.Response(
                200,
                json={
                    "message": {
                        "content": '{"root_cause":"abandonment","confidence":0.85,"reasoning":"dropoff"}'
                    }
                },
            )
        )
        r = client.post("/diagnose", json={"error_description": "unclear ZX-99"})
        assert r.status_code == 200
        body = r.json()
        assert body["used_llm"] is True
        assert body["root_cause"] == "abandonment"


def test_llm_down_manual_review(monkeypatch):
    monkeypatch.setattr(diag, "OLLAMA_BASE_URL", "http://ollama.down")
    with respx.mock:
        respx.post("http://ollama.down/api/chat").mock(side_effect=httpx.ConnectError("down"))
        r = client.post("/diagnose", json={"error_description": "???"})
        assert r.json()["root_cause"] == "manual_review"
