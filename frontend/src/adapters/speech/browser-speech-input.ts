import {
  SpeechInput,
  SpeechInputError,
  SpeechInputErrorCode,
  SpeechInputOptions,
  SpeechInputState,
} from '../../types/speech';

// Type declarations for the W3C Web Speech API SpeechRecognition
interface SpeechRecognitionEventLike extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultListLike;
}

interface SpeechRecognitionResultListLike {
  readonly length: number;
  item(index: number): SpeechRecognitionResultLike;
  [index: number]: SpeechRecognitionResultLike;
}

interface SpeechRecognitionResultLike {
  readonly isFinal: boolean;
  readonly length: number;
  item(index: number): SpeechRecognitionAlternativeLike;
  [index: number]: SpeechRecognitionAlternativeLike;
}

interface SpeechRecognitionAlternativeLike {
  readonly transcript: string;
  readonly confidence: number;
}

interface SpeechRecognitionErrorEventLike extends Event {
  readonly error: string;
  readonly message?: string;
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onstart: ((this: SpeechRecognitionInstance, ev: Event) => void) | null;
  onend: ((this: SpeechRecognitionInstance, ev: Event) => void) | null;
  onerror: ((this: SpeechRecognitionInstance, ev: SpeechRecognitionErrorEventLike) => void) | null;
  onresult: ((this: SpeechRecognitionInstance, ev: SpeechRecognitionEventLike) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionInstance;
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

/**
 * Browser-native Speech-to-Text adapter using the Web Speech API (SpeechRecognition / webkitSpeechRecognition).
 *
 * Implements the SpeechInput port to keep interview orchestration decoupled
 * from browser implementation details.
 */
export class BrowserSpeechInput implements SpeechInput {
  private _recognition: SpeechRecognitionInstance | null = null;
  private _state: SpeechInputState = 'inactive';
  private _isCanceled = false;
  private _isStopping = false;
  private _resolve: ((transcript: string) => void) | null = null;
  private _reject: ((error: SpeechInputError) => void) | null = null;
  private _finalTranscriptSegments: string[] = [];
  private _options: SpeechInputOptions | null = null;

  /**
   * Checks whether the current browser environment provides Web Speech Recognition.
   */
  isSupported(): boolean {
    if (typeof window === 'undefined') {
      return false;
    }
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  /**
   * Returns current input state.
   */
  getState(): SpeechInputState {
    return this._state;
  }

  private _setState(newState: SpeechInputState): void {
    if (this._state !== newState) {
      this._state = newState;
      this._options?.onStateChange?.(newState);
    }
  }

  private _getConstructor(): SpeechRecognitionConstructor | null {
    if (typeof window === 'undefined') {
      return null;
    }
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }

  /**
   * Starts speech recognition and returns a Promise that resolves with the final recognized transcript.
   */
  start(options?: SpeechInputOptions): Promise<string> {
    const RecognitionCtor = this._getConstructor();
    if (!RecognitionCtor) {
      const err = new SpeechInputError(
        'Speech recognition is not supported in this browser.',
        'unsupported'
      );
      options?.onError?.(err);
      return Promise.reject(err);
    }

    if (this._state !== 'inactive') {
      const err = new SpeechInputError(
        'A speech recognition session is already active.',
        'already-active'
      );
      options?.onError?.(err);
      return Promise.reject(err);
    }

    this._options = options || {};
    this._finalTranscriptSegments = [];
    this._isCanceled = false;
    this._isStopping = false;
    this._setState('starting');

    return new Promise<string>((resolve, reject) => {
      this._resolve = resolve;
      this._reject = reject;

      try {
        const recognition = new RecognitionCtor();
        this._recognition = recognition;

        recognition.continuous = options?.continuous ?? true;
        recognition.interimResults = options?.interimResults ?? true;
        recognition.lang = options?.language || 'en-IN';

        recognition.onstart = () => {
          this._setState('listening');
        };

        recognition.onresult = (event: SpeechRecognitionEventLike) => {
          let interimText = '';

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const res = event.results[i];
            const transcript = res[0]?.transcript || '';

            if (res.isFinal) {
              const trimmed = transcript.trim();
              if (trimmed) {
                this._finalTranscriptSegments.push(trimmed);
                const fullFinal = this._finalTranscriptSegments.join(' ');
                this._options?.onFinalTranscript?.(fullFinal);
              }
            } else {
              interimText += transcript;
            }
          }

          if (interimText.trim()) {
            this._setState('recognizing');
            this._options?.onInterimTranscript?.(interimText.trim());
          }
        };

        recognition.onerror = (event: SpeechRecognitionErrorEventLike) => {
          const rawError = event.error;
          let code: SpeechInputErrorCode = 'unknown';
          let message = `Speech recognition error: ${rawError}`;

          switch (rawError) {
            case 'not-allowed':
            case 'permission-denied':
              code = 'not-allowed';
              message = 'Microphone permission was denied. Please allow microphone access.';
              break;
            case 'no-speech':
              code = 'no-speech';
              message = 'No speech was detected. Please check your microphone and speak clearly.';
              break;
            case 'network':
              code = 'network';
              message = 'Speech recognition service network error occurred.';
              break;
            case 'audio-capture':
              code = 'audio-capture';
              message = 'Audio capture failed. Ensure a microphone is connected and working.';
              break;
            case 'aborted':
              code = 'aborted';
              message = 'Speech recognition was aborted.';
              break;
            default:
              code = 'unknown';
              message = event.message || `Speech recognition error (${rawError}).`;
          }

          // If canceled intentionally by student, do not trigger error callbacks
          if (this._isCanceled && code === 'aborted') {
            return;
          }

          const error = new SpeechInputError(message, code, event);
          this._options?.onError?.(error);

          if (this._reject) {
            const rej = this._reject;
            this._cleanup();
            rej(error);
          }
        };

        recognition.onend = () => {
          this._handleSessionEnd();
        };

        recognition.start();
      } catch (err) {
        const error = new SpeechInputError(
          'Failed to initialize speech recognition: ' + (err instanceof Error ? err.message : String(err)),
          'unknown',
          err
        );
        this._options?.onError?.(error);
        this._cleanup();
        reject(error);
      }
    });
  }

  private _handleSessionEnd(): void {
    if (this._isCanceled) {
      if (this._reject) {
        const rej = this._reject;
        this._cleanup();
        rej(new SpeechInputError('Speech recognition was canceled.', 'aborted'));
      } else {
        this._cleanup();
      }
      return;
    }

    const finalTranscript = this._finalTranscriptSegments.join(' ').trim();

    if (!finalTranscript) {
      if (this._reject) {
        const rej = this._reject;
        this._cleanup();
        rej(new SpeechInputError('No speech was recognized. Answer cannot be empty.', 'empty-transcript'));
      } else {
        this._cleanup();
      }
      return;
    }

    if (this._resolve) {
      const res = this._resolve;
      this._cleanup();
      res(finalTranscript);
    } else {
      this._cleanup();
    }
  }

  /**
   * Explicitly stop recognition and return the accumulated final transcript.
   */
  stop(): void {
    if (this._state === 'inactive' || !this._recognition) {
      return;
    }
    this._isStopping = true;
    this._setState('stopping');
    try {
      this._recognition.stop();
    } catch {
      // Ignore if already stopped
    }
  }

  /**
   * Immediately cancels active recognition without producing an answer transcript.
   */
  cancel(): void {
    if (this._state === 'inactive' || !this._recognition) {
      return;
    }
    this._isCanceled = true;
    try {
      this._recognition.abort();
    } catch {
      // Ignore if already inactive
    }
    this._handleSessionEnd();
  }

  private _cleanup(): void {
    if (this._recognition) {
      this._recognition.onstart = null;
      this._recognition.onend = null;
      this._recognition.onerror = null;
      this._recognition.onresult = null;
      this._recognition = null;
    }
    this._resolve = null;
    this._reject = null;
    this._isCanceled = false;
    this._isStopping = false;
    this._setState('inactive');
  }
}
