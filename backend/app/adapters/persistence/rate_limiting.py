from datetime import datetime, timedelta
from hashlib import sha256

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models import RateLimitCounterRow
from app.ports.rate_limiting import RateLimitPort


class SqlAlchemyRateLimitStore(RateLimitPort):
    """Shared fixed-window counter; atomic upsert works across app instances."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def consume(self, scope: str, now: datetime, window_seconds: int) -> int:
        epoch = int(now.timestamp())
        window_start = datetime.fromtimestamp(epoch - epoch % window_seconds, tz=now.tzinfo)
        expires_at = window_start + timedelta(seconds=window_seconds * 2)
        values = {
            "scope": scope,
            "window_started_at": window_start,
            "hits": 1,
            "expires_at": expires_at,
        }
        if self._session.bind is not None and self._session.bind.dialect.name == "postgresql":
            statement = (
                pg_insert(RateLimitCounterRow)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[RateLimitCounterRow.scope],
                    set_={"hits": RateLimitCounterRow.hits + 1},
                )
                .returning(RateLimitCounterRow.hits)
            )
        else:
            statement = (
                sqlite_insert(RateLimitCounterRow)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[RateLimitCounterRow.scope],
                    set_={"hits": RateLimitCounterRow.hits + 1},
                )
                .returning(RateLimitCounterRow.hits)
            )
        hits = self._session.scalar(statement)
        self._session.execute(
            delete(RateLimitCounterRow).where(RateLimitCounterRow.expires_at < now)
        )
        self._session.commit()
        return int(hits or 1)


def rate_limit_scope(category: str, client_address: str, window_started_at: datetime) -> str:
    material = f"{category}:{client_address}:{window_started_at.isoformat()}".encode()
    return sha256(material).hexdigest()
