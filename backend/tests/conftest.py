import os
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from alembic import command
from app.adapters.persistence.readiness import SqlAlchemyReadinessAdapter
from app.api.dependencies import get_db, get_readiness
from app.application.use_cases.readiness import CheckReadiness
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_POSTGRES_TABLES = {
    "alembic_version",
    "users",
    "courses",
    "enrollments",
    "course_content_revisions",
    "interview_sessions",
    "questions",
    "answers",
    "assessment_attempts",
    "evaluations",
    "assessment_results",
    "transcript_deletion_audit",
    "rate_limit_counters",
    "assessment_competencies",
    "assessment_rubrics",
    "assessment_question_bank",
}


def _validate_test_url(raw_url: str) -> URL:
    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg":
        pytest.fail("FINXL_TEST_POSTGRES_URL must use postgresql+psycopg")
    if url.database != "finxl_test":
        pytest.fail("PostgreSQL tests are restricted to the finxl_test database")
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("PostgreSQL tests may connect only to a local host")
    return url


def _upgrade_database(url: URL) -> None:
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    get_settings.cache_clear()
    try:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def _check_database(url: URL) -> None:
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    get_settings.cache_clear()
    try:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        command.check(config)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


@pytest.fixture
def client_and_factory() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    application = create_app()
    application.state.disable_workers = True
    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_settings] = lambda: Settings(app_env="test")
    application.dependency_overrides[get_readiness] = lambda: CheckReadiness(
        SqlAlchemyReadinessAdapter(engine)
    )
    with TestClient(application) as client:
        yield client, factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def dev_user_id() -> str:
    return str(uuid4())


@pytest.fixture(scope="session")
def postgres_url() -> URL:
    raw_url = os.environ.get("FINXL_TEST_POSTGRES_URL")
    if not raw_url:
        settings = Settings(_env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"))
        raw_url = settings.finxl_test_postgres_url
    if not raw_url:
        pytest.skip("FINXL_TEST_POSTGRES_URL is not configured")
    return _validate_test_url(raw_url)


@pytest.fixture(scope="session")
def postgres_engine(postgres_url: URL):
    engine = create_engine(postgres_url, pool_pre_ping=True)
    with engine.connect() as connection:
        database_name = connection.scalar(text("SELECT current_database()"))
        if database_name != "finxl_test":
            engine.dispose()
            pytest.fail("Connected database is not finxl_test")
        existing_tables = set(inspect(connection).get_table_names(schema="public"))
    if existing_tables and existing_tables != EXPECTED_POSTGRES_TABLES:
        engine.dispose()
        pytest.fail("finxl_test contains an unexpected schema; refusing to migrate or alter it")
    _upgrade_database(postgres_url)
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM public.alembic_version"))
    if revision != "0009_answer_skips":
        engine.dispose()
        pytest.fail("finxl_test is not at the expected latest Alembic revision")
    _check_database(postgres_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def postgres_factory(postgres_engine):
    return sessionmaker(bind=postgres_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def upgrade_test_schema():
    return _upgrade_database
