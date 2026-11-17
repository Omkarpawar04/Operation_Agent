import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import Conflict, NotFound, Unavailable
from app.db.models import (
    AnswerRow,
    AssessmentAttemptRow,
    AssessmentResultRow,
    AssessmentRubricRow,
    CourseContentRevisionRow,
    EvaluationRow,
    InterviewSessionRow,
    QuestionRow,
    UserRow,
)
from app.domain.assessments.content import QuestionProvenance
from app.domain.assessments.models import AssessmentResult, EvaluationEvidence
from app.domain.interviews.decision import InterviewAction
from app.domain.interviews.models import (
    Answer,
    InterviewSession,
    InterviewStage,
    InterviewState,
    Question,
    QuestionKind,
    transition,
)
from app.ports.answer_workflow import (
    AnswerCommand,
    AnswerCompletion,
    AnswerReplay,
    AnswerReservation,
    AnswerWorkflowPort,
)

logger = logging.getLogger(__name__)


class SqlAlchemyAnswerWorkflowAdapter(AnswerWorkflowPort):
    """Implements short, optimistic transactions around external provider work."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def reserve(
        self, command: AnswerCommand, lease_seconds: int
    ) -> AnswerReservation | AnswerReplay:
        row = self._session.scalar(
            select(InterviewSessionRow).where(
                InterviewSessionRow.id == command.session_id,
                InterviewSessionRow.student_id == command.student_id,
            )
        )
        if row is None:
            raise NotFound("Interview not found")
        duplicate = self._session.scalar(
            select(AnswerRow).where(
                AnswerRow.session_id == row.id,
                AnswerRow.idempotency_key == command.idempotency_key,
            )
        )
        if duplicate is not None:
            if (
                duplicate.question_id != command.question_id
                or duplicate.transcript != command.text
                or duplicate.is_skipped != command.is_skip
            ):
                raise Conflict("Idempotency key reused with a different answer")
            active = (
                self._session.get(QuestionRow, row.active_question_id)
                if row.active_question_id
                else None
            )
            return AnswerReplay(row.state, row.version, active.text if active else None)

        if row.state == InterviewState.ANSWER_PROCESSING.value:
            started = row.processing_started_at
            if started is not None and started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            if started is not None and datetime.now(UTC) - started < timedelta(
                seconds=lease_seconds
            ):
                raise Conflict("Answer analysis is still processing")
            question = (
                self._session.get(QuestionRow, row.active_question_id)
                if row.active_question_id
                else None
            )
            row.state = (
                InterviewState.AWAITING_ANSWER.value
                if question is None or question.kind == QuestionKind.BASE.value
                else InterviewState.AWAITING_FOLLOW_UP_ANSWER.value
            )
            row.version += 1
            row.processing_started_at = None
            self._session.commit()
            logger.warning(
                "answer_processing_lease_expired session_id=%s question_id=%s version=%s",
                row.id,
                row.active_question_id,
                row.version,
            )
            raise Conflict("Processing reservation expired; reload the interview and retry")

        if row.version != command.expected_version:
            raise Conflict("stale_version")
        if row.state not in {
            InterviewState.AWAITING_ANSWER.value,
            InterviewState.AWAITING_FOLLOW_UP_ANSWER.value,
        }:
            raise Conflict("Interview is not accepting an answer")
        if row.active_question_id != command.question_id:
            raise Conflict("Question is not active")
        active = self._session.get(QuestionRow, command.question_id)
        attempt = self._session.scalar(
            select(AssessmentAttemptRow).where(AssessmentAttemptRow.session_id == row.id)
        )
        if active is None or attempt is None:
            raise Conflict("Interview is not ready")
        metadata: dict[str, object] = {}
        if row.content_revision_id:
            revision = self._session.get(CourseContentRevisionRow, row.content_revision_id)
            if revision is None:
                raise Conflict("Pinned course content is unavailable")
            metadata = dict(revision.metadata_json)
        previous_state = row.state
        prior_answers = tuple(
            self._session.scalars(
                select(AnswerRow.transcript)
                .where(AnswerRow.session_id == row.id, AnswerRow.is_skipped.is_(False))
                .order_by(AnswerRow.created_at.desc())
                .limit(8)
            ).all()
        )
        prior_questions = tuple(
            self._session.scalars(
                select(QuestionRow.text)
                .where(QuestionRow.session_id == row.id)
                .order_by(QuestionRow.sequence.desc())
                .limit(20)
            ).all()
        )
        all_questions = self._session.scalars(
            select(QuestionRow)
            .where(QuestionRow.session_id == row.id)
            .order_by(QuestionRow.sequence)
        ).all()
        root_question = active
        while root_question.parent_question_id is not None:
            parent = self._session.get(QuestionRow, root_question.parent_question_id)
            if parent is None:
                raise Conflict("Question history is incomplete")
            root_question = parent
        previous_followups = tuple(
            item.text for item in all_questions if item.kind in ("follow_up", "clarification")
        )
        follow_up_index = int(
            self._session.scalar(
                select(func.count(QuestionRow.id)).where(
                    QuestionRow.session_id == row.id,
                    QuestionRow.kind.in_(("follow_up", "clarification")),
                )
            )
            or 0
        )
        previous_evidence = self._previous_evidence(row.id)
        aggregate = self._aggregate(row)
        try:
            transition(aggregate, InterviewState.ANSWER_PROCESSING, command.expected_version)
            row.state = aggregate.state.value
            row.version = aggregate.version
            row.processing_started_at = datetime.now(UTC)
            processing_version = row.version
            self._session.commit()
        except StaleDataError as exc:
            self._session.rollback()
            raise Conflict("stale_version") from exc
        logger.info(
            "answer_reservation_committed session_id=%s question_id=%s expected_version=%s "
            "processing_version=%s stage=%s",
            row.id,
            active.id,
            command.expected_version,
            processing_version,
            row.stage,
        )

        domain_question = Question(
            session_id=row.id,
            text=active.text,
            sequence=active.sequence,
            kind=QuestionKind(active.kind),
            id=active.id,
            parent_question_id=active.parent_question_id,
            provenance=QuestionProvenance.from_json(active.provenance_json),
        )
        return AnswerReservation(
            session=aggregate,
            previous_state=previous_state,
            processing_version=processing_version,
            lease_seconds=lease_seconds,
            active_question=domain_question,
            attempt_id=attempt.id,
            course_metadata=metadata,
            prior_answers=prior_answers,
            previous_questions=prior_questions,
            previous_evidence=previous_evidence,
            follow_up_index=follow_up_index,
            original_question_text=root_question.text,
            previous_follow_up_questions=previous_followups,
            root_question_id=root_question.id,
        )

    def release(self, reservation: AnswerReservation) -> None:
        # Clear a failed or incomplete finalization transaction before releasing the lease.
        self._session.rollback()
        self._session.scalar(
            select(UserRow.id).where(UserRow.id == reservation.session.student_id).with_for_update()
        )
        row = self._session.get(InterviewSessionRow, reservation.session.id)
        if (
            row is None
            or row.version != reservation.processing_version
            or row.state != InterviewState.ANSWER_PROCESSING.value
        ):
            self._session.rollback()
            return
        row.state = reservation.previous_state
        row.version += 1
        row.processing_started_at = None
        try:
            self._session.commit()
        except StaleDataError as exc:
            self._session.rollback()
            raise Conflict("stale_version") from exc
        logger.info(
            "answer_reservation_released session_id=%s question_id=%s processing_version=%s",
            row.id,
            reservation.active_question.id,
            reservation.processing_version,
        )

    def complete(
        self,
        command: AnswerCommand,
        reservation: AnswerReservation,
        evidence: tuple[EvaluationEvidence, ...],
        rubric_version: str,
        action: InterviewAction,
        next_question_text: str | None,
        result: AssessmentResult | None,
        next_question_provenance: QuestionProvenance | None = None,
    ) -> AnswerCompletion:
        try:
            return self._persist_completion(
                command,
                reservation,
                evidence,
                rubric_version,
                action,
                next_question_text,
                result,
                next_question_provenance,
            )
        except StaleDataError as exc:
            self._session.rollback()
            raise Conflict("stale_version") from exc
        except IntegrityError as exc:
            self._session.rollback()
            raise Conflict("Answer command conflicts with an existing result") from exc
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise Unavailable("Answer persistence is temporarily unavailable") from exc

    def _persist_completion(
        self,
        command: AnswerCommand,
        reservation: AnswerReservation,
        evidence: tuple[EvaluationEvidence, ...],
        rubric_version: str,
        action: InterviewAction,
        next_question_text: str | None,
        result: AssessmentResult | None,
        next_question_provenance: QuestionProvenance | None,
    ) -> AnswerCompletion:
        self._session.scalar(
            select(UserRow.id).where(UserRow.id == reservation.session.student_id).with_for_update()
        )
        row = self._session.get(InterviewSessionRow, reservation.session.id)
        if (
            row is None
            or row.version != reservation.processing_version
            or row.state != InterviewState.ANSWER_PROCESSING.value
            or row.active_question_id != command.question_id
        ):
            self._session.rollback()
            raise Conflict("stale_version")
        started = row.processing_started_at
        if started is not None and started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        if started is None or datetime.now(UTC) - started >= timedelta(
            seconds=reservation.lease_seconds
        ):
            row.state = reservation.previous_state
            row.version += 1
            row.processing_started_at = None
            self._session.commit()
            logger.warning(
                "late_answer_provider_response_rejected session_id=%s question_id=%s "
                "reservation_version=%s current_version=%s",
                row.id,
                command.question_id,
                reservation.processing_version,
                row.version,
            )
            raise Conflict("Processing reservation expired; reload the interview and retry")
        if (
            action
            in {
                InterviewAction.FOLLOW_UP,
                InterviewAction.CLARIFICATION,
                InterviewAction.NEXT_QUESTION,
            }
            and not next_question_text
        ):
            raise Conflict("Interview transition requires a generated question")

        answer_id = uuid4()
        if not command.is_skip:
            Answer(
                session_id=row.id,
                question_id=command.question_id,
                text=command.text,
                idempotency_key=command.idempotency_key,
            )
        answer_row = AnswerRow(
            id=answer_id,
            session_id=row.id,
            question_id=command.question_id,
            transcript=command.text,
            idempotency_key=command.idempotency_key,
            is_skipped=command.is_skip,
        )
        self._session.add(answer_row)
        self._session.flush()
        self._session.add(
            EvaluationRow(
                answer_id=answer_id,
                rubric_version=rubric_version,
                evidence_json=[self._evidence_record(item) for item in evidence],
            )
        )
        question_text: str | None = None
        if action in {
            InterviewAction.FOLLOW_UP,
            InterviewAction.CLARIFICATION,
            InterviewAction.NEXT_QUESTION,
        }:
            sequence = (
                int(
                    self._session.scalar(
                        select(func.max(QuestionRow.sequence)).where(
                            QuestionRow.session_id == row.id
                        )
                    )
                    or 0
                )
                + 1
            )
            kind = (
                QuestionKind.FOLLOW_UP.value
                if action is InterviewAction.FOLLOW_UP
                else QuestionKind.CLARIFICATION.value
                if action is InterviewAction.CLARIFICATION
                else QuestionKind.BASE.value
            )
            question = QuestionRow(
                session_id=row.id,
                parent_question_id=command.question_id if kind != QuestionKind.BASE.value else None,
                sequence=sequence,
                kind=kind,
                text=next_question_text or "",
                provenance_json=(
                    next_question_provenance.to_json() if next_question_provenance else None
                ),
            )
            self._session.add(question)
            self._session.flush()
            row.active_question_id = question.id
            question_text = question.text
            if action is InterviewAction.FOLLOW_UP:
                row.follow_up_count += 1
            elif action is InterviewAction.CLARIFICATION:
                row.clarification_count += 1
            else:
                row.base_question_count += 1
                row.follow_up_count = row.clarification_count = 0
        elif action is InterviewAction.COMPLETE:
            if result is None:
                raise Conflict("Completed interview is missing its assessment")
            self._session.add(
                AssessmentResultRow(
                    attempt_id=result.attempt_id,
                    score=str(result.score),
                    passed=result.passed,
                    rubric_version=result.rubric_version,
                    evidence_json=[self._evidence_record(item) for item in result.evidence],
                )
            )
            attempt = self._session.get(AssessmentAttemptRow, result.attempt_id)
            if attempt is None:
                raise Conflict("Assessment attempt is unavailable")
            attempt.status = "passed" if result.passed else "failed"
        target = {
            InterviewAction.FOLLOW_UP: InterviewState.AWAITING_FOLLOW_UP_ANSWER,
            InterviewAction.CLARIFICATION: InterviewState.AWAITING_FOLLOW_UP_ANSWER,
            InterviewAction.NEXT_QUESTION: InterviewState.AWAITING_ANSWER,
            InterviewAction.COMPLETE: InterviewState.COMPLETED,
        }[action]
        aggregate = self._aggregate(row)
        try:
            transition(aggregate, target, reservation.processing_version)
            row.state = aggregate.state.value
            row.version = aggregate.version
            row.completed_at = aggregate.completed_at
            row.processing_started_at = None
            self._session.commit()
        except StaleDataError as exc:
            self._session.rollback()
            raise Conflict("stale_version") from exc
        except IntegrityError as exc:
            self._session.rollback()
            raise Conflict("Answer command conflicts with an existing result") from exc
        logger.info(
            "answer_persisted session_id=%s question_id=%s processing_version=%s "
            "action=%s final_version=%s",
            row.id,
            command.question_id,
            reservation.processing_version,
            action.value,
            row.version,
        )
        if action is InterviewAction.COMPLETE:
            logger.info(
                "interview_completed session_id=%s stage=%s final_version=%s",
                row.id,
                row.stage,
                row.version,
            )
        return AnswerCompletion(
            row.state,
            row.version,
            action,
            question_text,
            result.score if result else None,
        )

    def _previous_evidence(self, session_id: UUID) -> tuple[EvaluationEvidence, ...]:
        records = self._session.execute(
            select(EvaluationRow.evidence_json, EvaluationRow.rubric_version, QuestionRow)
            .join(AnswerRow, AnswerRow.id == EvaluationRow.answer_id)
            .join(QuestionRow, QuestionRow.id == AnswerRow.question_id)
            .where(AnswerRow.session_id == session_id)
        ).all()
        evidence: list[EvaluationEvidence] = []
        for record, rubric_version, question in records:
            if not isinstance(record, list):
                raise ValueError("Stored evaluation evidence is malformed")
            root = self._question_root(question)
            rubric_row = self._session.get(AssessmentRubricRow, rubric_version)
            dimensions = rubric_row.dimensions_json if rubric_row else []
            weights = {
                str(item.get("key")): Decimal(str(item.get("weight")))
                for item in dimensions
                if isinstance(item, dict) and item.get("key") is not None
            }
            for item in record:
                if not isinstance(item, dict):
                    raise ValueError("Stored evaluation evidence is malformed")
                score = item.get("score")
                evidence_value = item.get("evidence", [])
                missing_value = item.get("missing", [])
                if not isinstance(evidence_value, list) or not isinstance(missing_value, list):
                    raise ValueError("Stored evaluation evidence is malformed")
                evidence.append(
                    EvaluationEvidence(
                        dimension_key=str(item["dimension"]),
                        supporting_evidence=tuple(str(value) for value in evidence_value),
                        missing_evidence=tuple(str(value) for value in missing_value),
                        insufficient_evidence=bool(item.get("insufficient", False)),
                        confidence=Decimal(str(item.get("confidence", "0"))),
                        score=Decimal(str(score)) if score not in (None, "None") else None,
                        explanation=str(item.get("explanation", ""))[:500],
                        relevance=self._rating(item.get("relevance")),
                        correctness=self._rating(item.get("correctness")),
                        completeness=self._rating(item.get("completeness")),
                        root_question_id=(
                            UUID(str(item["root_question_id"]))
                            if item.get("root_question_id")
                            else root.id
                        ),
                        dimension_weight=(
                            Decimal(str(item["dimension_weight"]))
                            if item.get("dimension_weight") is not None
                            else (
                                weights[str(item["dimension"])]
                                if str(item["dimension"]) in weights
                                else Decimal("1") if len(record) == 1 else None
                            )
                        ),
                    )
                )
        return tuple(evidence)

    def _question_root(self, question: QuestionRow) -> QuestionRow:
        root = question
        while root.parent_question_id is not None:
            parent = self._session.get(QuestionRow, root.parent_question_id)
            if parent is None:
                raise ValueError("Question history is incomplete")
            root = parent
        return root

    @staticmethod
    def _rating(value: object) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int):
            raise ValueError("Stored evaluation rating is malformed")
        return value

    @staticmethod
    def _aggregate(row: InterviewSessionRow) -> InterviewSession:
        return InterviewSession(
            student_id=row.student_id,
            stage=InterviewStage(row.stage),
            course_id=row.course_id,
            content_revision_id=row.content_revision_id,
            id=row.id,
            state=InterviewState(row.state),
            version=row.version,
            base_question_count=row.base_question_count,
            follow_up_count=row.follow_up_count,
            clarification_count=row.clarification_count,
            active_question_id=row.active_question_id,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )

    @staticmethod
    def _evidence_record(item: EvaluationEvidence) -> dict[str, object]:
        return {
            "dimension": item.dimension_key,
            "evidence": list(item.supporting_evidence),
            "missing": list(item.missing_evidence),
            "insufficient": item.insufficient_evidence,
            "confidence": str(item.confidence),
            "score": str(item.score) if item.score is not None else None,
            "explanation": item.explanation,
            "relevance": item.relevance,
            "correctness": item.correctness,
            "completeness": item.completeness,
            "root_question_id": str(item.root_question_id) if item.root_question_id else None,
            "dimension_weight": (
                str(item.dimension_weight) if item.dimension_weight is not None else None
            ),
        }
