import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ResultsDashboardUI } from '../src/components/results-dashboard-ui';
import { InterviewApiClient } from '../src/api/interview-api-client';
import { ProgressionResponse } from '../src/types/interview';

describe('ResultsDashboardUI Component', () => {
  let container: HTMLElement;
  let apiClient: InterviewApiClient;
  let startInterviewMock: ReturnType<typeof vi.fn>;
  let viewResultsMock: ReturnType<typeof vi.fn>;
  let dashboard: ResultsDashboardUI;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    apiClient = new InterviewApiClient({ baseUrl: 'http://test-server/api/v1' });
    startInterviewMock = vi.fn();
    viewResultsMock = vi.fn();
    dashboard = new ResultsDashboardUI(container, apiClient, {
      onStartInterview: startInterviewMock,
      onViewResults: viewResultsMock,
    });
  });

  it('renders all 6 progression stages with correct status badges', async () => {
    const progressionData: ProgressionResponse = {
      stages: [
        { stage: 'soft_1', status: 'passed' },
        { stage: 'soft_2', status: 'available' },
        { stage: 'soft_3', status: 'locked' },
        { stage: 'technical_1', status: 'locked' },
        { stage: 'technical_2', status: 'locked' },
        { stage: 'technical_3', status: 'locked' },
      ],
    };

    vi.spyOn(apiClient, 'getProgression').mockResolvedValue(progressionData);

    await dashboard.renderProgression();

    expect(container.textContent).toContain('Student Interview Journey');
    expect(container.textContent).toContain('1 / 6 Passed');
    expect(container.textContent).toContain('Communication & Behavioral Foundations');
    expect(container.textContent).toContain('Stage Cleared');
    expect(container.textContent).toContain('Problem Framing & Structured Thinking');
    expect(container.textContent).toContain('Start Stage Interview');
    expect(container.textContent).toContain('Executive Presence & Stakeholder Influence');
    expect(container.textContent).toContain('Accounting Fundamentals & 3-Statement Mechanics');

    // Clicking available start stage button triggers callback
    const startBtn = container.querySelector<HTMLButtonElement>('.start-stage-btn[data-stage="soft_2"]');
    expect(startBtn).not.toBeNull();
    startBtn?.click();
    expect(startInterviewMock).toHaveBeenCalledWith('soft_2');
  });

  it('renders error banner when progression API fails and allows retry', async () => {
    vi.spyOn(apiClient, 'getProgression')
      .mockRejectedValueOnce(new Error('Network disconnected'))
      .mockResolvedValueOnce({
        stages: [{ stage: 'soft_1', status: 'available' }],
      });

    await dashboard.renderProgression();

    expect(container.textContent).toContain('Progression Unavailable: Network disconnected');
    const retryBtn = container.querySelector<HTMLButtonElement>('#retry-progression-btn');
    expect(retryBtn).not.toBeNull();

    retryBtn?.click();
    // Wait next tick
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(container.textContent).toContain('Student Interview Journey');
  });

  it('renders detailed assessment results with score, attempt ID, and rubric evidence breakdown', async () => {
    const assessmentData = {
      attempt_id: 'att-555-uuid',
      score: '88.5',
      passed: true,
      rubric_version: 'rubric_v2',
      evidence: [
        {
          dimension: 'financial_accuracy',
          evidence: ['Correctly identified working capital cash impact'],
          missing: ['Could elaborate on Capex timing effects'],
          insufficient: false,
          confidence: '0.95',
          score: '90.0',
          explanation: 'Clear and accurate calculation flow.',
        },
      ],
    };

    vi.spyOn(apiClient, 'getAssessment').mockResolvedValue(assessmentData as any);

    await dashboard.renderAssessmentResult('sess-completed-1');

    expect(container.textContent).toContain('STAGE PASSED');
    expect(container.textContent).toContain('88.5');
    expect(container.textContent).toContain('att-555-uuid');
    expect(container.textContent).toContain('rubric_v2');
    expect(container.textContent).toContain('Financial Accuracy');
    expect(container.textContent).toContain('Correctly identified working capital cash impact');
    expect(container.textContent).toContain('Could elaborate on Capex timing effects');
    expect(container.textContent).toContain('Clear and accurate calculation flow.');
  });
});
