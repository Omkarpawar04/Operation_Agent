export class MockSpeechSynthesisUtterance {
  text: string;
  lang = 'en-IN';
  rate = 1.0;
  pitch = 1.0;
  volume = 1.0;
  voice: any = null;

  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;

  constructor(text: string) {
    this.text = text;
  }
}

export class MockSpeechSynthesis {
  speaking = false;
  paused = false;
  pending = false;
  onvoiceschanged: (() => void) | null = null;

  private _voices: any[] = [
    { name: 'Google Indian English', lang: 'en-IN', default: true },
    { name: 'Google UK English Female', lang: 'en-GB', default: false },
    { name: 'Google US English', lang: 'en-US', default: false },
  ];

  activeUtterances: MockSpeechSynthesisUtterance[] = [];

  getVoices(): any[] {
    return [...this._voices];
  }

  setVoices(voices: any[]): void {
    this._voices = voices;
    if (this.onvoiceschanged) {
      this.onvoiceschanged();
    }
  }

  speak(utterance: MockSpeechSynthesisUtterance): void {
    this.activeUtterances.push(utterance);
    this.speaking = true;
    setTimeout(() => {
      utterance.onstart?.();
      setTimeout(() => {
        this.speaking = false;
        utterance.onend?.();
      }, 10);
    }, 5);
  }

  cancel(): void {
    this.speaking = false;
    for (const u of this.activeUtterances) {
      u.onerror?.({ error: 'canceled' });
    }
    this.activeUtterances = [];
  }
}
