from sqlalchemy import text
from sqlmodel import Session, select

from reviva_shared.models import (
    AuditLog,
    Diagnosis,
    PaymentEvent,
    Recovery,
    RecoveryAction,
)

_PG = "auditlog, recovery, recoveryaction, diagnosis, paymentevent"


def wipe_ledger(session: Session, engine) -> None:
    """Delete practice rows and reset IDs to 1."""
    dialect = engine.dialect.name
    if dialect == "postgresql":
        session.execute(text(f"TRUNCATE TABLE {_PG} RESTART IDENTITY CASCADE"))
        session.commit()
        return
    for model in (AuditLog, Recovery, RecoveryAction, Diagnosis, PaymentEvent):
        for row in session.exec(select(model)).all():
            session.delete(row)
    session.commit()
    try:
        session.execute(text("DELETE FROM sqlite_sequence"))
        session.commit()
    except Exception:
        session.rollback()
