import { describe, it, expect, beforeEach, vi } from 'vitest';
import { PortalApp } from '../src/portal-app';
import { InterviewApiClient } from '../src/api/interview-api-client';

describe('PortalApp Full Student Flow', () => {
  let headerEl: HTMLElement;
  let mainEl: HTMLElement;
  let app: PortalApp;

  beforeEach(() => {
    headerEl = document.createElement('header');
    mainEl = document.createElement('main');
    document.body.appendChild(headerEl);
    document.body.appendChild(mainEl);

    app = new PortalApp(headerEl, mainEl, {
      apiBaseUrl: 'http://test-server/api/v1',
      devUserId: '00000000-0000-0000-0000-000000000001',
    });
  });

  it('initializes in progression view with navigation buttons', () => {
    expect(app.currentView).toBe('progression');
    expect(headerEl.textContent).toContain('AI Interviewer Student Portal');
    expect(headerEl.textContent).toContain('Curriculum & Stages');
    expect(headerEl.textContent).toContain('Development Mode');
  });

  it('switches views between progression and interview', async () => {
    const apiClient = (app as any)._apiClient as InterviewApiClient;

    vi.spyOn(apiClient, 'startInterview').mockResolvedValue({
      id: 'sess-new-123',
      stage: 'soft_1',
      state: 'awaiting_answer',
      version: 0,
      active_question_id: 'q-1',
      question: 'Introduce yourself and your finance background.',
    });

    vi.spyOn(apiClient, 'getInterview').mockResolvedValue({
      id: 'sess-new-123',
      stage: 'soft_1',
      state: 'awaiting_answer',
      version: 0,
      active_question_id: 'q-1',
    });

    vi.spyOn(apiClient, 'getActiveQuestion').mockResolvedValue({
      id: 'q-1',
      text: 'Introduce yourself and your finance background.',
      kind: 'base',
      sequence: 1,
      version: 0,
    });

    await app.startInterview('soft_1');

    expect(app.currentView).toBe('interview');
    expect(app.activeSessionId).toBe('sess-new-123');
    expect(mainEl.textContent).toContain('FINXL AI INTERVIEW STUDIO');
    expect(mainEl.textContent).toContain('Introduce yourself and your finance background.');

    // Switch back to progression
    app.showProgression();
    expect(app.currentView).toBe('progression');
  });
});
