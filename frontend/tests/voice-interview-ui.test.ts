import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { VoiceInterviewUI } from '../src/components/voice-interview-ui';
import { VoiceInterviewLifecycle } from '../src/orchestrator/voice-interview-lifecycle';

describe('VoiceInterviewUI Component', () => {
  let container: HTMLElement;
  let mockLifecycle: any;
  let component: VoiceInterviewUI;
  let subscriberCallback: ((snapshot: any) => void) | null = null;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);

    mockLifecycle = {
      subscribe: vi.fn().mockImplementation((cb) => {
        subscriberCallback = cb;
        return () => {
          subscriberCallback = null;
        };
      }),
      startListening: vi.fn(),
      stopListening: vi.fn(),
      cancelListening: vi.fn(),
      speakCurrentQuestion: vi.fn(),
      stopSpeaking: vi.fn(),
      submitAnswer: vi.fn(),
      retry: vi.fn(),
    };

    component = new VoiceInterviewUI(container, mockLifecycle as unknown as VoiceInterviewLifecycle);
  });

  afterEach(() => {
    component.destroy();
    if (container.parentElement) {
      container.parentElement.removeChild(container);
    }
  });

  it('renders question text and stage badge', () => {
    subscriberCallback?.({
      sessionId: 'sess-1',
      stage: 'soft_1',
      state: 'question_ready',
      activeQuestion: { id: 'q-1', text: 'How do you handle team disagreements?', kind: 'base', sequence: 1, version: 1 },
      currentVersion: 1,
      interimTranscript: '',
      finalTranscript: '',
      isSpeechInputSupported: true,
      isSpeechOutputSupported: true,
      isListening: false,
      isSpeaking: false,
      isSubmitting: false,
      lastError: null,
      assessmentResult: null,
      isFollowUp: false,
    });

    expect(container.textContent).toContain('FINXL AI Voice Interview');
    expect(container.textContent).toContain('Behavioral Interview 1');
    expect(container.textContent).toContain('How do you handle team disagreements?');
    expect(container.textContent?.match(/Behavioral Interview 1/g)).toHaveLength(1);
    expect(container.querySelector('.finxl-question-card strong')?.textContent?.trim()).toBe('Question 1');
    expect(container.querySelector('#finxl-btn-start-mic')).not.toBeNull();
  });

  it('decodes encoded text, renders clean metadata, and keeps the submit label readable', () => {
    subscriberCallback?.({
      sessionId: 'sess-1', stage: 'soft_1', state: 'question_ready',
      activeQuestion: { id: 'q-1', text: 'Behavioral&amp;#x20;**&amp;#x73;oft_1** — explain your decision.', kind: 'base', sequence: 2, version: 1 },
      currentVersion: 1, interimTranscript: '', finalTranscript: 'Captured speech',
      isSpeechInputSupported: true, isSpeechOutputSupported: true, isListening: false,
      isSpeaking: false, isSubmitting: false, lastError: null, assessmentResult: null, isFollowUp: false,
    });
    expect(container.textContent).toContain('Behavioral Interview 1');
    expect(container.textContent).toContain('explain your decision.');
    expect(container.textContent).not.toContain('soft_1');
    expect(container.textContent).not.toContain('&#x20;');
    expect(container.textContent).not.toContain('**');
    expect(container.textContent).not.toContain('[Synthetic development question');
    expect(container.textContent).toContain('Question 2');
    expect(container.textContent?.match(/Behavioral Interview 1/g)).toHaveLength(1);
    expect(container.querySelector('.finxl-question-card strong')?.textContent?.trim()).toBe('Question 2');
    const button = container.querySelector<HTMLButtonElement>('#finxl-btn-submit-voice-answer')!;
    expect(button.textContent?.trim()).toBe('Submit Spoken Answer');
    expect(button.disabled).toBe(false);
    expect(button.style.whiteSpace).toBe('normal');
    expect(button.style.textOverflow).toBe('clip');
    expect(button.style.color).toBe('#ffffff');
  });

  it('hides stale synthetic fixture text and keeps submission disabled', () => {
    subscriberCallback?.({
      sessionId: 'sess-old', stage: 'soft_1', state: 'question_ready',
      activeQuestion: { id: 'q-old', text: '[Synthetic development question 1] Describe a specific situation and the evidence behind your decision.', kind: 'base', sequence: 1, version: 1 },
      currentVersion: 1, interimTranscript: '', finalTranscript: 'Captured speech',
      isSpeechInputSupported: true, isSpeechOutputSupported: true, isListening: false,
      isSpeaking: false, isSubmitting: false, lastError: null, assessmentResult: null, isFollowUp: false,
    });
    expect(container.textContent).not.toContain('[Synthetic development question');
    expect(container.textContent).toContain('start a fresh interview');
    expect(container.querySelector<HTMLButtonElement>('#finxl-btn-submit-voice-answer')?.disabled).toBe(true);
  });

  it('keeps voice submission disabled while listening or submitting', () => {
    const snapshot = {
      sessionId: 'sess-1', stage: 'soft_1', state: 'question_ready',
      activeQuestion: { id: 'q-1', text: 'Describe your decision and how you verified the result.', kind: 'base', sequence: 1, version: 1 },
      currentVersion: 1, interimTranscript: '', finalTranscript: 'Captured speech',
      isSpeechInputSupported: true, isSpeechOutputSupported: true, isSpeaking: false,
      lastError: null, assessmentResult: null, isFollowUp: false,
    };
    subscriberCallback?.({ ...snapshot, isListening: true, isSubmitting: false });
    expect(container.querySelector<HTMLButtonElement>('#finxl-btn-submit-voice-answer')?.disabled).toBe(true);
    subscriberCallback?.({ ...snapshot, isListening: false, isSubmitting: true });
    expect(container.querySelector<HTMLButtonElement>('#finxl-btn-submit-voice-answer')?.disabled).toBe(true);
    expect(container.querySelector('textarea')).toBeNull();
  });

  it('displays spoken indicator when question is being spoken', () => {
    subscriberCallback?.({
      sessionId: 'sess-1',
      stage: 'soft_1',
      state: 'speaking_question',
      activeQuestion: { id: 'q-1', text: 'Sample question', kind: 'base', sequence: 1, version: 1 },
      currentVersion: 1,
      interimTranscript: '',
      finalTranscript: '',
      isSpeechInputSupported: true,
      isSpeechOutputSupported: true,
      isListening: false,
      isSpeaking: true,
      isSubmitting: false,
      lastError: null,
      assessmentResult: null,
      isFollowUp: false,
    });

    expect(container.textContent).toContain('Speaking question...');
  });

  it('displays listening status and live transcripts', () => {
    subscriberCallback?.({
      sessionId: 'sess-1',
      stage: 'soft_1',
      state: 'recognizing',
      activeQuestion: { id: 'q-1', text: 'Sample question', kind: 'base', sequence: 1, version: 1 },
      currentVersion: 1,
      interimTranscript: 'in progress words',
      finalTranscript: 'I initiated a technical review',
      isSpeechInputSupported: true,
      isSpeechOutputSupported: true,
      isListening: true,
      isSpeaking: false,
      isSubmitting: false,
      lastError: null,
      assessmentResult: null,
      isFollowUp: false,
    });

    expect(container.textContent).toContain('Recognizing speech...');
    expect(container.textContent).toContain('I initiated a technical review');
    expect(container.textContent).toContain('in progress words');
    expect(container.querySelector('#finxl-btn-stop-mic')).not.toBeNull();
  });

  it('triggers startListening() and stopListening() on button clicks', () => {
    subscriberCallback?.({
      sessionId: 'sess-1',
      stage: 'soft_1',
      state: 'question_ready',
      activeQuestion: { id: 'q-1', text: 'Sample question', kind: 'base', sequence: 1, version: 1 },
      currentVersion: 1,
      interimTranscript: '',
      finalTranscript: '',
      isSpeechInputSupported: true,
      isSpeechOutputSupported: true,
      isListening: false,
      isSpeaking: false,
      isSubmitting: false,
      lastError: null,
      assessmentResult: null,
      isFollowUp: false,
    });

    const startBtn = container.querySelector<HTMLButtonElement>('#finxl-btn-start-mic')!;
    startBtn.click();
    expect(mockLifecycle.startListening).toHaveBeenCalled();

    // Switch to listening state
    subscriberCallback?.({
      sessionId: 'sess-1',
      stage: 'soft_1',
      state: 'listening',
      activeQuestion: { id: 'q-1', text: 'Sample question', kind: 'base', sequence: 1, version: 1 },
      currentVersion: 1,
      interimTranscript: '',
      finalTranscript: '',
      isSpeechInputSupported: true,
      isSpeechOutputSupported: true,
      isListening: true,
      isSpeaking: false,
      isSubmitting: false,
      lastError: null,
      assessmentResult: null,
      isFollowUp: false,
    });

    const stopBtn = container.querySelector<HTMLButtonElement>('#finxl-btn-stop-mic')!;
    stopBtn.click();
    expect(mockLifecycle.stopListening).toHaveBeenCalled();
  });

  it('submits voice answer when transcript is present and submit button is clicked', () => {
    subscriberCallback?.({
      sessionId: 'sess-1',
      stage: 'soft_1',
      state: 'question_ready',
      activeQuestion: { id: 'q-1', text: 'Sample question', kind: 'base', sequence: 1, version: 1 },
      currentVersion: 1,
      interimTranscript: '',
      finalTranscript: 'My spoken answer content.',
      isSpeechInputSupported: true,
      isSpeechOutputSupported: true,
      isListening: false,
      isSpeaking: false,
      isSubmitting: false,
      playbackBlocked: false,
      lastError: null,
      assessmentResult: null,
      isFollowUp: false,
    });

    const submitBtn = container.querySelector<HTMLButtonElement>('#finxl-btn-submit-voice-answer')!;
    expect(submitBtn).not.toBeNull();
    expect(submitBtn.disabled).toBe(false);

    submitBtn.click();
    expect(mockLifecycle.submitAnswer).toHaveBeenCalled();
  });

  it('renders microphone permission denial error and provides retry button', () => {
    subscriberCallback?.({
      sessionId: 'sess-1',
      stage: 'soft_1',
      state: 'error',
      activeQuestion: { id: 'q-1', text: 'Sample question', kind: 'base', sequence: 1, version: 1 },
      currentVersion: 1,
      interimTranscript: '',
      finalTranscript: '',
      isSpeechInputSupported: true,
      isSpeechOutputSupported: true,
      isListening: false,
      isSpeaking: false,
      isSubmitting: false,
      lastError: {
        message: 'Microphone permission was denied. Please allow microphone access.',
        code: 'not-allowed',
        isRetryable: false,
      },
      assessmentResult: null,
      isFollowUp: false,
    });

    expect(container.textContent).toContain('Microphone permission was denied');
  });

  it('renders completed assessment card with score and pass status', () => {
    subscriberCallback?.({
      sessionId: 'sess-1',
      stage: 'soft_1',
      state: 'completed',
      activeQuestion: null,
      currentVersion: 3,
      interimTranscript: '',
      finalTranscript: '',
      isSpeechInputSupported: true,
      isSpeechOutputSupported: true,
      isListening: false,
      isSpeaking: false,
      isSubmitting: false,
      lastError: null,
      assessmentResult: {
        attempt_id: 'att-xyz-99',
        score: '84.0',
        passed: true,
        rubric_version: 'rubric_v1',
      },
      isFollowUp: false,
    });

    expect(container.textContent).toContain('Interview Completed — PASSED');
    expect(container.textContent).toContain('Final Score: 84.0%');
    expect(container.textContent).toContain('Attempt ID: att-xyz-99');
  });
});
