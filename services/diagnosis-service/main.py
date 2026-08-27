import os

from fastapi import FastAPI
from pydantic import BaseModel
from reviva_shared.health import service_health
from reviva_shared.llm_classify import classify_llm
from reviva_shared.rules import classify_rules

app = FastAPI(title="reviva-diagnosis")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")


class DiagnoseIn(BaseModel):
    error_reason: str | None = None
    error_code: str | None = None
    error_description: str | None = None
    event_type: str | None = "payment.failed"


@app.get("/health")
def health():
    return service_health("diagnosis-service")


@app.post("/diagnose")
async def diagnose(body: DiagnoseIn):
    hit = classify_rules(body.error_reason, body.error_code, body.error_description, body.event_type)
    used_llm = False
    if hit is None:
        used_llm = True
        hit = await classify_llm(body.model_dump(), OLLAMA_BASE_URL, OLLAMA_MODEL)
    root = hit.root_cause
    source = f"rule:{hit.rule_id}" if not used_llm else hit.rule_id
    if used_llm and (hit.confidence < 0.6 or root == "unknown"):
        root = "manual_review"
    return {
        "root_cause": root,
        "retry_class": hit.retry_class,
        "confidence": hit.confidence,
        "decision_source": source,
        "reasoning": hit.reasoning,
        "used_llm": used_llm,
    }
