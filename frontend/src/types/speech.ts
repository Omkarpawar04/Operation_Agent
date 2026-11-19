/**
 * Provider-independent speech abstractions for FINXL AI Interviewer.
 *
 * Designed to isolate speech recognition (STT) and speech synthesis (TTS)
 * so browser Web Speech, cloud services (Google Cloud, Azure, AWS), or local
 * models (Whisper) can be plugged in without mutating interview orchestration.
 */

export type SpeechInputState =
  | 'inactive'
  | 'starting'
  | 'listening'
  | 'recognizing'
  | 'stopping';

export type SpeechInputErrorCode =
  | 'not-allowed'
  | 'no-speech'
  | 'network'
  | 'audio-capture'
  | 'aborted'
  | 'unsupported'
  | 'already-active'
  | 'empty-transcript'
  | 'unknown';

export class SpeechInputError extends Error {
  readonly code: SpeechInputErrorCode;
  readonly originalError?: unknown;

  constructor(message: string, code: SpeechInputErrorCode, originalError?: unknown) {
    super(message);
    this.name = 'SpeechInputError';
    this.code = code;
    this.originalError = originalError;
  }
}

export interface SpeechInputOptions {
  /**
   * BCP 47 language tag, e.g. 'en-IN', 'en-US', 'en-GB'. Defaults to 'en-IN'.
   */
  language?: string;

  /**
   * Whether to keep recognizing continuously or stop after one final utterance.
   */
  continuous?: boolean;

  /**
   * Whether to fire callbacks for interim (in-progress) speech recognition.
   */
  interimResults?: boolean;

  /**
   * Real-time callback for interim transcript fragments. Never submitted as answers.
   */
  onInterimTranscript?: (interim: string) => void;

  /**
   * Callback fired when a final transcript segment is recognized.
   */
  onFinalTranscript?: (final: string) => void;

  /**
   * Callback fired when an error occurs during recognition.
   */
  onError?: (error: SpeechInputError) => void;

  /**
   * Callback fired on recognition lifecycle state changes.
   */
  onStateChange?: (state: SpeechInputState) => void;
}

/**
 * Replaceable speech-to-text port.
 * Implemented by BrowserSpeechInput, CloudSTTAdapter, WhisperSTTAdapter, etc.
 */
export interface SpeechInput {
  /**
   * Returns true if the underlying speech recognition mechanism is supported in the current environment.
   */
  isSupported(): boolean;

  /**
   * Starts speech recognition and resolves with the final recognized transcript text.
   * Rejects if recognition fails, permission is denied, or no speech is detected.
   */
  start(options?: SpeechInputOptions): Promise<string>;

  /**
   * Explicitly stops listening and finalizes the accumulated transcript.
   */
  stop(): void;

  /**
   * Aborts active recognition without yielding a transcript.
   */
  cancel(): void;
}

export type SpeechOutputErrorCode =
  | 'canceled'
  | 'interrupted'
  | 'audio-busy'
  | 'not-allowed'
  | 'unsupported'
  | 'synthesis-failed'
  | 'unknown';

export class SpeechOutputError extends Error {
  readonly code: SpeechOutputErrorCode;
  readonly originalError?: unknown;

  constructor(message: string, code: SpeechOutputErrorCode, originalError?: unknown) {
    super(message);
    this.name = 'SpeechOutputError';
    this.code = code;
    this.originalError = originalError;
  }
}

export interface SpeechOutputOptions {
  /**
   * Preferred voice language tag (e.g., 'en-IN', 'en-GB', 'en-US').
   */
  language?: string;

  /**
   * Speaking rate (0.1 to 10, default 1.0).
   */
  rate?: number;

  /**
   * Speaking pitch (0 to 2, default 1.0).
   */
  pitch?: number;

  /**
   * Speaking volume (0 to 1, default 1.0).
   */
  volume?: number;

  /**
   * Optional voice name to match (exact or substring).
   */
  voiceName?: string;

  /** Browser speech boundary offset, when the engine supplies word events. */
  onBoundary?: (charIndex: number) => void;
}

/**
 * Replaceable text-to-speech port.
 * Implemented by BrowserSpeechOutput, CloudTTSAdapter, GeminiTTSAdapter, etc.
 */
export interface SpeechOutput {
  /**
   * Returns true if speech synthesis is supported in the current environment.
   */
  isSupported(): boolean;

  /**
   * Speaks the provided text and resolves when speech finishes.
   * Cancels any previously ongoing speech to prevent overlap.
   */
  speak(text: string, language?: string, options?: SpeechOutputOptions): Promise<void>;

  /**
   * Stops any currently active or queued speech immediately.
   */
  stop(): void;
}
