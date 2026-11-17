import { BrowserSpeechInput } from '../adapters/speech/browser-speech-input';
import { BrowserSpeechOutput } from '../adapters/speech/browser-speech-output';
import { InterviewApiClient } from '../api/interview-api-client';
import {
  AssessmentResult,
  AnswerSubmission,
  InterviewStage,
  Question,
  SkipQuestionSubmission,
  VoiceInterviewState,
} from '../types/interview';
import { SpeechInput, SpeechInputError, SpeechOutput } from '../types/speech';

export type MicrophoneState =
  | 'unknown'      // haven't tried yet
  | 'ready'        // permission granted and working
  | 'denied'       // permission denied (not-allowed error)
  | 'unavailable'  // audio-capture error — hardware issue
  | 'unsupported'; // browser doesn't support speech recognition

export interface VoiceInterviewSnapshot {
  sessionId: string;
  stage: InterviewStage | null;
  state: VoiceInterviewState;
  activeQuestion: Question | null;
  currentVersion: number;
  interimTranscript: string;
  finalTranscript: string;
  isSpeechInputSupported: boolean;
  isSpeechOutputSupported: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  isSubmitting: boolean;
  playbackBlocked: boolean;
  microphoneState: MicrophoneState;
  lastError: {
    message: string;
    code?: string;
    isRetryable: boolean;
  } | null;
  assessmentResult: AssessmentResult | null;
  isFollowUp: boolean;
}

export interface VoiceInterviewConfig {
  apiClient: InterviewApiClient;
  speechInput?: SpeechInput;
  speechOutput?: SpeechOutput;
  autoSpeakQuestions?: boolean;
  language?: string;
}

/**
 * Orchestrates the full voice interview lifecycle on the browser client,
 * coordinating SpeechInput, SpeechOutput, and the backend InterviewApiClient.
 */
export class VoiceInterviewLifecycle {
  private _apiClient: InterviewApiClient;
  private _speechInput: SpeechInput;
  private _speechOutput: SpeechOutput;
  private _autoSpeak: boolean;
  private _language: string;
  private _snapshot: VoiceInterviewSnapshot;
  private _listeners: Set<(snapshot: VoiceInterviewSnapshot) => void> = new Set();
  private _isDisposed = false;
  private _spokenQuestionIds: Set<string> = new Set();
  private _pendingSubmission: AnswerSubmission | null = null;
  private _pendingSkip: SkipQuestionSubmission | null = null;

  constructor(config: VoiceInterviewConfig) {
    this._apiClient = config.apiClient;
    this._speechInput = config.speechInput || new BrowserSpeechInput();
    this._speechOutput = config.speechOutput || new BrowserSpeechOutput();
    this._autoSpeak = config.autoSpeakQuestions ?? true;
    this._language = config.language || 'en-IN';

    this._snapshot = {
      sessionId: '',
      stage: null,
      state: 'uninitialized',
      activeQuestion: null,
      currentVersion: 0,
      interimTranscript: '',
      finalTranscript: '',
      isSpeechInputSupported: this._speechInput.isSupported(),
      isSpeechOutputSupported: this._speechOutput.isSupported(),
      isListening: false,
      isSpeaking: false,
      isSubmitting: false,
      playbackBlocked: false,
      microphoneState: !this._speechInput.isSupported() ? 'unsupported' : 'unknown',
      lastError: null,
      assessmentResult: null,
      isFollowUp: false,
    };
  }

  getSnapshot(): VoiceInterviewSnapshot {
    return { ...this._snapshot };
  }

  subscribe(listener: (snapshot: VoiceInterviewSnapshot) => void): () => void {
    this._listeners.add(listener);
    listener(this.getSnapshot());
    return () => {
      this._listeners.delete(listener);
    };
  }

  private _updateSnapshot(updates: Partial<VoiceInterviewSnapshot>): void {
    if (this._isDisposed) return;
    this._snapshot = { ...this._snapshot, ...updates };
    const copy = this.getSnapshot();
    for (const listener of this._listeners) {
      listener(copy);
    }
  }

  /**
   * Initializes the session: loads session state, active question, and speaks the question if autoSpeak is true.
   */
  async initialize(sessionId: string): Promise<void> {
    if (!sessionId) {
      throw new Error('Session ID is required');
    }

    this._updateSnapshot({
      sessionId,
      state: 'loading',
      lastError: null,
    });

    try {
      const session = await this._apiClient.getInterview(sessionId);
      this._updateSnapshot({
        stage: session.stage,
        currentVersion: session.version,
      });

      if (session.state === 'completed') {
        const assessment = await this._apiClient.getAssessment(sessionId);
        this._updateSnapshot({
          state: 'completed',
          assessmentResult: assessment,
        });
        return;
      }

      if (session.state === 'abandoned') {
        this._updateSnapshot({ state: 'abandoned' });
        return;
      }

      const question = await this._apiClient.getActiveQuestion(sessionId);
      this._updateSnapshot({
        activeQuestion: question,
        currentVersion: question.version ?? session.version,
        isFollowUp: question.kind === 'follow_up',
        state: 'question_ready',
      });

      if (this._autoSpeak && this._speechOutput.isSupported() && question.text) {
        if (!this._spokenQuestionIds.has(question.id)) {
          this._spokenQuestionIds.add(question.id);
          await this.speakCurrentQuestion();
        }
      }
    } catch (err) {
      this._handleError(err, 'Failed to initialize interview session.');
    }
  }

  /**
   * Speaks the current active question using SpeechOutput.
   */
  async speakCurrentQuestion(): Promise<void> {
    const questionText = this._snapshot.activeQuestion?.text;
    if (!questionText || !this._speechOutput.isSupported() || this._isDisposed) {
      return;
    }

    const previousState = this._snapshot.state;
    this._updateSnapshot({ isSpeaking: true, playbackBlocked: false, state: 'speaking_question' });

    try {
      await this._speechOutput.speak(questionText, this._language);
    } catch (err: any) {
      if (err?.code === 'not-allowed') {
        this._updateSnapshot({ playbackBlocked: true });
      }
    } finally {
      if (!this._isDisposed) {
        const targetState =
          previousState !== 'speaking_question'
            ? previousState
            : this._snapshot.isFollowUp
            ? 'follow_up_received'
            : 'question_ready';
        this._updateSnapshot({
          isSpeaking: false,
          state: targetState,
        });
      }
    }
  }

  /**
   * Stops current TTS speech playback.
   */
  stopSpeaking(): void {
    if (!this._snapshot.isSpeaking) return;
    this._speechOutput.stop();
    this._updateSnapshot({
      isSpeaking: false,
      state: this._snapshot.isFollowUp ? 'follow_up_received' : 'question_ready',
    });
  }

  /**
   * Starts microphone speech recognition for the current question.
   */
  async startListening(): Promise<void> {
    if (this._isDisposed) return;

    if (!this._speechInput.isSupported()) {
      this._updateSnapshot({
        lastError: {
          message: 'Speech recognition is not supported in this browser. Please use Chrome or Edge.',
          code: 'unsupported',
          isRetryable: false,
        },
      });
      return;
    }

    if (this._snapshot.isListening) {
      return;
    }

    // Stop speaking before starting microphone recognition to avoid listening to our own TTS
    this._speechOutput.stop();

    this._updateSnapshot({
      isListening: true,
      isSpeaking: false,
      interimTranscript: '',
      finalTranscript: '',
      state: 'listening',
      lastError: null,
    });

    try {
      const finalResult = await this._speechInput.start({
        language: this._language,
        continuous: true,
        interimResults: true,
        onInterimTranscript: (interim) => {
          this._updateSnapshot({
            interimTranscript: interim,
            state: 'recognizing',
          });
        },
        onFinalTranscript: (final) => {
          this._updateSnapshot({
            finalTranscript: final,
            interimTranscript: '',
          });
        },
        onError: (speechErr) => {
          this._handleSpeechError(speechErr);
        },
      });

      if (this._isDisposed) return;

      this._updateSnapshot({
        isListening: false,
        interimTranscript: '',
        finalTranscript: finalResult,
        microphoneState: 'ready',
      });
    } catch (err) {
      if (this._isDisposed) return;
      this._updateSnapshot({ isListening: false });
      if (err instanceof SpeechInputError) {
        this._handleSpeechError(err);
      } else {
        this._handleError(err, 'Microphone recognition failed.');
      }
    }
  }

  /**
   * Explicitly stops listening and finalizes recognized speech.
   */
  stopListening(): void {
    if (!this._snapshot.isListening) return;
    this._speechInput.stop();
    this._updateSnapshot({ isListening: false });
  }

  /**
   * Cancels active recognition without submitting.
   */
  cancelListening(): void {
    this._speechInput.cancel();
    this._updateSnapshot({
      isListening: false,
      interimTranscript: '',
      state: 'question_ready',
    });
  }

  /**
   * Submits recognized speech answer through the backend answer API.
   * Voice-only: requires non-empty answer text.
   */
  async submitAnswer(answerText?: string): Promise<void> {
    if (this._isDisposed) return;

    const trimmed = (answerText ?? this._snapshot.finalTranscript)?.trim();
    if (!trimmed) {
      this._updateSnapshot({
        lastError: {
          message: 'Answer cannot be empty. Please speak your response before submitting.',
          code: 'empty_answer',
          isRetryable: true,
        },
      });
      return;
    }

    const { sessionId, activeQuestion, currentVersion } = this._snapshot;
    if (!sessionId || !activeQuestion) {
      this._updateSnapshot({
        lastError: {
          message: 'No active question found to answer.',
          code: 'invalid_state',
          isRetryable: false,
        },
      });
      return;
    }

    // Stop microphone if still listening
    this._speechInput.stop();

    this._updateSnapshot({
      isSubmitting: true,
      isListening: false,
      state: 'submitting',
      lastError: null,
      finalTranscript: trimmed,
    });

    if (
      !this._pendingSubmission ||
      this._pendingSubmission.question_id !== activeQuestion.id ||
      this._pendingSubmission.text !== trimmed
    ) {
      this._pendingSkip = null;
      this._pendingSubmission = {
        question_id: activeQuestion.id,
        expected_version: currentVersion,
        idempotency_key: `voice-ans-${this._generateId()}`,
        text: trimmed,
      };
    } else {
      this._pendingSubmission = {
        ...this._pendingSubmission,
        expected_version: currentVersion,
      };
    }

    try {
      const response = await this._apiClient.submitAnswer(sessionId, this._pendingSubmission);

      if (this._isDisposed) return;

      this._updateSnapshot({
        currentVersion: response.version,
        isSubmitting: false,
      });

      if (response.action === 'complete' || response.state === 'completed') {
        const assessment = await this._apiClient.getAssessment(sessionId);
        this._updateSnapshot({
          state: 'completed',
          assessmentResult: assessment,
          interimTranscript: '',
          finalTranscript: '',
        });
        this._pendingSubmission = null;
        return;
      }

      // Next question or follow-up question
      const nextQuestion = await this._apiClient.getActiveQuestion(sessionId);
      const isFollowUp = response.action === 'follow_up' || nextQuestion.kind === 'follow_up';
      const updatedVersion = response.version ?? nextQuestion.version ?? currentVersion;

      this._updateSnapshot({
        activeQuestion: nextQuestion,
        currentVersion: updatedVersion,
        isFollowUp,
        state: isFollowUp ? 'follow_up_received' : 'question_ready',
        interimTranscript: '',
        finalTranscript: '',
      });
      this._pendingSubmission = null;

      if (this._autoSpeak && this._speechOutput.isSupported() && nextQuestion.text) {
        if (!this._spokenQuestionIds.has(nextQuestion.id)) {
          this._spokenQuestionIds.add(nextQuestion.id);
          await this.speakCurrentQuestion();
        }
      }
    } catch (err) {
      if (this._isDisposed) return;
      this._updateSnapshot({ isSubmitting: false });
      this._handleError(err, 'Failed to submit answer. Please retry.');
    }
  }

  async skipQuestion(): Promise<void> {
    if (this._isDisposed) return;
    const { sessionId, activeQuestion, currentVersion } = this._snapshot;
    if (!sessionId || !activeQuestion) {
      this._updateSnapshot({
        lastError: {
          message: 'No active question found to skip.',
          code: 'invalid_state',
          isRetryable: false,
        },
      });
      return;
    }
    this._pendingSubmission = null;
    if (this._pendingSkip?.question_id !== activeQuestion.id) {
      this._pendingSkip = {
        question_id: activeQuestion.id,
        expected_version: currentVersion,
        idempotency_key: `voice-skip-${this._generateId()}`,
      };
    }
    await this._sendPendingSkip();
  }

  private async _sendPendingSkip(): Promise<void> {
    const { sessionId } = this._snapshot;
    const pending = this._pendingSkip;
    if (!sessionId || !pending) return;
    this._speechInput.stop();
    this._speechInput.cancel();
    this._speechOutput.stop();
    this._updateSnapshot({
      isSubmitting: true,
      isListening: false,
      isSpeaking: false,
      playbackBlocked: false,
      state: 'skipping',
      lastError: null,
      interimTranscript: '',
    });
    try {
      const response = await this._apiClient.skipQuestion(sessionId, pending);
      if (this._isDisposed) return;
      this._updateSnapshot({ currentVersion: response.version, isSubmitting: false });
      if (response.action === 'complete' || response.state === 'completed') {
        const assessment = await this._apiClient.getAssessment(sessionId);
        this._pendingSkip = null;
        this._updateSnapshot({
          state: 'completed',
          assessmentResult: assessment,
          finalTranscript: '',
          interimTranscript: '',
        });
        return;
      }
      const nextQuestion = await this._apiClient.getActiveQuestion(sessionId);
      this._pendingSkip = null;
      this._updateSnapshot({
        activeQuestion: nextQuestion,
        currentVersion: response.version ?? nextQuestion.version,
        isFollowUp: nextQuestion.kind === 'follow_up',
        state: nextQuestion.kind === 'follow_up' ? 'follow_up_received' : 'question_ready',
        finalTranscript: '',
        interimTranscript: '',
      });
      if (this._autoSpeak && this._speechOutput.isSupported() && nextQuestion.text) {
        this._spokenQuestionIds.add(nextQuestion.id);
        await this.speakCurrentQuestion();
      }
    } catch (err) {
      if (this._isDisposed) return;
      this._updateSnapshot({ isSubmitting: false });
      this._handleError(err, 'Failed to skip question. Please retry.');
    }
  }

  /**
   * Safely retries the last failed action without duplicating submissions.
   */
  async retry(): Promise<void> {
    if (this._isDisposed) return;

    const { lastError, finalTranscript, sessionId, state } = this._snapshot;
    if (!lastError?.isRetryable) {
      return;
    }

    this._updateSnapshot({ lastError: null });

    if (state === 'error' && this._pendingSkip && sessionId) {
      try {
        const session = await this._apiClient.getInterview(sessionId);
        if (session.state !== 'completed' && session.state !== 'abandoned') {
          await this._apiClient.getActiveQuestion(sessionId);
          this._pendingSkip = { ...this._pendingSkip, expected_version: session.version };
          this._updateSnapshot({ currentVersion: session.version });
        }
      } catch (err) {
        this._handleError(err, 'Could not refresh the interview before retrying.');
        return;
      }
      await this._sendPendingSkip();
    } else if (state === 'error' && finalTranscript) {
      // A failed reservation is released at a newer monotonic version. Refresh
      // before retrying, while keeping the original idempotency key and answer.
      if (sessionId && this._pendingSubmission) {
        try {
          const session = await this._apiClient.getInterview(sessionId);
          if (session.state !== 'completed' && session.state !== 'abandoned') {
            const question = await this._apiClient.getActiveQuestion(sessionId);
            this._pendingSubmission = {
              ...this._pendingSubmission,
              expected_version: session.version,
            };
            this._updateSnapshot({
              activeQuestion: question,
              currentVersion: session.version,
            });
          }
        } catch (err) {
          this._handleError(err, 'Could not refresh the interview before retrying.');
          return;
        }
      }
      await this.submitAnswer(finalTranscript);
    } else if (state === 'error' && !this._snapshot.activeQuestion) {
      // Retry initialization
      await this.initialize(sessionId);
    } else {
      // Retry listening
      await this.startListening();
    }
  }

  /**
   * Resets microphone state and retries startListening.
   */
  async retryMicrophoneAccess(): Promise<void> {
    if (this._isDisposed) return;
    this._updateSnapshot({
      microphoneState: 'unknown',
      lastError: null,
    });
    await this.startListening();
  }

  private _handleSpeechError(speechErr: SpeechInputError): void {
    let userMsg = speechErr.message;
    let isRetryable = true;
    let microphoneState: MicrophoneState = 'unknown';

    if (speechErr.code === 'not-allowed') {
      userMsg = 'Microphone permission was denied. Please allow microphone access in your browser.';
      isRetryable = false;
      microphoneState = 'denied';
    } else if (speechErr.code === 'audio-capture') {
      userMsg = speechErr.message;
      isRetryable = true;
      microphoneState = 'unavailable';
    } else if (speechErr.code === 'unsupported') {
      userMsg = 'Speech recognition is not supported in this browser. Please use a supported browser (Chrome or Edge).';
      isRetryable = false;
      microphoneState = 'unsupported';
    } else if (speechErr.code === 'no-speech') {
      userMsg = 'No speech was detected. Click microphone to try speaking again.';
      isRetryable = true;
    }

    this._updateSnapshot({
      isListening: false,
      state: 'error',
      microphoneState,
      lastError: {
        message: userMsg,
        code: speechErr.code,
        isRetryable,
      },
    });
  }

  private _handleError(err: unknown, defaultMsg: string): void {
    const message = err instanceof Error ? err.message : defaultMsg;
    const isRetryable = !(message.includes('401') || message.includes('404') || message.includes('403'));

    this._updateSnapshot({
      state: 'error',
      lastError: {
        message,
        code: (err as { code?: string })?.code || 'api_error',
        isRetryable,
      },
    });
  }

  private _generateId(): string {
    return Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
  }

  /**
   * Cleanup resources on component unmount or navigation.
   */
  dispose(): void {
    this._isDisposed = true;
    this._speechOutput.stop();
    this._speechInput.cancel();
    this._listeners.clear();
  }
}
