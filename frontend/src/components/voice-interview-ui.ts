import {
  VoiceInterviewLifecycle,
  VoiceInterviewSnapshot,
} from '../orchestrator/voice-interview-lifecycle';

export interface VoiceInterviewUIOptions {
  onComplete?: (sessionId: string) => void;
  onExit?: () => void;
}

/**
 * DOM-based Voice Interview component rendering question display, spoken indicators,
 * real-time recognition feedback, read-only transcript preview, error banners, and voice-only controls.
 */
export class VoiceInterviewUI {
  private _container: HTMLElement;
  private _lifecycle: VoiceInterviewLifecycle;
  private _options?: VoiceInterviewUIOptions;
  private _unsubscribe: (() => void) | null = null;

  constructor(
    container: HTMLElement,
    lifecycle: VoiceInterviewLifecycle,
    options?: VoiceInterviewUIOptions
  ) {
    this._container = container;
    this._lifecycle = lifecycle;
    this._options = options;
    this._init();
  }

  private _init(): void {
    this._unsubscribe = this._lifecycle.subscribe((snapshot) => {
      this._render(snapshot);
    });
  }

  private _render(snapshot: VoiceInterviewSnapshot): void {
    const {
      sessionId,
      state,
      activeQuestion,
      isSpeaking,
      isListening,
      isSubmitting,
      playbackBlocked,
      interimTranscript,
      finalTranscript,
      lastError,
      assessmentResult,
      isSpeechInputSupported,
      isSpeechOutputSupported,
      isFollowUp,
      microphoneState,
    } = snapshot;

    let html = `
      <div class="finxl-voice-interview" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 760px; margin: 0 auto; padding: 24px; border: 1px solid var(--border-color, #e2e8f0); border-radius: 12px; background: #ffffff; box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.1));">
        <header style="border-bottom: 1px solid #edf2f7; padding-bottom: 14px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
          <div>
            <h2 style="margin: 0; font-size: 1.25rem; color: #0f172a;">FINXL AI Voice Interview</h2>
            <span style="display: inline-block; margin-top: 6px; font-size: 0.9rem; color: #475569; font-weight: 600;">
              ${this._stageLabel(snapshot.stage)}
            </span>
          </div>
          ${
            this._options?.onExit
              ? `<button type="button" id="finxl-btn-exit-session" class="btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;">Exit</button>`
              : ''
          }
        </header>
    `;

    // 1. Completed State
    if (state === 'completed' && assessmentResult) {
      const passed = assessmentResult.passed;
      html += `
        <div class="finxl-completed-card" style="padding: 32px 24px; text-align: center; background: ${passed ? '#f0fdf4' : '#fef2f2'}; border: 1px solid ${passed ? '#86efac' : '#fca5a5'}; border-radius: 8px;">
          <h3 style="color: ${passed ? '#22543d' : '#742a2a'}; margin-top: 0; font-size: 1.25rem;">
            ${passed ? 'Interview Completed — PASSED' : 'Interview Completed — NOT PASSED'}
          </h3>
          <p style="font-size: 1.125rem; font-weight: 600; color: #2d3748; margin: 12px 0;">
            Final Score: ${assessmentResult.score}%
          </p>
          <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 20px;">
            Attempt ID: ${this._escapeHtml(assessmentResult.attempt_id)} | Rubric: ${this._escapeHtml(assessmentResult.rubric_version)}
          </p>
          <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;">
            ${
              this._options?.onComplete
                ? `<button type="button" id="finxl-btn-view-detailed-results" class="btn-primary" style="padding: 8px 20px;">
                    View Detailed Results &amp; Feedback
                   </button>`
                : ''
            }
          </div>
        </div>
      `;
      html += `</div>`;
      this._container.innerHTML = html;
      this._attachCompletedListeners(sessionId);
      return;
    }

    // 2. Abandoned State
    if (state === 'abandoned') {
      html += `
        <div style="padding: 20px; background: #fffaf0; border: 1px solid #fbd38d; border-radius: 8px; color: #744210; text-align: center;">
          <h3 style="margin-top: 0; color: #975a16;">Interview Session Abandoned</h3>
          <p style="margin-bottom: 16px; font-size: 0.9rem;">This session has been terminated and can no longer accept answers.</p>
          ${
            this._options?.onExit
              ? `<button type="button" id="finxl-btn-abandoned-exit" class="btn-secondary">Return to Dashboard</button>`
              : ''
          }
        </div>
      </div>`;
      this._container.innerHTML = html;
      this._container.querySelector('#finxl-btn-abandoned-exit')?.addEventListener('click', () => {
        this._options?.onExit?.();
      });
      return;
    }

    // 3. Question Card (Always prominently visible as readable text)
    if (activeQuestion) {
      const displayQuestion = this._plainQuestionText(activeQuestion.text);
      const contaminatedQuestion = this._isDevelopmentPlaceholder(displayQuestion);
      html += `
        <div class="finxl-question-card" style="background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #2563eb; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="font-size: 1rem; color: #0f172a;">
              Question ${Number.isInteger(activeQuestion.sequence) && activeQuestion.sequence > 0 ? activeQuestion.sequence : ''}
            </strong>
            <div style="display: flex; gap: 6px; align-items: center;">
              ${
                isSpeechOutputSupported
                  ? isSpeaking
                    ? '<button type="button" id="finxl-btn-stop-speech" class="btn-secondary" style="padding: 2px 8px; font-size: 0.75rem; color: #b91c1c;">Stop Speaking</button>'
                    : '<button type="button" id="finxl-btn-replay-speech" class="btn-secondary" style="padding: 2px 8px; font-size: 0.75rem;">Replay Audio</button>'
                  : ''
              }
            </div>
          </div>
          <div style="font-size: 1.15rem; line-height: 1.5; color: #1e293b; font-weight: 500; margin-bottom: 8px;">
            ${contaminatedQuestion ? 'This question is unavailable. Please start a fresh interview.' : this._escapeHtml(displayQuestion)}
          </div>
          ${
            isSpeaking
              ? '<div class="finxl-speaking-indicator" style="color: #2563eb; font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 6px;"><span>Speaking question...</span></div>'
              : ''
          }
          ${
            playbackBlocked
              ? '<div style="margin-top: 8px; font-size: 0.8rem; color: #92400e; background: #fef3c7; padding: 6px 10px; border-radius: 4px;">Browser audio requires interaction: <button type="button" id="finxl-btn-play-blocked" class="btn-secondary" style="padding: 2px 6px; font-size: 0.75rem; margin-left: 6px;">Play Question</button></div>'
              : ''
          }
        </div>
      `;
    }

    // 4. Status Indicator Banner
    let statusText = 'Ready to answer';
    let statusBg = '#f1f5f9';
    let statusColor = '#334155';

    if (isSubmitting) {
      statusText = 'Evaluating answer with FINXL analysis engine...';
      statusBg = '#fef3c7';
      statusColor = '#92400e';
    } else if (isListening) {
      statusText = interimTranscript ? 'Recognizing speech...' : 'Listening... Speak into your microphone';
      statusBg = '#dcfce7';
      statusColor = '#166534';
    } else if (isSpeaking) {
      statusText = 'Question being spoken...';
      statusBg = '#eff6ff';
      statusColor = '#1e40af';
    }

    html += `
      <div class="finxl-status-badge" style="background: ${statusBg}; color: ${statusColor}; padding: 10px 14px; border-radius: 6px; font-size: 0.9rem; font-weight: 600; margin-bottom: 16px; text-align: center;">
        ${statusText}
      </div>
    `;

    // 5. Speech Recognition Transcripts (Strictly read-only display)
    if (isListening || finalTranscript || interimTranscript) {
      html += `
        <div class="finxl-transcript-box" style="border: 1px solid #cbd5e1; padding: 14px; border-radius: 8px; min-height: 64px; margin-bottom: 16px; background: #fafafa;">
          <div style="font-size: 0.7rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
            Spoken Transcript
          </div>
          <div style="color: #1e293b; font-size: 1rem; line-height: 1.5;">
            <span style="font-weight: 500;">${this._escapeHtml(finalTranscript)}</span>
            <span style="color: #64748b; font-style: italic;"> ${this._escapeHtml(interimTranscript)}</span>
          </div>
        </div>
      `;
    }

    // 6. Error Banner
    if (lastError) {
      html += `
        <div class="finxl-error-banner" style="background: #fef2f2; border: 1px solid #fca5a5; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; color: #991b1b; font-size: 0.875rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong>Notice:</strong> ${this._escapeHtml(lastError.message)}
          </div>
          ${lastError.isRetryable ? '<button type="button" id="finxl-btn-retry" class="btn-danger" style="padding: 4px 10px; font-size: 0.75rem;">Retry</button>' : ''}
        </div>
      `;
    }

    // 7. Voice-Only Action Controls (No typed textarea or typing buttons)
    const hasFinalAnswer = Boolean(finalTranscript && finalTranscript.trim());
    const hasSafeQuestion = Boolean(activeQuestion && !this._isDevelopmentPlaceholder(activeQuestion.text));

    html += `
      <div class="finxl-voice-controls" style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px;">
        ${
          microphoneState === 'unsupported'
            ? `<div class="finxl-mic-unsupported" style="color: #991b1b; font-size: 0.9rem; background: #fef2f2; padding: 14px; border-radius: 8px; border: 1px solid #fca5a5;">
                <strong>Speech Recognition Not Supported</strong>
                <p style="margin: 8px 0 4px;">This voice interview requires browser speech recognition support.</p>
                <p style="margin: 0; font-size: 0.85rem;">Please open this page in <strong>Google Chrome</strong> or <strong>Microsoft Edge</strong> to continue.</p>
              </div>`
            : microphoneState === 'denied'
            ? `<div class="finxl-mic-denied" style="background: #fef2f2; border: 1px solid #fca5a5; padding: 16px; border-radius: 8px;">
                <strong style="color: #991b1b;">Microphone Access Required</strong>
                <p style="color: #7f1d1d; font-size: 0.9rem; margin: 8px 0;">
                  Microphone permission was denied. This interview requires microphone access.
                </p>
                <p style="color: #7f1d1d; font-size: 0.85rem; margin: 0 0 12px;">
                  To enable: click the microphone icon in your browser's address bar → Allow → then click Retry below.
                </p>
                <button type="button" id="finxl-btn-retry-mic" class="btn-secondary" style="padding: 8px 16px;">
                  Retry Microphone Access
                </button>
              </div>`
            : microphoneState === 'unavailable'
            ? `<div class="finxl-mic-unavailable" style="background: #fff7ed; border: 1px solid #fed7aa; padding: 16px; border-radius: 8px;">
                <strong style="color: #9a3412;">Microphone Unavailable</strong>
                <p style="color: #7c2d12; font-size: 0.9rem; margin: 8px 0 12px;">
                  Your microphone could not be accessed. Ensure a microphone is connected and not in use by another application.
                </p>
                <button type="button" id="finxl-btn-retry-mic" class="btn-secondary" style="padding: 8px 16px;">
                  Retry Microphone Access
                </button>
              </div>`
            : isSpeechInputSupported
            ? `<div style="display: flex; gap: 12px;">
                ${
                  isListening
                    ? '<button type="button" id="finxl-btn-stop-mic" class="btn-danger" style="flex: 1; padding: 12px 18px; font-size: 1rem;">Stop Listening</button>'
                    : `<button type="button" id="finxl-btn-start-mic" class="btn-primary" ${isSubmitting ? 'disabled' : ''} style="flex: 1; padding: 12px 18px; font-size: 1rem;">${hasFinalAnswer ? 'Speak Again' : 'Start Voice Answer'}</button>`
                }
              </div>
              <div style="margin-top: 4px;">
                <button type="button" id="finxl-btn-submit-voice-answer" class="btn-primary" ${isSubmitting || isListening || !hasFinalAnswer || !hasSafeQuestion ? 'disabled' : ''} style="box-sizing: border-box; width: 100%; min-height: 52px; padding: 12px 18px; font-size: 1rem; font-weight: 700; line-height: 1.4; white-space: normal; overflow: visible; text-overflow: clip; color: #ffffff; background: ${hasFinalAnswer && !isListening && !isSubmitting ? '#15803d' : '#475569'};">
                  ${isSubmitting ? 'Submitting...' : 'Submit Spoken Answer'}
                </button>
              </div>`
            : '<div style="color: #991b1b; font-size: 0.9rem; background: #fef2f2; padding: 14px; border-radius: 8px; border: 1px solid #fca5a5;"><strong>Microphone / Speech Recognition Unsupported:</strong> This voice-first interview requires a browser with speech recognition support (Google Chrome or Microsoft Edge). Please reopen this page in Chrome or Edge to complete your interview.</div>'
        }
      </div>
    `;

    html += `</div>`;

    this._container.innerHTML = html;
    this._attachEventListeners(snapshot);
  }

  private _attachCompletedListeners(sessionId: string): void {
    const btnViewResults = this._container.querySelector<HTMLButtonElement>('#finxl-btn-view-detailed-results');
    if (btnViewResults && this._options?.onComplete) {
      btnViewResults.addEventListener('click', () => {
        this._options?.onComplete?.(sessionId);
      });
    }
  }

  private _attachEventListeners(snapshot: VoiceInterviewSnapshot): void {
    const btnExit = this._container.querySelector<HTMLButtonElement>('#finxl-btn-exit-session');
    if (btnExit && this._options?.onExit) {
      btnExit.addEventListener('click', () => {
        this._options?.onExit?.();
      });
    }

    const btnStartMic = this._container.querySelector<HTMLButtonElement>('#finxl-btn-start-mic');
    if (btnStartMic) {
      btnStartMic.addEventListener('click', () => {
        this._lifecycle.startListening();
      });
    }

    const btnStopMic = this._container.querySelector<HTMLButtonElement>('#finxl-btn-stop-mic');
    if (btnStopMic) {
      btnStopMic.addEventListener('click', () => {
        this._lifecycle.stopListening();
      });
    }

    const btnReplay = this._container.querySelector<HTMLButtonElement>('#finxl-btn-replay-speech');
    if (btnReplay) {
      btnReplay.addEventListener('click', () => {
        this._lifecycle.speakCurrentQuestion();
      });
    }

    const btnStopSpeaking = this._container.querySelector<HTMLButtonElement>('#finxl-btn-stop-speech');
    if (btnStopSpeaking) {
      btnStopSpeaking.addEventListener('click', () => {
        this._lifecycle.stopSpeaking();
      });
    }

    const btnPlayBlocked = this._container.querySelector<HTMLButtonElement>('#finxl-btn-play-blocked');
    if (btnPlayBlocked) {
      btnPlayBlocked.addEventListener('click', () => {
        this._lifecycle.speakCurrentQuestion();
      });
    }

    const btnSubmit = this._container.querySelector<HTMLButtonElement>('#finxl-btn-submit-voice-answer');
    if (btnSubmit) {
      btnSubmit.addEventListener('click', () => {
        this._lifecycle.submitAnswer();
      });
    }

    const btnRetry = this._container.querySelector<HTMLButtonElement>('#finxl-btn-retry');
    if (btnRetry) {
      btnRetry.addEventListener('click', () => {
        this._lifecycle.retry();
      });
    }
  }

  private _escapeHtml(text: string): string {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  private _stageLabel(stage: VoiceInterviewSnapshot['stage']): string {
    const labels: Record<string, string> = {
      soft_1: 'Behavioral Interview 1',
      soft_2: 'Behavioral Interview 2',
      soft_3: 'Behavioral Interview 3',
      technical_1: 'Technical Interview 1',
      technical_2: 'Technical Interview 2',
      technical_3: 'Technical Interview 3',
    };
    return (stage ? labels[stage] : undefined) || 'Interview Stage';
  }

  private _plainQuestionText(text: string): string {
    const decoder = document.createElement('textarea');
    let decoded = text;
    for (let pass = 0; pass < 2 && /&(?:#\d+|#x[\da-f]+|[a-z]+);/i.test(decoded); pass += 1) {
      decoder.innerHTML = decoded;
      const next = decoder.value;
      if (next === decoded) break;
      decoded = next;
    }
    return decoded
      .replace(/^\s*(?:Behavioral|Technical)\s+\*{0,2}(?:soft|technical)_\d\*{0,2}\s*(?:[-—:]\s*)?/i, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/__(.*?)__/g, '$1');
  }

  private _isDevelopmentPlaceholder(text: string): boolean {
    const lowered = text.toLocaleLowerCase();
    return ['synthetic development question', 'synthetic-development-fixture', 'development question placeholder', 'fixture question']
      .some((marker) => lowered.includes(marker));
  }

  destroy(): void {
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = null;
    }
    this._container.innerHTML = '';
  }
}
