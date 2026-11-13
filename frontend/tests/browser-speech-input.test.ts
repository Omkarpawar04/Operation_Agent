import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BrowserSpeechInput } from '../src/adapters/speech/browser-speech-input';
import { SpeechInputError } from '../src/types/speech';
import { MockSpeechRecognition } from './mocks/mock-speech-recognition';

describe('BrowserSpeechInput', () => {
  let adapter: BrowserSpeechInput;

  beforeEach(() => {
    MockSpeechRecognition.instances = [];
    (window as any).SpeechRecognition = MockSpeechRecognition;
    (window as any).webkitSpeechRecognition = undefined;
    adapter = new BrowserSpeechInput();
  });

  afterEach(() => {
    adapter.cancel();
    delete (window as any).SpeechRecognition;
    delete (window as any).webkitSpeechRecognition;
  });

  it('detects supported browser correctly', () => {
    expect(adapter.isSupported()).toBe(true);

    // Test webkit prefix support
    delete (window as any).SpeechRecognition;
    (window as any).webkitSpeechRecognition = MockSpeechRecognition;
    expect(adapter.isSupported()).toBe(true);
  });

  it('detects unsupported browser correctly', () => {
    delete (window as any).SpeechRecognition;
    delete (window as any).webkitSpeechRecognition;
    expect(adapter.isSupported()).toBe(false);
  });

  it('rejects start() when browser is unsupported', async () => {
    delete (window as any).SpeechRecognition;
    delete (window as any).webkitSpeechRecognition;

    await expect(adapter.start()).rejects.toThrow(SpeechInputError);
    await expect(adapter.start()).rejects.toMatchObject({
      code: 'unsupported',
    });
  });

  it('captures successful final transcription', async () => {
    const finalCallback = vi.fn();
    const interimCallback = vi.fn();

    const startPromise = adapter.start({
      onFinalTranscript: finalCallback,
      onInterimTranscript: interimCallback,
    });

    const mockInstance = MockSpeechRecognition.instances[0];
    expect(mockInstance).toBeDefined();

    // Simulate interim results
    mockInstance.simulateResult([
      { transcript: 'I designed', isFinal: false },
    ]);
    expect(interimCallback).toHaveBeenCalledWith('I designed');

    // Simulate final result
    mockInstance.simulateResult([
      { transcript: 'I designed the system architecture with zero downtime.', isFinal: true },
    ]);
    expect(finalCallback).toHaveBeenCalledWith('I designed the system architecture with zero downtime.');

    // End session
    mockInstance.simulateEnd();

    const result = await startPromise;
    expect(result).toBe('I designed the system architecture with zero downtime.');
  });

  it('does not yield interim transcripts as the final result', async () => {
    const startPromise = adapter.start();
    const mockInstance = MockSpeechRecognition.instances[0];

    // Only interim transcripts sent
    mockInstance.simulateResult([
      { transcript: 'partial utterance', isFinal: false },
    ]);

    mockInstance.simulateEnd();

    // Should reject because only interim was heard, no final transcript
    await expect(startPromise).rejects.toMatchObject({
      code: 'empty-transcript',
    });
  });

  it('rejects empty transcript when recognition ends without speech', async () => {
    const startPromise = adapter.start();
    const mockInstance = MockSpeechRecognition.instances[0];

    mockInstance.simulateEnd();

    await expect(startPromise).rejects.toMatchObject({
      code: 'empty-transcript',
    });
  });

  it('handles microphone permission denial (not-allowed / permission-denied)', async () => {
    const errorCallback = vi.fn();
    const startPromise = adapter.start({ onError: errorCallback });
    const mockInstance = MockSpeechRecognition.instances[0];

    mockInstance.simulateError('not-allowed');

    await expect(startPromise).rejects.toMatchObject({
      code: 'not-allowed',
    });
    expect(errorCallback).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'not-allowed' })
    );
  });

  it('handles no-speech error', async () => {
    const errorCallback = vi.fn();
    const startPromise = adapter.start({ onError: errorCallback });
    const mockInstance = MockSpeechRecognition.instances[0];

    mockInstance.simulateError('no-speech');

    await expect(startPromise).rejects.toMatchObject({
      code: 'no-speech',
    });
    expect(errorCallback).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'no-speech' })
    );
  });

  it('handles network error', async () => {
    const errorCallback = vi.fn();
    const startPromise = adapter.start({ onError: errorCallback });
    const mockInstance = MockSpeechRecognition.instances[0];

    mockInstance.simulateError('network');

    await expect(startPromise).rejects.toMatchObject({
      code: 'network',
    });
    expect(errorCallback).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'network' })
    );
  });

  it('handles audio-capture error', async () => {
    const errorCallback = vi.fn();
    const startPromise = adapter.start({ onError: errorCallback });
    const mockInstance = MockSpeechRecognition.instances[0];

    mockInstance.simulateError('audio-capture');

    await expect(startPromise).rejects.toMatchObject({
      code: 'audio-capture',
    });
  });

  it('supports explicit cancellation and rejects with aborted code', async () => {
    const startPromise = adapter.start();
    expect(adapter.getState()).toBe('starting');

    adapter.cancel();
    expect(adapter.getState()).toBe('inactive');

    await expect(startPromise).rejects.toMatchObject({
      code: 'aborted',
    });
  });

  it('prevents multiple simultaneous recognition sessions', async () => {
    const firstPromise = adapter.start();
    await expect(adapter.start()).rejects.toMatchObject({
      code: 'already-active',
    });

    adapter.cancel();
    await expect(firstPromise).rejects.toMatchObject({ code: 'aborted' });
  });

  it('cleans up event handlers on stop and cancel', async () => {
    const startPromise = adapter.start();
    const mockInstance = MockSpeechRecognition.instances[0];

    expect(mockInstance.onresult).not.toBeNull();
    expect(mockInstance.onerror).not.toBeNull();

    mockInstance.simulateResult([
      { transcript: 'Completed answer statement.', isFinal: true },
    ]);

    adapter.stop();
    mockInstance.simulateEnd();

    await startPromise;

    expect(adapter.getState()).toBe('inactive');
    expect(mockInstance.onresult).toBeNull();
    expect(mockInstance.onerror).toBeNull();
  });
});
