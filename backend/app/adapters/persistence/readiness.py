from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import Unavailable
from app.ports.readiness import ReadinessPort


class SqlAlchemyReadinessAdapter(ReadinessPort):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def check(self) -> None:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise Unavailable("Database is unavailable") from exc
