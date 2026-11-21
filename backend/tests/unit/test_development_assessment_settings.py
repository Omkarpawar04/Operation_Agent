import pytest

from app.core.config import Settings


def test_question_bank_mode_and_draft_selection_are_explicit_development_opt_ins() -> None:
    defaults = Settings(_env_file=None, app_env="development")
    assert defaults.dev_assessment_content_mode == "fixture"
    assert defaults.dev_assessment_allow_draft is False

    enabled = Settings(
        _env_file=None,
        app_env="development",
        dev_assessment_content_mode="question_bank",
        dev_assessment_allow_draft=True,
    )
    assert enabled.dev_assessment_content_mode == "question_bank"
    assert enabled.dev_assessment_allow_draft is True


@pytest.mark.parametrize(
    "settings",
    [
        {"dev_assessment_content_mode": "question_bank"},
        {"dev_assessment_allow_draft": True},
    ],
)
def test_production_rejects_development_assessment_content(settings) -> None:
    with pytest.raises(ValueError, match="Development assessment content"):
        Settings(
            _env_file=None,
            app_env="production",
            llm_provider="gemini",
            gemini_api_key="test-only-not-used",
            cors_allowed_origins=["https://example.invalid"],
            trusted_hosts=["example.invalid"],
            transcript_retention_days=365,
            **settings,
        )


def test_other_environments_cannot_enable_development_assessment_mode() -> None:
    with pytest.raises(ValueError, match="development or test"):
        Settings(_env_file=None, app_env="staging", dev_assessment_content_mode="question_bank")
