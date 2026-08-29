from sqlalchemy import text
from sqlmodel import SQLModel, Session, select

from reviva_shared.models import (
    AuditLog,
    Diagnosis,
    PaymentEvent,
    Recovery,
    RecoveryAction,
)

_KEEP = {"merchantstate"}


def _table_names() -> list[str]:
    return [t.name for t in SQLModel.metadata.sorted_tables if t.name.lower() not in _KEEP]


def wipe_ledger(session: Session, engine) -> dict:
    """Delete practice rows and reset IDs so the next row is #1."""
    names = _table_names()
    dialect = engine.dialect.name
    if dialect == "postgresql":
        quoted = ", ".join(f'"{n}"' for n in names)
        session.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
        session.commit()
        return {"dialect": dialect, "tables": names, "ids_reset": True}
    for model in (AuditLog, Recovery, RecoveryAction, Diagnosis, PaymentEvent):
        for row in session.exec(select(model)).all():
            session.delete(row)
    session.commit()
    try:
        session.execute(text("DELETE FROM sqlite_sequence"))
        session.commit()
    except Exception:
        session.rollback()
    return {"dialect": dialect, "tables": names, "ids_reset": True}
