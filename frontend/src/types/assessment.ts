export interface DimensionEvidenceItem {
  dimension: string;
  evidence: string[];
  missing: string[];
  insufficient: boolean;
  confidence: string;
  score: string | null;
  explanation: string;
  relevance?: number | null;
  correctness?: number | null;
  completeness?: number | null;
}

export interface DetailedAssessmentResult {
  attempt_id: string;
  score: string;
  passed: boolean;
  rubric_version: string;
  evidence?: DimensionEvidenceItem[];
  competency_feedback?: CompetencyFeedbackItem[];
}

export interface CompetencyFeedbackItem {
  competency_id: string;
  title: string;
  strengths: string[];
  areas_for_improvement: string[];
}
