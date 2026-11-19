import { VoiceInterviewLifecycle, VoiceInterviewSnapshot } from '../orchestrator/voice-interview-lifecycle';
import { NeuralOrbState, renderNeuralOrb } from './neural-orb';
import { renderLiveTranscriptionPanel } from './live-transcription-panel';

export interface VoiceInterviewUIOptions {
  onComplete?: (sessionId: string) => void;
  onExit?: () => void;
}

/** Production voice interview studio. All displayed interview content comes from lifecycle snapshots. */
export class VoiceInterviewUI {
  private _container: HTMLElement;
  private _lifecycle: VoiceInterviewLifecycle;
  private _options?: VoiceInterviewUIOptions;
  private _unsubscribe: (() => void) | null = null;

  constructor(container: HTMLElement, lifecycle: VoiceInterviewLifecycle, options?: VoiceInterviewUIOptions) {
    this._container = container;
    this._lifecycle = lifecycle;
    this._options = options;
    this._unsubscribe = lifecycle.subscribe((snapshot) => this._render(snapshot));
  }

  private _render(snapshot: VoiceInterviewSnapshot): void {
    const {
      sessionId, state, stage, activeQuestion, isSpeaking, isListening, isSubmitting, playbackBlocked,
      interimTranscript, finalTranscript, lastError, assessmentResult, isSpeechInputSupported,
      isSpeechOutputSupported, microphoneState, spokenCharIndex = 0,
    } = snapshot;

    if (state === 'completed' && assessmentResult) {
      this._container.innerHTML = `<article class="finxl-voice-interview completion-view">
        <section class="finxl-completed-card" aria-labelledby="completion-title">
          <span class="question-index">ASSESSMENT COMPLETE</span>
          <h1 id="completion-title">${assessmentResult.passed ? 'Stage passed' : 'Stage not passed'}</h1>
          <p class="completion-score">${this._escapeHtml(String(assessmentResult.score))}<span>/100</span></p>
          <p>Attempt ${this._escapeHtml(assessmentResult.attempt_id)} · Rubric ${this._escapeHtml(assessmentResult.rubric_version)}</p>
          ${this._options?.onComplete ? '<button type="button" id="finxl-btn-view-detailed-results" class="btn-primary">View detailed results</button>' : ''}
        </section>
      </article>`;
      this._container.querySelector('#finxl-btn-view-detailed-results')?.addEventListener('click', () => this._options?.onComplete?.(sessionId));
      return;
    }

    if (state === 'abandoned') {
      this._container.innerHTML = `<article class="finxl-voice-interview completion-view"><section class="finxl-completed-card">
        <span class="question-index">SESSION CLOSED</span><h1>Interview session abandoned</h1>
        <p>This session can no longer accept answers.</p>
        ${this._options?.onExit ? '<button type="button" id="finxl-btn-abandoned-exit" class="btn-secondary">Return to dashboard</button>' : ''}
      </section></article>`;
      this._container.querySelector('#finxl-btn-abandoned-exit')?.addEventListener('click', () => this._options?.onExit?.());
      return;
    }

    const orbState = this._orbState(snapshot);
    const safeQuestion = Boolean(activeQuestion && !this._isDevelopmentPlaceholder(activeQuestion.text));
    const displayQuestion = activeQuestion ? this._plainQuestionText(activeQuestion.text) : '';
    const questionText = safeQuestion
      ? this._karaokeText(displayQuestion, spokenCharIndex, isSpeaking)
      : state === 'loading' || state === 'uninitialized'
        ? 'Preparing your interview question…'
        : 'This question is unavailable. Please start a fresh interview.';
    const questionIndex = activeQuestion && Number.isInteger(activeQuestion.sequence) && activeQuestion.sequence > 0
      ? `QUESTION ${activeQuestion.sequence}`
      : activeQuestion?.kind === 'follow_up' || activeQuestion?.kind === 'clarification' ? 'FOLLOW-UP QUESTION' : 'CURRENT QUESTION';

    this._container.innerHTML = `<article class="finxl-voice-interview" data-orb-state="${orbState}">
      <section class="studio-question" aria-labelledby="studio-question-title">
        <div class="question-overline"><span>FINXL AI INTERVIEW STUDIO</span><span>${this._stageLabel(stage)}</span></div>
        <div class="question-index">${questionIndex}</div>
        <h1 id="studio-question-title" class="finxl-question-text">${questionText}</h1>
        <div class="question-actions">
          ${isSpeechOutputSupported ? '<button type="button" id="finxl-btn-replay-speech" class="btn-secondary" aria-label="Replay question audio"' + (isSubmitting || !safeQuestion ? ' disabled' : '') + '>Replay Audio</button>' : ''}
          <button type="button" id="finxl-btn-skip-question" class="btn-secondary"${isSubmitting || !safeQuestion ? ' disabled' : ''}>${isSubmitting && state === 'skipping' ? 'Skipping…' : activeQuestion?.kind === 'follow_up' || activeQuestion?.kind === 'clarification' ? 'Skip Follow-up' : 'Skip Question'}</button>
          ${this._options?.onExit ? '<button type="button" id="finxl-btn-exit-session" class="studio-exit">Exit interview</button>' : ''}
        </div>
        ${playbackBlocked ? '<p class="playback-notice" role="status">Audio playback was blocked. Select Replay Audio to try again.</p>' : ''}
      </section>

      <section class="studio-workspace" aria-label="Interview workspace">
        ${renderNeuralOrb(orbState)}
        ${renderLiveTranscriptionPanel({ finalTranscript, interimTranscript, listening: isListening, supported: isSpeechInputSupported, microphoneState })}
      </section>

      ${lastError ? `<div class="finxl-error-banner" role="alert"><span>${this._escapeHtml(lastError.message)}</span>${lastError.isRetryable ? '<button type="button" id="finxl-btn-retry" class="btn-secondary">Retry</button>' : ''}</div>` : ''}
      ${this._microphoneNotice(microphoneState)}

      <section class="finxl-voice-controls" aria-label="Interview controls">
        <button type="button" id="finxl-btn-start-mic" class="btn-primary"${!isSpeechInputSupported || isListening || isSubmitting || !safeQuestion ? ' disabled' : ''}>${finalTranscript ? 'Start Voice Answer Again' : 'Start Voice Answer'}</button>
        <button type="button" id="finxl-btn-stop-mic" class="btn-secondary"${!isListening || isSubmitting ? ' disabled' : ''}>Stop Recording</button>
        <button type="button" id="finxl-btn-submit-voice-answer" class="btn-primary submit-answer"${isSubmitting || isListening || !finalTranscript.trim() || !safeQuestion ? ' disabled' : ''}>${isSubmitting ? state === 'skipping' ? 'Skipping…' : 'Submitting…' : 'Submit Spoken Answer'}</button>
        <button type="button" id="finxl-btn-stop-speech" class="btn-secondary"${!isSpeechOutputSupported || !isSpeaking ? ' disabled' : ''}>Stop Audio</button>
      </section>
      ${!isSpeechInputSupported ? '<p class="speech-unsupported" role="status">Speech recognition is unavailable in this browser. Use a supported browser such as Chrome or Edge.</p>' : ''}
    </article>`;

    const transcript = this._container.querySelector<HTMLElement>('.transcript-content');
    if (transcript) transcript.scrollTop = transcript.scrollHeight;
    this._attachEventListeners();
  }

  private _orbState(snapshot: VoiceInterviewSnapshot): NeuralOrbState {
    if (snapshot.state === 'loading' || snapshot.state === 'uninitialized') return 'idle';
    if (snapshot.state === 'error' || snapshot.lastError) return 'error';
    if (snapshot.isSubmitting) return 'processing';
    if (snapshot.isListening) return 'listening';
    if (snapshot.isSpeaking) return 'speaking';
    return 'ready';
  }

  private _microphoneNotice(state: VoiceInterviewSnapshot['microphoneState']): string {
    if (state === 'denied') return '<div class="microphone-notice" role="alert"><span>Microphone access was denied. Allow microphone access in your browser, then retry.</span><button type="button" id="finxl-btn-retry-mic" class="btn-secondary">Retry microphone</button></div>';
    if (state === 'unavailable') return '<div class="microphone-notice" role="alert"><span>No microphone is available. Connect or enable a microphone, then retry.</span><button type="button" id="finxl-btn-retry-mic" class="btn-secondary">Retry microphone</button></div>';
    if (state === 'unsupported') return '<p class="microphone-notice" role="status">This browser does not support speech recognition.</p>';
    return '';
  }

  private _attachEventListeners(): void {
    this._container.querySelector('#finxl-btn-exit-session')?.addEventListener('click', () => this._options?.onExit?.());
    this._container.querySelector('#finxl-btn-start-mic')?.addEventListener('click', () => this._lifecycle.startListening());
    this._container.querySelector('#finxl-btn-retry-mic')?.addEventListener('click', () => this._lifecycle.retryMicrophoneAccess());
    this._container.querySelector('#finxl-btn-stop-mic')?.addEventListener('click', () => this._lifecycle.stopListening());
    this._container.querySelector('#finxl-btn-replay-speech')?.addEventListener('click', () => this._lifecycle.speakCurrentQuestion());
    this._container.querySelector('#finxl-btn-stop-speech')?.addEventListener('click', () => this._lifecycle.stopSpeaking());
    this._container.querySelector('#finxl-btn-submit-voice-answer')?.addEventListener('click', () => this._lifecycle.submitAnswer());
    this._container.querySelector('#finxl-btn-skip-question')?.addEventListener('click', () => this._lifecycle.skipQuestion());
    this._container.querySelector('#finxl-btn-retry')?.addEventListener('click', () => this._lifecycle.retry());
  }

  private _escapeHtml(text: string): string {
    if (!text) return '';
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  private _karaokeText(text: string, charIndex: number, isSpeaking: boolean): string {
    let cursor = 0;
    return text.split(/(\s+)/).map((part) => {
      const start = cursor;
      cursor += part.length;
      if (/^\s+$/.test(part)) return this._escapeHtml(part);
      const active = isSpeaking && start <= charIndex && charIndex < cursor;
      const spoken = isSpeaking && cursor <= charIndex;
      return `<span class="karaoke-word${active ? ' is-active' : ''}${spoken ? ' is-spoken' : ''}">${this._escapeHtml(part)}</span>`;
    }).join('');
  }

  private _stageLabel(stage: VoiceInterviewSnapshot['stage']): string {
    const labels: Record<string, string> = {
      soft_1: 'Behavioral Interview 1', soft_2: 'Behavioral Interview 2', soft_3: 'Behavioral Interview 3',
      technical_1: 'Technical Interview 1', technical_2: 'Technical Interview 2', technical_3: 'Technical Interview 3',
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
      .replace(/^\s*(?:Behavioral|Technical)\s+\*{0,2}(?:soft|technical)_\d\*{0,2}\s*(?:[-–—:]\s*)?/i, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/__(.*?)__/g, '$1');
  }

  private _isDevelopmentPlaceholder(text: string): boolean {
    const lowered = text.toLocaleLowerCase();
    return ['synthetic development question', 'synthetic-development-fixture', 'development question placeholder', 'fixture question']
      .some((marker) => lowered.includes(marker));
  }

  destroy(): void {
    this._unsubscribe?.();
    this._unsubscribe = null;
    this._container.innerHTML = '';
  }
}
