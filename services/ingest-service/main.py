import json
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sqlmodel import Session, SQLModel, create_engine
from reviva_shared.db_init import init_db
from reviva_shared.dedup import DedupStore
from reviva_shared.health import service_health
from reviva_shared.hmac_util import verify_razorpay_signature
from reviva_shared.models import PaymentEvent, utcnow
from reviva_shared.settings import settings


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ingest.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine_kwargs = {"connect_args": connect_args}
if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy.pool import StaticPool

    engine_kwargs["poolclass"] = StaticPool
engine = create_engine(DATABASE_URL, **engine_kwargs)
init_db(engine)


class MemoryRedis:
    def __init__(self):
        self._d: dict[str, str] = {}

    def set(self, key, val, nx=False, ex=None):
        if nx and key in self._d:
            return False
        self._d[key] = val
        return True


def _redis():
    url = os.getenv("REDIS_URL", "")
    if url.startswith("redis://"):
        try:
            import redis

            return redis.from_url(url, decode_responses=True)
        except Exception:
            return MemoryRedis()
    return MemoryRedis()


dedup = DedupStore(_redis())
PIPELINE_ENABLED = os.getenv("PIPELINE_ENABLED", "true").lower() != "false"
DIAGNOSIS_URL = os.getenv("DIAGNOSIS_URL", "http://diagnosis-service:8000")
POLICY_URL = os.getenv("POLICY_URL", "http://policy-service:8000")
EXECUTOR_URL = os.getenv("EXECUTOR_URL", "http://executor-service:8000")


def run_pipeline(ev: PaymentEvent) -> dict:
    if not PIPELINE_ENABLED or ev.event_type != "payment.failed":
        return {}
    with httpx.Client(timeout=60.0) as client:
        d = client.post(
            f"{DIAGNOSIS_URL}/diagnose",
            json={
                "error_reason": ev.error_reason,
                "error_code": ev.error_code,
                "error_description": ev.error_description,
                "event_type": ev.event_type,
            },
        )
        d.raise_for_status()
        diagnosis = d.json()
        p = client.post(
            f"{POLICY_URL}/decide",
            json={
                "merchant_id": ev.merchant_id,
                "customer_ref": ev.customer_ref,
                "amount_paise": ev.amount_paise,
                "root_cause": diagnosis["root_cause"],
            },
        )
        p.raise_for_status()
        decision = p.json()
        e = client.post(
            f"{EXECUTOR_URL}/execute",
            json={
                "event_id": ev.id,
                "payment_id": ev.razorpay_payment_id,
                "customer_ref": ev.customer_ref,
                "amount_paise": ev.amount_paise,
                "action_type": decision["action_type"],
                "status": decision["status"],
                "block_reason": decision.get("block_reason"),
                "decision_source": diagnosis.get("decision_source", ""),
                "playbook": decision.get("playbook", ""),
                "customer_email": ev.customer_email,
                "source": ev.source,
            },
        )
        e.raise_for_status()
        return {"diagnosis": diagnosis, "decision": decision, "execution": e.json()}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    yield


from reviva_shared.cors import add_cors

app = FastAPI(title="reviva-ingest", lifespan=lifespan)
add_cors(app)


def get_session():
    with Session(engine) as session:
        yield session


@app.get("/health")
def health():
    return service_health("ingest-service")


@app.post("/ops/clear")
def clear_events(session: Session = Depends(get_session)):
    from reviva_shared.wipe import wipe_ledger

    wipe_ledger(session, engine)
    client = _redis()
    if hasattr(client, "flushdb"):
        try:
            client.flushdb()
        except Exception:
            pass
    return {"ok": True, "cleared": "events", "ids_reset": True}


def _customer_ref(entity: dict) -> str:
    return entity.get("email") or entity.get("contact") or entity.get("id") or "anon"


def persist_failed_payload(session: Session, payload: dict, source: str) -> PaymentEvent:
    entity = payload.get("payload", {}).get("payment", {}).get("entity", payload.get("entity", {}))
    err = entity.get("error") or {}
    ev = PaymentEvent(
        merchant_id=settings.merchant_id,
        razorpay_payment_id=entity.get("id") or payload.get("payment_id") or "unknown",
        razorpay_order_id=entity.get("order_id"),
        event_type=payload.get("event") or "payment.failed",
        amount_paise=int(entity.get("amount") or payload.get("amount_paise") or 0),
        currency=entity.get("currency") or "INR",
        customer_ref=_customer_ref(entity) if entity else payload.get("customer_ref") or "anon",
        customer_email=entity.get("email") or payload.get("customer_email"),
        error_code=err.get("code") or entity.get("error_code") or payload.get("error_code"),
        error_reason=err.get("reason") or entity.get("error_reason") or payload.get("error_reason"),
        error_description=err.get("description") or entity.get("error_description") or payload.get("error_description"),
        error_source=err.get("source"),
        error_step=err.get("step"),
        payload=payload,
        source=source,
        created_at=utcnow(),
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


@app.post("/webhooks/razorpay")
async def webhook(
    request: Request,
    session: Session = Depends(get_session),
    x_razorpay_signature: str | None = Header(default=None),
):
    body = await request.body()
    secret = settings.razorpay_webhook_secret
    if secret and secret != "replace_me":
        if not verify_razorpay_signature(body, x_razorpay_signature, secret):
            raise HTTPException(400, "invalid webhook signature")
    payload = json.loads(body.decode() or "{}")
    event_type = payload.get("event") or ""
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = entity.get("id") or "unknown"
    if not dedup.claim(payment_id, event_type):
        return {"ok": True, "deduped": True}
    if event_type not in ("payment.failed", "payment.captured"):
        return {"ok": True, "ignored": event_type}
    ev = persist_failed_payload(session, payload, source="webhook")
    pipe = {}
    if ev.event_type == "payment.failed":
        try:
            pipe = run_pipeline(ev)
        except Exception as exc:
            pipe = {"pipeline_error": str(exc)[:300]}
    return {"ok": True, "event_id": ev.id, "deduped": False, "pipeline": pipe}


@app.post("/internal/events")
def internal_event(payload: dict, session: Session = Depends(get_session)):
    pid = payload.get("razorpay_payment_id") or payload.get("payment_id") or "sim_unknown"
    et = payload.get("event") or "payment.failed"
    if not dedup.claim(pid, et):
        return {"ok": True, "deduped": True}
    wrapped = {
        "event": et,
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "order_id": payload.get("razorpay_order_id"),
                    "amount": payload.get("amount_paise", 0),
                    "email": payload.get("customer_email"),
                    "error": {
                        "code": payload.get("error_code"),
                        "reason": payload.get("error_reason"),
                        "description": payload.get("error_description"),
                    },
                }
            }
        },
        **payload,
    }
    ev = persist_failed_payload(session, wrapped, source=payload.get("source") or "sim")
    pipe = {}
    try:
        pipe = run_pipeline(ev)
    except Exception as exc:
        pipe = {"pipeline_error": str(exc)[:300]}
    return {"ok": True, "event_id": ev.id, "pipeline": pipe}
