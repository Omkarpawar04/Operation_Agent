export class MockSpeechRecognition {
  continuous = true;
  interimResults = true;
  lang = 'en-IN';
  maxAlternatives = 1;

  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error: string; message?: string }) => void) | null = null;
  onresult: ((event: any) => void) | null = null;

  static instances: MockSpeechRecognition[] = [];

  constructor() {
    MockSpeechRecognition.instances.push(this);
  }

  start(): void {
    if (this.onstart) {
      setTimeout(() => this.onstart?.(), 0);
    }
  }

  stop(): void {
    if (this.onend) {
      setTimeout(() => this.onend?.(), 0);
    }
  }

  abort(): void {
    if (this.onend) {
      setTimeout(() => this.onend?.(), 0);
    }
  }

  // Test helpers to simulate speech events
  simulateResult(results: Array<{ transcript: string; isFinal: boolean }>): void {
    if (!this.onresult) return;
    const event = {
      resultIndex: 0,
      results: results.map((r) => {
        const item = [{ transcript: r.transcript, confidence: 0.95 }];
        (item as any).isFinal = r.isFinal;
        return item;
      }),
    };
    this.onresult(event);
  }

  simulateError(error: string, message?: string): void {
    if (!this.onerror) return;
    this.onerror({ error, message });
  }

  simulateEnd(): void {
    if (!this.onend) return;
    this.onend();
  }
}
