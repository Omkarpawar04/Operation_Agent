import { BrowserSpeechInput } from './adapters/speech/browser-speech-input';
import { BrowserSpeechOutput } from './adapters/speech/browser-speech-output';
import { InterviewApiClient } from './api/interview-api-client';
import { ResultsDashboardUI } from './components/results-dashboard-ui';
import { VoiceInterviewUI } from './components/voice-interview-ui';
import { VoiceInterviewLifecycle } from './orchestrator/voice-interview-lifecycle';
import { InterviewStage, InterviewSession } from './types/interview';

export type PortalView = 'progression' | 'interview' | 'results';

export interface PortalAppConfig {
  apiBaseUrl?: string;
  devUserId?: string;
  bearerToken?: string;
}

export class PortalApp {
  private _headerEl: HTMLElement;
  private _mainEl: HTMLElement;
  private _apiClient: InterviewApiClient;
  private _currentView: PortalView = 'progression';
  private _activeSessionId: string | null = null;
  private _activeStage: string | null = null;
  private _voiceUI: VoiceInterviewUI | null = null;
  private _voiceLifecycle: VoiceInterviewLifecycle | null = null;
  private _dashboardUI: ResultsDashboardUI;
  private _activeInterview: InterviewSession | null = null;

  constructor(headerEl: HTMLElement, mainEl: HTMLElement, config?: PortalAppConfig) {
    this._headerEl = headerEl;
    this._mainEl = mainEl;

    // Use environment or sensible local development defaults
    const baseUrl = config?.apiBaseUrl || (import.meta as any).env?.VITE_API_URL || '/api/v1';
    const devUserId =
      config?.devUserId ||
      (import.meta as any).env?.VITE_DEV_USER_ID ||
      '00000000-0000-0000-0000-000000000001';
    const bearerToken = config?.bearerToken || (import.meta as any).env?.VITE_AUTH_TOKEN;

    this._apiClient = new InterviewApiClient({
      baseUrl,
      devUserId,
      bearerToken,
    });

    this._dashboardUI = new ResultsDashboardUI(this._mainEl, this._apiClient, {
      onStartInterview: (stage) => this.handleStageAction(stage as InterviewStage),
      onViewResults: (sessionId) => this.showResults(sessionId),
    });

    this._renderHeader();
  }

  get currentView(): PortalView {
    return this._currentView;
  }

  get activeSessionId(): string | null {
    return this._activeSessionId;
  }

  get activeInterview(): InterviewSession | null {
    return this._activeInterview;
  }

  private _renderHeader(): void {
    const isDev = !this._apiClient.hasBearerToken();

    this._headerEl.innerHTML = `
      <div class="portal-brand">
        <span class="brand-badge">FINXL</span>
        <h1 class="brand-title">AI Interviewer Student Portal</h1>
      </div>
      <div class="portal-nav">
        <button id="nav-progression-btn" class="nav-tab-btn ${this._currentView === 'progression' ? 'active' : ''}">
          Curriculum &amp; Stages
        </button>
        ${
          this._activeSessionId
            ? `<button id="nav-interview-btn" class="nav-tab-btn ${this._currentView === 'interview' ? 'active' : ''}">
                ${this._currentView === 'interview' ? 'Active Interview' : 'Resume Interview'}
               </button>`
            : ''
        }
        <span class="auth-badge">
          ${isDev ? 'Development Mode' : 'Authenticated'}
        </span>
      </div>
    `;

    this._headerEl.querySelector('#nav-progression-btn')?.addEventListener('click', () => {
      this.showProgression();
    });

    this._headerEl.querySelector('#nav-interview-btn')?.addEventListener('click', () => {
      if (this._activeSessionId) {
        this.showInterview(this._activeSessionId);
      }
    });
  }

  /**
   * Checks for an active, resumable interview session from the backend on startup.
   */
  async checkResumableSession(): Promise<InterviewSession | null> {
    try {
      const active = await this._apiClient.getActiveInterview();
      this._activeInterview = active;
      if (active) {
        this._activeSessionId = active.id;
        this._activeStage = active.stage;
      } else {
        this._activeSessionId = null;
        this._activeStage = null;
      }
      this._renderHeader();
      return active;
    } catch {
      return null;
    }
  }

  async showProgression(): Promise<void> {
    this._cleanupVoiceInterview();
    this._currentView = 'progression';
    await this.checkResumableSession();
    this._renderHeader();
    await this._dashboardUI.renderProgression();
  }

  showResults(sessionId: string): void {
    this._cleanupVoiceInterview();
    this._currentView = 'results';
    this._activeSessionId = null;
    this._activeInterview = null;
    this._renderHeader();
    this._dashboardUI.renderAssessmentResult(sessionId);
  }

  /**
   * Starts a new stage or resumes an existing interview if one is already active for this student.
   */
  async handleStageAction(stage: InterviewStage): Promise<void> {
    // If the student already has an active session for this stage (or any stage), resume it directly!
    if (this._activeInterview) {
      if (this._activeInterview.stage === stage) {
        await this.showInterview(this._activeInterview.id);
        return;
      }
    }

    // Double check with backend before attempting start to avoid 409 conflict
    const active = await this.checkResumableSession();
    if (active) {
      if (active.stage === stage) {
        await this.showInterview(active.id);
        return;
      } else {
        // Active session exists for a different stage
        this._mainEl.innerHTML = `
          <div class="portal-alert alert-error">
            <strong>Active Session in Progress:</strong> You already have an unfinished interview in stage <strong>${this._escapeHtml(active.stage)}</strong>. Please resume and complete or abandon that session before starting a new stage.
          </div>
          <div style="text-align: center; margin-top: 1rem; display: flex; gap: 12px; justify-content: center;">
            <button id="resume-existing-active-btn" class="btn-primary">Resume ${this._escapeHtml(active.stage)} Interview</button>
            <button id="return-from-conflict-btn" class="btn-secondary">Return to Stages</button>
          </div>
        `;
        this._mainEl.querySelector('#resume-existing-active-btn')?.addEventListener('click', () => {
          this.showInterview(active.id);
        });
        this._mainEl.querySelector('#return-from-conflict-btn')?.addEventListener('click', () => {
          this.showProgression();
        });
        return;
      }
    }

    await this.startInterview(stage);
  }

  async startInterview(stage: InterviewStage): Promise<void> {
    this._cleanupVoiceInterview();
    this._currentView = 'interview';
    this._activeStage = stage;
    this._renderHeader();

    this._mainEl.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem;">
        <div style="font-size: 1.2rem; font-weight: 600; color: var(--secondary-navy); margin-bottom: 0.5rem;">
          Preparing Your Interview Session...
        </div>
        <div style="color: var(--text-muted); font-size: 0.9rem;">
          Initializing stage: ${stage} with FINXL deterministic evaluation engine.
        </div>
      </div>
    `;

    try {
      const idempotencyKey = `voice-start-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      const session = await this._apiClient.startInterview({
        stage,
        idempotency_key: idempotencyKey,
      });

      this._activeSessionId = session.id;
      this._renderHeader();
      await this.showInterview(session.id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start interview session.';
      this._mainEl.innerHTML = `
        <div class="portal-alert alert-error">
          <strong>Unable to start interview:</strong> ${this._escapeHtml(message)}
        </div>
        <div style="text-align: center; margin-top: 1rem;">
          <button id="return-from-error-btn" class="btn-secondary">Return to Stages</button>
        </div>
      `;
      this._mainEl.querySelector('#return-from-error-btn')?.addEventListener('click', () => {
        this.showProgression();
      });
    }
  }

  async showInterview(sessionId: string): Promise<void> {
    this._cleanupVoiceInterview();
    this._currentView = 'interview';
    this._activeSessionId = sessionId;
    this._renderHeader();

    this._mainEl.innerHTML = `<div id="voice-interview-container"></div>`;
    const container = this._mainEl.querySelector<HTMLElement>('#voice-interview-container')!;

    const speechInput = new BrowserSpeechInput();
    const speechOutput = new BrowserSpeechOutput();

    this._voiceLifecycle = new VoiceInterviewLifecycle({
      apiClient: this._apiClient,
      speechInput,
      speechOutput,
      autoSpeakQuestions: true,
    });

    this._voiceUI = new VoiceInterviewUI(container, this._voiceLifecycle, {
      onComplete: (completedSessionId) => {
        this.showResults(completedSessionId);
      },
      onExit: () => {
        this.showProgression();
      },
    });

    await this._voiceLifecycle.initialize(sessionId);
  }

  private _cleanupVoiceInterview(): void {
    if (this._voiceUI) {
      this._voiceUI.destroy();
      this._voiceUI = null;
    }
    if (this._voiceLifecycle) {
      this._voiceLifecycle.dispose();
      this._voiceLifecycle = null;
    }
  }

  private _escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
