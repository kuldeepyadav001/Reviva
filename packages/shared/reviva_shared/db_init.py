import time

from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlmodel import SQLModel


def init_db(engine, attempts: int = 8) -> None:
    """create_all is not safe across two services starting together."""
    last = None
    for i in range(attempts):
        try:
            SQLModel.metadata.create_all(engine, checkfirst=True)
            return
        except (IntegrityError, OperationalError, ProgrammingError) as exc:
            last = exc
            msg = str(exc).lower()
            if "already exists" not in msg and "duplicate" not in msg and "unique" not in msg:
                raise
            time.sleep(0.25 * (i + 1))
    if last:
        raise last
