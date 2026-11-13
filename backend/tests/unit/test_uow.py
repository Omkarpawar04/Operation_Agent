import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.persistence.uow import SqlAlchemyUnitOfWork
from app.db.base import Base
from app.db.models import UserRow


def test_unit_of_work_commit_explicit_rollback_and_commit_failure() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    try:
        with factory() as db:
            with SqlAlchemyUnitOfWork(db):
                db.add(UserRow(auth_subject="uow-commit"))
        with factory() as db:
            assert db.scalar(select(UserRow.id).where(UserRow.auth_subject == "uow-commit"))

        with pytest.raises(RuntimeError, match="rollback sentinel"):
            with factory() as db:
                with SqlAlchemyUnitOfWork(db):
                    db.add(UserRow(auth_subject="uow-explicit-rollback"))
                    raise RuntimeError("rollback sentinel")
        with factory() as db:
            assert (
                db.scalar(select(UserRow.id).where(UserRow.auth_subject == "uow-explicit-rollback"))
                is None
            )

        with factory() as db:
            db.add(UserRow(auth_subject="uow-unique"))
            db.commit()
            with pytest.raises(IntegrityError):
                with SqlAlchemyUnitOfWork(db):
                    db.add(UserRow(auth_subject="uow-unique"))
            assert db.scalar(select(UserRow.id).where(UserRow.auth_subject == "uow-unique"))
    finally:
        engine.dispose()
