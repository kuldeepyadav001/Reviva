import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from reviva_shared.cors import add_cors

from reviva_shared.db_init import init_db
from reviva_shared.gates import bump_attempt, mark_link, MemoryRedis
from reviva_shared.health import service_health
from reviva_shared.models import AuditLog, Recovery, RecoveryAction, utcnow
from reviva_shared.razorpay_links import create_payment_link
from reviva_shared.recovery_sim import seeded_recover
from reviva_shared.wipe import wipe_ledger

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./executor.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
kwargs = {"connect_args": connect_args}
if DATABASE_URL.startswith("sqlite"):
    kwargs["poolclass"] = StaticPool
engine = create_engine(DATABASE_URL, **kwargs)
init_db(engine)

_redis = MemoryRedis()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    yield


app = FastAPI(title="reviva-executor", lifespan=lifespan)
add_cors(app)


class ExecuteIn(BaseModel):
    event_id: int
    payment_id: str
    customer_ref: str
    amount_paise: int
    action_type: str
    status: str
    block_reason: str | None = None
    decision_source: str = ""
    playbook: str = ""
    customer_email: str | None = None
    source: str = "sim"


def get_session():
    with Session(engine) as s:
        yield s


@app.get("/health")
def health():
    return service_health("executor-service")


@app.post("/execute")
def execute(body: ExecuteIn):
    with Session(engine) as session:
        action = RecoveryAction(
            event_id=body.event_id,
            action_type=body.action_type,
            status="blocked" if body.status == "blocked" else body.status,
            block_reason=body.block_reason,
            amount_paise=body.amount_paise,
            created_at=utcnow(),
        )
        extra_link: dict = {}
        if body.status == "execute" and body.action_type in (
            "send_payment_link",
            "send_single_reminder_link",
        ):
            action.status = "executed"
            link = create_payment_link(
                body.amount_paise,
                body.payment_id,
                body.customer_email,
                f"Reviva recovery for {body.payment_id}",
            )
            action.razorpay_ref = link.get("id")
            extra_link = link
            mark_link(_redis, body.customer_ref, body.amount_paise)
            bump_attempt(_redis, body.customer_ref)
        elif body.status == "scheduled":
            action.status = "scheduled"
            bump_attempt(_redis, body.customer_ref)
        session.add(action)
        session.commit()
        session.refresh(action)

        audit = AuditLog(
            event_id=body.event_id,
            action_id=action.id,
            action=body.action_type,
            decision_source=body.decision_source,
            reason=body.block_reason or body.playbook,
            amount_paise=body.amount_paise,
            outcome=action.status,
            extra={"playbook": body.playbook, "razorpay_ref": action.razorpay_ref, "link": extra_link},
            created_at=utcnow(),
        )
        session.add(audit)
        recovered = False
        rec_amt = 0
        if action.status in ("executed", "scheduled"):
            recovered = seeded_recover(body.payment_id, body.action_type)
            rec_amt = body.amount_paise if recovered else 0
            session.add(
                Recovery(
                    event_id=body.event_id,
                    action_id=action.id,
                    amount_paise=rec_amt,
                    recovered=recovered,
                    mode="sim",
                    created_at=utcnow(),
                )
            )
            session.add(
                AuditLog(
                    event_id=body.event_id,
                    action_id=action.id,
                    action="measure_recovery",
                    decision_source="simulator",
                    reason="seeded RNG; not live conversion",
                    amount_paise=rec_amt,
                    outcome="recovered" if recovered else "not_recovered",
                    created_at=utcnow(),
                )
            )
        session.commit()
        return {
            "action_id": action.id,
            "status": action.status,
            "razorpay_ref": action.razorpay_ref,
            "recovered_sim": recovered,
            "amount_recovered_paise": rec_amt,
        }


@app.get("/metrics")
def metrics():
    with Session(engine) as session:
        actions = session.exec(select(RecoveryAction)).all()
        recs = session.exec(select(Recovery)).all()
        recovered = sum(x.amount_paise for x in recs if x.recovered)
        return {
            "actions_taken": sum(1 for a in actions if a.status in ("executed", "scheduled")),
            "actions_blocked": sum(1 for a in actions if a.status == "blocked"),
            "pending_approval": sum(1 for a in actions if a.status == "pending_approval"),
            "rupees_recovered_sim": recovered / 100,
            "recovery_rate": (sum(1 for x in recs if x.recovered) / len(recs)) if recs else 0,
            "note": "₹ recovered is seeded simulation unless tagged live.",
        }


@app.get("/audit/{event_id}")
def audit_chain(event_id: int):
    with Session(engine) as session:
        logs = session.exec(select(AuditLog).where(AuditLog.event_id == event_id)).all()
        if not logs:
            raise HTTPException(404, "no audit")
        return logs


@app.get("/actions")
def actions():
    with Session(engine) as session:
        return session.exec(
            select(RecoveryAction).order_by(RecoveryAction.id.desc()).limit(250)
        ).all()


@app.post("/ops/clear")
def clear_ops():
    with Session(engine) as session:
        wipe_ledger(session, engine)
    return {"ok": True, "cleared": "all", "ids_reset": True}
