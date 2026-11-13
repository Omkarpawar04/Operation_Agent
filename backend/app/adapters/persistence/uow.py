from sqlalchemy.orm import Session

from app.ports.repositories import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Explicit transaction boundary; never keep this open across provider calls."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session.begin()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            try:
                self.commit()
            except Exception:
                self.rollback()
                raise

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
