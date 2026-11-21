import { InterviewApiClient } from '../api/interview-api-client';
import { ProgressionResponse, ProgressionStage } from '../types/interview';
import { DetailedAssessmentResult } from '../types/assessment';

export interface DashboardCallbacks {
  onStartInterview: (stage: string) => void;
  onViewResults: (sessionId: string) => void;
}

export class ResultsDashboardUI {
  private _container: HTMLElement;
  private _apiClient: InterviewApiClient;
  private _callbacks: DashboardCallbacks;

  constructor(
    container: HTMLElement,
    apiClient: InterviewApiClient,
    callbacks: DashboardCallbacks
  ) {
    this._container = container;
    this._apiClient = apiClient;
    this._callbacks = callbacks;
  }

  static readonly STAGE_METADATA: Record<string, { title: string; category: string; description: string }> = {
    soft_1: {
      title: 'Finance Foundations and Communication',
      category: 'Soft Skills (Stage 1/3)',
      description: 'Explain basic finance concepts clearly, including working capital and why cash flow management matters.',
    },
    soft_2: {
      title: 'Conceptual Understanding and Financial Reasoning',
      category: 'Soft Skills (Stage 2/3)',
      description: 'Interpret basic financial ratios and connect profitability, liquidity, working capital, and business health.',
    },
    soft_3: {
      title: 'Practical Finance Scenarios',
      category: 'Soft Skills (Stage 3/3)',
      description: 'Analyze realistic business problems and justify recommendations for non-finance stakeholders.',
    },
    technical_1: {
      title: 'Financial Modeling Fundamentals',
      category: 'Technical Skills (Stage 1/3)',
      description: 'Build and explain forecasts from historical data, assumptions, and business drivers.',
    },
    technical_2: {
      title: 'Financial Statements and Ratio Analysis',
      category: 'Technical Skills (Stage 2/3)',
      description: 'Interpret financial statements, ratios, trends, and comparisons in context.',
    },
    technical_3: {
      title: 'Advanced Financial Modeling Applications',
      category: 'Technical Skills (Stage 3/3)',
      description: 'Integrate forecasts, sensitivities, variance analysis, and evidence based recommendations.',
    },
  };

  async renderProgression(courseId?: string): Promise<void> {
    this._container.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem;">
        <div style="font-size: 1.1rem; color: var(--text-muted);">Loading your interview progression...</div>
      </div>
    `;

    try {
      const data: ProgressionResponse = await this._apiClient.getProgression(courseId);
      this._renderProgressionView(data.stages);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load student progression.';
      this._container.innerHTML = `
        <div class="portal-alert alert-error">
          <strong>Progression Unavailable:</strong> ${this._escapeHtml(message)}
        </div>
        <div style="text-align: center; margin-top: 1rem;">
          <button id="retry-progression-btn" class="btn-secondary">Retry</button>
        </div>
      `;
      this._container.querySelector('#retry-progression-btn')?.addEventListener('click', () => {
        this.renderProgression(courseId);
      });
    }
  }

  private _renderProgressionView(stages: ProgressionStage[]): void {
    const passedCount = stages.filter((s) => s.status === 'passed').length;
    const totalCount = stages.length;
    const progressPercent = Math.round((passedCount / totalCount) * 100);

    let html = `
      <div class="assessment-overview-card" style="text-align: left; padding: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <div>
            <h2 style="margin: 0; font-size: 1.4rem; color: var(--primary-navy);">Student Interview Journey</h2>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; color: var(--text-muted);">
              Progress through all 6 deterministic interview stages to complete FINXL certification.
            </p>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-blue);">${passedCount} / ${totalCount} Passed</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${progressPercent}% Completed</div>
          </div>
        </div>
        <div style="background: #e2e8f0; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 1rem;">
          <div style="background: var(--accent-blue); height: 100%; width: ${progressPercent}%; transition: width 0.3s ease;"></div>
        </div>
      </div>

      <div class="dashboard-grid">
    `;

    for (const item of stages) {
      const meta = ResultsDashboardUI.STAGE_METADATA[item.stage] || { title: item.stage, category: 'Interview Stage', description: '' };

      const statusBadge = this._getStatusBadgeHtml(item.status);
      const isAvailable = item.status === 'available' || item.status === 'in_progress';
      const isPassed = item.status === 'passed';

      html += `
        <div class="stage-card ${isPassed ? 'is-complete' : isAvailable ? 'is-active' : 'is-locked'}" data-stage="${item.stage}">
          <div>
            <div class="stage-card-header">
              <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 600;">${meta.category}</span>
              ${statusBadge}
            </div>
            <h3 class="stage-title">${this._escapeHtml(meta.title)}</h3>
            <p class="stage-description">${this._escapeHtml(meta.description)}</p>
            <p class="stage-description">${this._escapeHtml(item.stage.replace('_', ' ').toUpperCase())} · ${this._escapeHtml(item.status.replace('_', ' '))}</p>
          </div>
          <div style="margin-top: 1rem;">
            ${
              isAvailable
                ? `<button class="btn-primary start-stage-btn" data-stage="${item.stage}" style="width: 100%;">
                    ${item.status === 'in_progress' ? 'Resume Interview' : 'Start Stage Interview'}
                   </button>`
                : isPassed
                ? `<div style="text-align: center; color: var(--success-text); font-weight: 600; font-size: 0.85rem; padding: 0.5rem; background: var(--success-bg); border-radius: 4px;">
                    Stage Cleared
                   </div>`
                : `<button class="btn-primary" disabled style="width: 100%;">
                    ${item.status === 'course_required' ? 'Enrollment Required' : 'Stage Locked'}
                   </button>`
            }
          </div>
        </div>
      `;
    }

    html += `</div>`;
    this._container.innerHTML = html;

    // Attach event listeners to start buttons
    this._container.querySelectorAll('.start-stage-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const stage = (e.currentTarget as HTMLElement).getAttribute('data-stage');
        if (stage) {
          this._callbacks.onStartInterview(stage);
        }
      });
    });
  }

  async renderAssessmentResult(sessionId: string): Promise<void> {
    this._container.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem;">
        <div style="font-size: 1.1rem; color: var(--text-muted);">Retrieving assessment results...</div>
      </div>
    `;

    try {
      const result: DetailedAssessmentResult = (await this._apiClient.getAssessment(
        sessionId
      )) as DetailedAssessmentResult;
      this._renderAssessmentView(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Assessment is not available.';
      this._container.innerHTML = `
        <div class="portal-alert alert-error">
          <strong>Assessment View Error:</strong> ${this._escapeHtml(message)}
        </div>
        <div style="text-align: center; margin-top: 1rem;">
          <button id="back-to-progression-btn" class="btn-secondary">Return to Progression</button>
        </div>
      `;
      this._container.querySelector('#back-to-progression-btn')?.addEventListener('click', () => {
        this.renderProgression();
      });
    }
  }

  private _renderAssessmentView(result: DetailedAssessmentResult): void {
    const passed = result.passed;
    const scoreNum = parseFloat(String(result.score));
    const scoreFormatted = isNaN(scoreNum) ? String(result.score) : scoreNum.toFixed(1);

    let html = `
      <div class="assessment-overview-card">
        <span class="outcome-badge ${passed ? 'outcome-passed' : 'outcome-failed'}">
          ${passed ? 'STAGE PASSED' : 'STAGE FAILED'}
        </span>
        <div class="score-display">${scoreFormatted}<span style="font-size: 1.75rem; color: var(--text-muted); font-weight: 500;">/100</span></div>
        <p style="color: var(--text-muted); font-size: 0.95rem; max-width: 500px; margin: 0 auto;">
          ${
            passed
              ? 'Congratulations! You have satisfied the deterministic rubric criteria for this stage.'
              : 'You have not met the passing threshold for this stage. Please review the rubric feedback below before re-attempting.'
          }
        </p>

        <div class="assessment-meta-grid">
          <div class="meta-item">
            <div class="meta-label">Attempt Identifier</div>
            <div class="meta-value" style="font-size: 0.85rem; font-family: monospace; word-break: break-all;">
              ${this._escapeHtml(result.attempt_id)}
            </div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Rubric Version</div>
            <div class="meta-value">${this._escapeHtml(result.rubric_version)}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Assessment Policy</div>
            <div class="meta-value">Deterministic Python Policy</div>
          </div>
        </div>
      </div>
    `;

    if (result.competency_feedback?.length) {
      html += `
        <div class="dimensions-section">
          <h3 style="margin-top: 0; font-size: 1.2rem; color: var(--secondary-navy); margin-bottom: 1.25rem;">
            Competency Feedback
          </h3>
          ${result.competency_feedback.map((item) => `
            <div class="dimension-card">
              <div class="dimension-header">
                <span class="dimension-title">${this._escapeHtml(item.title)}</span>
              </div>
              ${item.strengths.length ? `<p><strong>Demonstrated:</strong> ${item.strengths.map((value) => this._escapeHtml(value)).join(' · ')}</p>` : ''}
              ${item.areas_for_improvement.length ? `<p><strong>To practice:</strong> ${item.areas_for_improvement.map((value) => this._escapeHtml(value)).join(' · ')}</p>` : ''}
            </div>
          `).join('')}
        </div>
      `;
    }

    // Evidence / Rubric breakdown if available
    if (!result.competency_feedback?.length && result.evidence && result.evidence.length > 0) {
      html += `
        <div class="dimensions-section">
          <h3 style="margin-top: 0; font-size: 1.2rem; color: var(--secondary-navy); margin-bottom: 1.25rem;">
            Rubric Evaluation &amp; Evidence Breakdown
          </h3>
      `;

      for (const item of result.evidence) {
        const dimScore = item.score !== null ? `${parseFloat(item.score).toFixed(1)}/100` : 'Unscored';
        html += `
          <div class="dimension-card">
            <div class="dimension-header">
              <span class="dimension-title">${this._escapeHtml(this._formatDimensionName(item.dimension))}</span>
              <span class="dimension-score">${dimScore}</span>
            </div>
            ${item.explanation ? `<p style="font-size: 0.9rem; color: #475569; margin: 0.25rem 0 0.5rem 0;">${this._escapeHtml(item.explanation)}</p>` : ''}
            
            ${
              item.evidence && item.evidence.length > 0
                ? `<div style="margin-top: 0.5rem;">
                    <strong style="font-size: 0.8rem; color: var(--success-text); text-transform: uppercase;">Observed Strengths &amp; Evidence:</strong>
                    <ul class="evidence-list">
                      ${item.evidence.map((e) => `<li>${this._escapeHtml(e)}</li>`).join('')}
                    </ul>
                   </div>`
                : ''
            }

            ${
              item.missing && item.missing.length > 0
                ? `<div style="margin-top: 0.5rem;">
                    <strong style="font-size: 0.8rem; color: var(--error-text); text-transform: uppercase;">Areas for Improvement:</strong>
                    <ul class="evidence-list">
                      ${item.missing.map((m) => `<li>${this._escapeHtml(m)}</li>`).join('')}
                    </ul>
                   </div>`
                : ''
            }
          </div>
        `;
      }

      html += `</div>`;
    }

    html += `
      <div style="text-align: center; margin-top: 2rem;">
        <button id="dashboard-return-btn" class="btn-primary" style="padding: 0.75rem 2rem;">
          Return to Interview Dashboard
        </button>
      </div>
    `;

    this._container.innerHTML = html;
    this._container.querySelector('#dashboard-return-btn')?.addEventListener('click', () => {
      this.renderProgression();
    });
  }

  private _getStatusBadgeHtml(status: string): string {
    switch (status) {
      case 'available':
        return '<span class="stage-badge badge-available">Ready to Start</span>';
      case 'in_progress':
        return '<span class="stage-badge badge-in_progress">In Progress</span>';
      case 'passed':
        return '<span class="stage-badge badge-passed">Passed</span>';
      case 'failed':
        return '<span class="stage-badge badge-failed">Failed</span>';
      case 'course_required':
        return '<span class="stage-badge badge-locked">Course Req</span>';
      case 'locked':
      default:
        return '<span class="stage-badge badge-locked">Locked</span>';
    }
  }

  private _formatDimensionName(key: string): string {
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  private _escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
