import json
import re
from typing import Any

import httpx

from reviva_shared.rules import RuleHit

ALLOWED = {
    "insufficient_funds",
    "bank_downtime",
    "auth_failure",
    "abandonment",
    "unknown",
}

RETRY_CLASS = {
    "insufficient_funds": "hard",
    "bank_downtime": "soft",
    "auth_failure": "session",
    "abandonment": "abandon",
    "unknown": "review",
}

SYSTEM = (
    "Classify Indian payment-failure payloads. Return ONLY JSON "
    '{"root_cause":"...","confidence":0-1,"reasoning":"short"}. '
    "root_cause one of: insufficient_funds, bank_downtime, auth_failure, abandonment, unknown. "
    "If unsure use unknown and confidence below 0.6."
)


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def parse_llm_payload(content: str) -> RuleHit:
    data = _extract_json(content)
    if not data:
        return RuleHit("unknown", "review", "llm_fallback", "Invalid JSON from LLM.", 0.0)
    cause = str(data.get("root_cause", "unknown"))
    if cause not in ALLOWED:
        cause = "unknown"
    try:
        conf = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    reasoning = str(data.get("reasoning", ""))[:500]
    if conf < 0.6:
        return RuleHit(
            "unknown",
            "review",
            "llm_low_confidence",
            f"confidence={conf:.2f} < 0.6. {reasoning}",
            conf,
        )
    return RuleHit(cause, RETRY_CLASS[cause], "llm", reasoning, conf)


async def classify_llm(payload: dict, base_url: str, model: str) -> RuleHit:
    safe = {
        "error_code": payload.get("error_code"),
        "error_reason": payload.get("error_reason"),
        "error_description": payload.get("error_description"),
        "event_type": payload.get("event_type"),
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(
                f"{base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": json.dumps(safe)},
                    ],
                },
            )
            res.raise_for_status()
            content = res.json().get("message", {}).get("content", "")
    except Exception as exc:
        return RuleHit("unknown", "review", "llm_error", f"Ollama error: {exc!s}"[:400], 0.0)
    return parse_llm_payload(content)
