from uuid import uuid4

import pytest
from sqlalchemy import inspect, text

pytestmark = pytest.mark.postgres


def test_empty_schema_migrates_to_latest_revision(
    postgres_url, postgres_engine, upgrade_test_schema
) -> None:
    schema_name = f"migration_test_{uuid4().hex}"
    with postgres_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    schema_url = postgres_url.update_query_dict({"options": f"-csearch_path={schema_name}"})
    try:
        upgrade_test_schema(schema_url)
        with postgres_engine.connect() as connection:
            tables = set(inspect(connection).get_table_names(schema=schema_name))
            revision = connection.scalar(
                text(f'SELECT version_num FROM "{schema_name}".alembic_version')
            )
            question_columns = {
                column["name"]
                for column in inspect(connection).get_columns("questions", schema=schema_name)
            }
            bank_primary_key = inspect(connection).get_pk_constraint(
                "assessment_question_bank", schema=schema_name
            )["constrained_columns"]
            competency_columns = {
                column["name"]
                for column in inspect(connection).get_columns(
                    "assessment_competencies", schema=schema_name
                )
            }
            rubric_columns = {
                column["name"]
                for column in inspect(connection).get_columns(
                    "assessment_rubrics", schema=schema_name
                )
            }
            bank_columns = {
                column["name"]
                for column in inspect(connection).get_columns(
                    "assessment_question_bank", schema=schema_name
                )
            }
            bank_foreign_keys = inspect(connection).get_foreign_keys(
                "assessment_question_bank", schema=schema_name
            )
        expected = {
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
        assert expected <= tables
        assert revision == "0008_content_pack_metadata"
        assert "provenance_json" in question_columns
        assert bank_primary_key == ["question_id", "content_version"]
        assert {"stage_ids_json", "content_metadata_json"} <= competency_columns
        assert "content_metadata_json" in rubric_columns
        assert {
            "parent_question_id",
            "parent_content_version",
            "development_eligible",
            "content_metadata_json",
        } <= bank_columns
        assert any(item["name"] == "fk_qbank_parent_question" for item in bank_foreign_keys)
    finally:
        # Only the random schema created above is removed; public/test data is untouched.
        with postgres_engine.begin() as connection:
            present = connection.scalar(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name=:name"),
                {"name": schema_name},
            )
            if present == schema_name:
                connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
