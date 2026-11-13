import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BrowserSpeechOutput } from '../src/adapters/speech/browser-speech-output';
import { SpeechOutputError } from '../src/types/speech';
import { MockSpeechSynthesis, MockSpeechSynthesisUtterance } from './mocks/mock-speech-synthesis';

describe('BrowserSpeechOutput', () => {
  let adapter: BrowserSpeechOutput;
  let mockSynth: MockSpeechSynthesis;

  beforeEach(() => {
    mockSynth = new MockSpeechSynthesis();
    (window as any).speechSynthesis = mockSynth;
    (window as any).SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;
    adapter = new BrowserSpeechOutput();
  });

  afterEach(() => {
    adapter.stop();
    delete (window as any).speechSynthesis;
    delete (window as any).SpeechSynthesisUtterance;
  });

  it('detects browser support correctly', () => {
    expect(adapter.isSupported()).toBe(true);

    delete (window as any).speechSynthesis;
    expect(adapter.isSupported()).toBe(false);
  });

  it('rejects speak() when speech synthesis is unsupported', async () => {
    delete (window as any).speechSynthesis;

    await expect(adapter.speak('Hello candidate')).rejects.toThrow(SpeechOutputError);
    await expect(adapter.speak('Hello candidate')).rejects.toMatchObject({
      code: 'unsupported',
    });
  });

  it('successfully speaks the provided text', async () => {
    const speakPromise = adapter.speak('Can you explain your approach to system reliability?');

    expect(mockSynth.speaking).toBe(true);
    expect(mockSynth.activeUtterances.length).toBe(1);
    expect(mockSynth.activeUtterances[0].text).toBe('Can you explain your approach to system reliability?');

    await speakPromise;
    expect(mockSynth.speaking).toBe(false);
  });

  it('selects suitable voice matching requested language (en-IN)', async () => {
    adapter.speak('Welcome to the interview', 'en-IN');

    const utterance = mockSynth.activeUtterances[0];
    expect(utterance.lang).toBe('en-IN');
    expect(utterance.voice?.lang).toBe('en-IN');
  });

  it('falls back gracefully to available English voices when requested voice is absent', () => {
    // Only US voice available
    mockSynth.setVoices([
      { name: 'Generic Voice', lang: 'en-US', default: false },
    ]);

    const voice = adapter.findVoice('en-IN');
    expect(voice).toBeDefined();
    expect(voice?.lang).toBe('en-US');
  });

  it('falls back to default voice when language does not match at all', () => {
    mockSynth.setVoices([
      { name: 'French Voice', lang: 'fr-FR', default: false },
      { name: 'Default Voice', lang: 'de-DE', default: true },
    ]);

    const voice = adapter.findVoice('en-IN');
    expect(voice?.name).toBe('Default Voice');
  });

  it('stops and cancels active speech cleanly', async () => {
    const cancelSpy = vi.spyOn(mockSynth, 'cancel');

    const speakPromise = adapter.speak('A long interview question being spoken...');
    expect(mockSynth.speaking).toBe(true);

    adapter.stop();
    expect(cancelSpy).toHaveBeenCalled();

    // Resolves cleanly on cancellation without unhandled rejection
    await speakPromise;
  });

  it('prevents overlapping speech by stopping previous utterance before starting new one', async () => {
    const cancelSpy = vi.spyOn(mockSynth, 'cancel');

    adapter.speak('First question');
    expect(mockSynth.activeUtterances.length).toBe(1);

    adapter.speak('Second follow-up question');
    expect(cancelSpy).toHaveBeenCalled();
  });

  it('resolves immediately when given empty or whitespace text', async () => {
    await expect(adapter.speak('')).resolves.toBeUndefined();
    await expect(adapter.speak('   ')).resolves.toBeUndefined();
    expect(mockSynth.activeUtterances.length).toBe(0);
  });
});
