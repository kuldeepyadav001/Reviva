import os

from fastapi import FastAPI
from pydantic import BaseModel
from reviva_shared.cors import add_cors
from reviva_shared.gates import MemoryRedis
from reviva_shared.health import service_health
from reviva_shared.policy import decide

app = FastAPI(title="reviva-policy")
add_cors(app)

_redis = MemoryRedis()
try:
    url = os.getenv("REDIS_URL", "")
    if url.startswith("redis://"):
        import redis as redislib

        _redis = redislib.from_url(url, decode_responses=True)
except Exception:
    _redis = MemoryRedis()


class DecideIn(BaseModel):
    merchant_id: str = "merch_local_1"
    customer_ref: str
    amount_paise: int
    root_cause: str
    env_kill: bool = False


@app.get("/health")
def health():
    return service_health("policy-service")


@app.post("/decide")
def decide_ep(body: DecideIn):
    d = decide(
        redis=_redis,
        merchant_id=body.merchant_id,
        customer_ref=body.customer_ref,
        amount_paise=body.amount_paise,
        root_cause=body.root_cause,
        env_kill=body.env_kill,
    )
    return {
        "action_type": d.action_type,
        "status": d.status,
        "block_reason": d.block_reason,
        "playbook": d.playbook,
    }


@app.get("/ops/kill-switch")
def kill_get(merchant_id: str = "merch_local_1"):
    on = _redis.get(f"kill:{merchant_id}") == "1"
    return {"kill_switch": on, "human": "Agent is frozen. No customer will be contacted." if on else "Agent is live."}


@app.post("/ops/kill-switch")
def kill(on: bool = True, merchant_id: str = "merch_local_1"):
    _redis.set(f"kill:{merchant_id}", "1" if on else "0")
    return {"kill_switch": on}
