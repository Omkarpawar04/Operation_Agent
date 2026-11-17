/**
 * Typed contracts matching FINXL backend API specifications (/api/v1).
 */

export type InterviewStage =
  | 'soft_1'
  | 'soft_2'
  | 'soft_3'
  | 'technical_1'
  | 'technical_2'
  | 'technical_3';

export type InterviewState =
  | 'created'
  | 'awaiting_answer'
  | 'answer_processing'
  | 'awaiting_follow_up_answer'
  | 'completed'
  | 'abandoned'
  | 'failed';

export type QuestionKind = 'base' | 'follow_up' | 'clarification';

export interface InterviewSession {
  id: string;
  stage: InterviewStage;
  state: InterviewState;
  version: number;
  active_question_id: string | null;
  question?: string;
}

export interface Question {
  id: string;
  text: string;
  kind: QuestionKind;
  sequence: number;
  version: number;
  stage_id?: InterviewStage;
  content_origin?: string;
  content_approval_status?: string;
  bank_question_id?: string | null;
  competency_id?: string | null;
  rubric_version_id?: string | null;
  content_version?: string | null;
  parent_question_id?: string | null;
  development_only?: boolean;
}

export interface AnswerSubmission {
  question_id: string;
  expected_version: number;
  idempotency_key: string;
  text: string;
}

export interface SkipQuestionSubmission {
  question_id: string;
  expected_version: number;
  idempotency_key: string;
}

export type AnswerAction = 'follow_up' | 'clarification' | 'next_question' | 'complete';

export interface AnswerResponse {
  state: InterviewState;
  version: number;
  question: string | null;
  action?: AnswerAction | null;
}

export interface AssessmentResult {
  attempt_id: string;
  score: string | number;
  passed: boolean;
  rubric_version: string;
}

export type ProgressionStatus =
  | 'available'
  | 'locked'
  | 'passed'
  | 'failed'
  | 'in_progress'
  | 'course_required';

export interface ProgressionStage {
  stage: InterviewStage;
  status: ProgressionStatus;
}

export interface ProgressionResponse {
  stages: ProgressionStage[];
}

export interface StartInterviewPayload {
  stage: InterviewStage;
  idempotency_key: string;
  course_id?: string;
}

export interface AbandonPayload {
  expected_version: number;
}

export type VoiceInterviewState =
  | 'uninitialized'
  | 'loading'
  | 'question_ready'
  | 'speaking_question'
  | 'listening'
  | 'recognizing'
  | 'submitting'
  | 'skipping'
  | 'follow_up_received'
  | 'completed'
  | 'error'
  | 'abandoned';
