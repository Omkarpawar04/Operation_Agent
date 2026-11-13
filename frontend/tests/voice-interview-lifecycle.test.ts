import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InterviewApiClient, ProviderUnavailableError } from '../src/api/interview-api-client';
import { VoiceInterviewLifecycle } from '../src/orchestrator/voice-interview-lifecycle';
import { SpeechInput, SpeechInputError, SpeechOutput } from '../src/types/speech';

describe('VoiceInterviewLifecycle Integration', () => {
  let mockApiClient: InterviewApiClient;
  let mockSpeechInput: SpeechInput;
  let mockSpeechOutput: SpeechOutput;
  let lifecycle: VoiceInterviewLifecycle;

  let simulatedSpeechStartCallback: ((options?: any) => Promise<string>) | null = null;

  beforeEach(() => {
    mockApiClient = {
      getInterview: vi.fn().mockResolvedValue({
        id: 'session-001',
        stage: 'soft_1',
        state: 'awaiting_answer',
        version: 1,
        active_question_id: 'q-base-1',
      }),
      getActiveQuestion: vi.fn().mockResolvedValue({
        id: 'q-base-1',
        text: 'Tell me about a challenging technical trade-off you had to make.',
        kind: 'base',
        sequence: 1,
        version: 1,
      }),
      submitAnswer: vi.fn().mockResolvedValue({
        state: 'awaiting_follow_up_answer',
        version: 2,
        question: 'What specific metrics did you monitor?',
        action: 'follow_up',
      }),
      getAssessment: vi.fn().mockResolvedValue({
        attempt_id: 'att-123',
        score: 78.5,
        passed: true,
        rubric_version: 'rubric_v1_soft_skills',
      }),
      abandonInterview: vi.fn(),
      startInterview: vi.fn(),
      getProgression: vi.fn(),
    } as unknown as InterviewApiClient;

    mockSpeechInput = {
      isSupported: vi.fn().mockReturnValue(true),
      start: vi.fn().mockImplementation((options) => {
        if (simulatedSpeechStartCallback) {
          return simulatedSpeechStartCallback(options);
        }
        return Promise.resolve('I balanced consistency against availability using quorum writes.');
      }),
      stop: vi.fn(),
      cancel: vi.fn(),
    };

    mockSpeechOutput = {
      isSupported: vi.fn().mockReturnValue(true),
      speak: vi.fn().mockResolvedValue(undefined),
      stop: vi.fn(),
    };

    lifecycle = new VoiceInterviewLifecycle({
      apiClient: mockApiClient,
      speechInput: mockSpeechInput,
      speechOutput: mockSpeechOutput,
      autoSpeakQuestions: true,
      language: 'en-IN',
    });
  });

  it('initializes session, displays question, and automatically speaks it', async () => {
    await lifecycle.initialize('session-001');

    const snap = lifecycle.getSnapshot();
    expect(snap.sessionId).toBe('session-001');
    expect(snap.stage).toBe('soft_1');
    expect(snap.activeQuestion?.text).toBe('Tell me about a challenging technical trade-off you had to make.');
    expect(snap.currentVersion).toBe(1);

    // Verified: Question was spoken via SpeechOutput
    expect(mockSpeechOutput.speak).toHaveBeenCalledWith(
      'Tell me about a challenging technical trade-off you had to make.',
      'en-IN'
    );
  });

  it('allows student to start and stop listening, capturing transcript and submitting voice answer', async () => {
    await lifecycle.initialize('session-001');

    await lifecycle.startListening();

    expect(mockSpeechInput.start).toHaveBeenCalled();
    const snap = lifecycle.getSnapshot();
    expect(snap.finalTranscript).toBe('I balanced consistency against availability using quorum writes.');

    // Now submit the spoken answer
    await lifecycle.submitAnswer();

    // Verified: Answer was submitted through backend API
    expect(mockApiClient.submitAnswer).toHaveBeenCalledWith(
      'session-001',
      expect.objectContaining({
        question_id: 'q-base-1',
        expected_version: 1,
        text: 'I balanced consistency against availability using quorum writes.',
        idempotency_key: expect.stringMatching(/^voice-ans-/),
      })
    );
    expect(lifecycle.getSnapshot().currentVersion).toBe(2);
  });

  it('displays and speaks follow-up question when returned by backend', async () => {
    // Setup follow-up question return
    (mockApiClient.getActiveQuestion as any).mockResolvedValueOnce({
      id: 'q-base-1',
      text: 'Tell me about a trade-off',
      kind: 'base',
      version: 1,
    }).mockResolvedValueOnce({
      id: 'q-followup-2',
      text: 'What specific metrics did you monitor?',
      kind: 'follow_up',
      sequence: 2,
      version: 2,
    });

    await lifecycle.initialize('session-001');

    // Submit answer
    await lifecycle.submitAnswer('I balanced consistency against availability.');

    const snap = lifecycle.getSnapshot();
    expect(snap.isFollowUp).toBe(true);
    expect(snap.activeQuestion?.id).toBe('q-followup-2');
    expect(snap.state).toBe('follow_up_received');

    // Verified: Spoke the follow-up question
    expect(mockSpeechOutput.speak).toHaveBeenCalledWith(
      'What specific metrics did you monitor?',
      'en-IN'
    );
  });

  it('transitions to completed and stops recognition/speech on final completion', async () => {
    (mockApiClient.submitAnswer as any).mockResolvedValueOnce({
      state: 'completed',
      version: 3,
      question: null,
      action: 'complete',
    });

    await lifecycle.initialize('session-001');
    await lifecycle.submitAnswer('The response latencies dropped by 35% with zero regressions.');

    const snap = lifecycle.getSnapshot();
    expect(snap.state).toBe('completed');
    expect(snap.assessmentResult).toBeDefined();
    expect(snap.assessmentResult?.passed).toBe(true);
    expect(snap.assessmentResult?.score).toBe(78.5);

    // Recognition and speech stopped
    expect(mockSpeechInput.stop).toHaveBeenCalled();
  });

  it('permits safe retry on transient backend error without losing version or answer', async () => {
    await lifecycle.initialize('session-001');

    (mockApiClient.submitAnswer as any).mockRejectedValueOnce(
      new ProviderUnavailableError('Analysis provider timeout')
    );

    await lifecycle.submitAnswer('Valid answer text that failed due to provider timeout.');

    const errSnap = lifecycle.getSnapshot();
    expect(errSnap.state).toBe('error');
    expect(errSnap.lastError?.isRetryable).toBe(true);
    expect(errSnap.finalTranscript).toBe('Valid answer text that failed due to provider timeout.');
    expect(errSnap.currentVersion).toBe(1);
    const originalSubmission = (mockApiClient.submitAnswer as any).mock.calls[0][1];
    (mockApiClient.getInterview as any).mockResolvedValueOnce({
      id: 'session-001',
      stage: 'soft_1',
      state: 'awaiting_answer',
      version: 3,
      active_question_id: 'q-base-1',
    });
    (mockApiClient.getActiveQuestion as any).mockResolvedValueOnce({
      id: 'q-base-1',
      text: 'Tell me about a challenging technical trade-off you had to make.',
      kind: 'base',
      sequence: 1,
      version: 3,
    });

    // Setup success on retry
    (mockApiClient.submitAnswer as any).mockResolvedValueOnce({
      state: 'awaiting_follow_up_answer',
      version: 4,
      question: 'Next question',
      action: 'follow_up',
    });

    await lifecycle.retry();

    const successSnap = lifecycle.getSnapshot();
    expect(successSnap.state).toBe('follow_up_received');
    expect(successSnap.currentVersion).toBe(4);
    expect(successSnap.lastError).toBeNull();
    const retrySubmission = (mockApiClient.submitAnswer as any).mock.calls[1][1];
    expect(retrySubmission.idempotency_key).toBe(originalSubmission.idempotency_key);
    expect(retrySubmission.question_id).toBe(originalSubmission.question_id);
    expect(retrySubmission.text).toBe(originalSubmission.text);
    expect(retrySubmission.expected_version).toBe(3);
  });

  it('rejects voice submission when speech recognition is unsupported', async () => {
    (mockSpeechInput.isSupported as any).mockReturnValue(false);

    const unsupportedLifecycle = new VoiceInterviewLifecycle({
      apiClient: mockApiClient,
      speechInput: mockSpeechInput,
      speechOutput: mockSpeechOutput,
    });

    await unsupportedLifecycle.initialize('session-001');

    // Trying to start listening reports unsupported
    await unsupportedLifecycle.startListening();
    expect(unsupportedLifecycle.getSnapshot().lastError?.code).toBe('unsupported');
    expect(unsupportedLifecycle.getSnapshot().lastError?.message).toContain('Chrome or Edge');
  });

  it('handles microphone permission denial gracefully and blocks empty submit', async () => {
    (mockSpeechInput.start as any).mockRejectedValueOnce(
      new SpeechInputError('Permission denied', 'not-allowed')
    );

    await lifecycle.initialize('session-001');
    await lifecycle.startListening();

    const snap = lifecycle.getSnapshot();
    expect(snap.state).toBe('error');
    expect(snap.lastError?.code).toBe('not-allowed');
    expect(snap.lastError?.message).toContain('Microphone permission was denied');

    // Candidate cannot submit empty answer
    await lifecycle.submitAnswer();
    expect(lifecycle.getSnapshot().lastError?.code).toBe('empty_answer');
  });

  it('rejects empty or whitespace-only answers without making API requests', async () => {
    await lifecycle.initialize('session-001');
    (mockApiClient.submitAnswer as any).mockClear();

    await lifecycle.submitAnswer('   ');

    expect(mockApiClient.submitAnswer).not.toHaveBeenCalled();
    expect(lifecycle.getSnapshot().lastError?.code).toBe('empty_answer');
  });

  it('cleans up resources and halts active speech/recognition on dispose()', async () => {
    await lifecycle.initialize('session-001');

    lifecycle.dispose();

    expect(mockSpeechOutput.stop).toHaveBeenCalled();
    expect(mockSpeechInput.cancel).toHaveBeenCalled();
  });
});
