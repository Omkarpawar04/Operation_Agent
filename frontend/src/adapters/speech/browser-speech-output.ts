import {
  SpeechOutput,
  SpeechOutputError,
  SpeechOutputErrorCode,
  SpeechOutputOptions,
} from '../../types/speech';

/**
 * Browser-native Text-to-Speech adapter using window.speechSynthesis.
 *
 * Implements the SpeechOutput port to decouple spoken question output
 * from browser implementation details.
 */
export class BrowserSpeechOutput implements SpeechOutput {
  private _currentUtterance: SpeechSynthesisUtterance | null = null;
  private _voices: SpeechSynthesisVoice[] = [];
  private _voicesLoaded = false;
  private _currentReject: ((err: SpeechOutputError) => void) | null = null;

  constructor() {
    if (this.isSupported()) {
      this._initVoices();
    }
  }

  isSupported(): boolean {
    return typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  }

  private _initVoices(): void {
    if (!this.isSupported()) {
      return;
    }
    const synth = window.speechSynthesis;
    this._voices = synth.getVoices() || [];
    synth.onvoiceschanged = () => {
      this._voices = synth.getVoices() || [];
    };
  }

  /**
   * Returns available synthesis voices.
   */
  getVoices(): SpeechSynthesisVoice[] {
    if (this.isSupported()) {
      const live = window.speechSynthesis.getVoices();
      if (live && live.length > 0) {
        this._voices = live;
      }
    }
    return this._voices;
  }

  /**
   * Finds the most suitable voice for the requested language.
   * Priority:
   * 1. Specific voiceName match if requested
   * 2. Exact language match (e.g., 'en-IN')
   * 3. Prefix language match (e.g., 'en-GB', 'en-US', 'en')
   * 4. Default voice
   * 5. First available voice
   */
  findVoice(language = 'en-IN', voiceName?: string): SpeechSynthesisVoice | null {
    const voices = this.getVoices();
    if (voices.length === 0) {
      return null;
    }

    if (voiceName) {
      const byName = voices.find((v) => v.name.toLowerCase().includes(voiceName.toLowerCase()));
      if (byName) return byName;
    }

    const langLower = language.toLowerCase();

    // 1. Exact match (e.g. 'en-in')
    const exactMatch = voices.find((v) => v.lang.toLowerCase() === langLower || v.lang.toLowerCase().replace('_', '-') === langLower);
    if (exactMatch) return exactMatch;

    // 2. Dialect fallbacks for English
    if (langLower.startsWith('en')) {
      const gbMatch = voices.find((v) => v.lang.toLowerCase().startsWith('en-gb'));
      if (gbMatch) return gbMatch;
      const usMatch = voices.find((v) => v.lang.toLowerCase().startsWith('en-us'));
      if (usMatch) return usMatch;
      const anyEn = voices.find((v) => v.lang.toLowerCase().startsWith('en'));
      if (anyEn) return anyEn;
    }

    // 3. System default voice
    const defaultVoice = voices.find((v) => v.default);
    if (defaultVoice) return defaultVoice;

    // 4. First voice fallback
    return voices[0] || null;
  }

  /**
   * Speaks the provided text and resolves when speech finishes.
   * Stops any previous speech first to prevent overlapping playback.
   */
  speak(text: string, language = 'en-IN', options?: SpeechOutputOptions): Promise<void> {
    if (!this.isSupported()) {
      return Promise.reject(
        new SpeechOutputError('Speech synthesis is not supported in this browser.', 'unsupported')
      );
    }

    const textToSpeak = text?.trim();
    if (!textToSpeak) {
      return Promise.resolve();
    }

    // Stop and cancel any existing speech to prevent overlapping voices
    this.stop();

    return new Promise<void>((resolve, reject) => {
      this._currentReject = reject;

      try {
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        this._currentUtterance = utterance;

        const lang = options?.language || language;
        utterance.lang = lang;

        const voice = this.findVoice(lang, options?.voiceName);
        if (voice) {
          utterance.voice = voice;
        }

        utterance.rate = options?.rate ?? 1.0;
        utterance.pitch = options?.pitch ?? 1.0;
        utterance.volume = options?.volume ?? 1.0;

        utterance.onend = () => {
          this._currentUtterance = null;
          this._currentReject = null;
          resolve();
        };

        utterance.onerror = (event: SpeechSynthesisErrorEvent) => {
          this._currentUtterance = null;
          this._currentReject = null;

          // 'canceled' / 'interrupted' are expected when user stops or navigates away
          if (event.error === 'canceled' || event.error === 'interrupted') {
            resolve();
            return;
          }

          let code: SpeechOutputErrorCode = 'unknown';
          switch (event.error) {
            case 'audio-busy':
              code = 'audio-busy';
              break;
            case 'not-allowed':
              code = 'not-allowed';
              break;
            default:
              code = 'synthesis-failed';
          }

          reject(new SpeechOutputError(`Speech synthesis failed: ${event.error}`, code, event));
        };

        window.speechSynthesis.speak(utterance);
      } catch (err) {
        this._currentUtterance = null;
        this._currentReject = null;
        reject(
          new SpeechOutputError(
            'Failed to start speech synthesis: ' + (err instanceof Error ? err.message : String(err)),
            'unknown',
            err
          )
        );
      }
    });
  }

  /**
   * Cancels active speech output immediately.
   */
  stop(): void {
    if (!this.isSupported()) {
      return;
    }
    if (this._currentReject) {
      // Resolve cleanly on manual stop
      this._currentReject = null;
    }
    this._currentUtterance = null;
    try {
      window.speechSynthesis.cancel();
    } catch {
      // Ignore if cancel fails
    }
  }
}
