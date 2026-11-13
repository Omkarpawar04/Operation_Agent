import { describe, expect, it, vi } from 'vitest';
import {
  AuthenticationError,
  ConflictError,
  ForbiddenError,
  InterviewApiClient,
  NotFoundError,
  ProviderUnavailableError,
  RateLimitError,
} from '../src/api/interview-api-client';

describe('InterviewApiClient', () => {
  it('includes Authorization Bearer token when configured', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'session-123', stage: 'soft_1', state: 'awaiting_answer' }),
    });

    const client = new InterviewApiClient({
      baseUrl: '/api/v1',
      bearerToken: 'test-jwt-token-xyz',
      fetchFn: mockFetch as any,
    });

    await client.getInterview('session-123');

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/interviews/session-123',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-jwt-token-xyz',
        }),
      })
    );
  });

  it('includes X-Dev-User-ID when configured for dev environment', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'session-123' }),
    });

    const client = new InterviewApiClient({
      devUserId: '00000000-0000-0000-0000-000000000001',
      fetchFn: mockFetch as any,
    });

    await client.getInterview('session-123');

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/interviews/session-123',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Dev-User-ID': '00000000-0000-0000-0000-000000000001',
        }),
      })
    );
  });

  it('maps HTTP 401 to AuthenticationError', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ detail: 'Token has expired' }),
    });

    const client = new InterviewApiClient({ fetchFn: mockFetch as any });

    await expect(client.getInterview('session-123')).rejects.toThrow(AuthenticationError);
  });

  it('maps HTTP 403 to ForbiddenError', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: async () => ({ detail: 'Stage is locked' }),
    });

    const client = new InterviewApiClient({ fetchFn: mockFetch as any });

    await expect(client.getInterview('session-123')).rejects.toThrow(ForbiddenError);
  });

  it('maps HTTP 404 to NotFoundError', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Interview not found' }),
    });

    const client = new InterviewApiClient({ fetchFn: mockFetch as any });

    await expect(client.getInterview('session-123')).rejects.toThrow(NotFoundError);
  });

  it('maps HTTP 409 to ConflictError', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      statusText: 'Conflict',
      json: async () => ({ detail: 'Stale interview version' }),
    });

    const client = new InterviewApiClient({ fetchFn: mockFetch as any });

    await expect(
      client.submitAnswer('session-123', {
        question_id: 'q-1',
        expected_version: 1,
        idempotency_key: 'idemp-1',
        text: 'answer text',
      })
    ).rejects.toThrow(ConflictError);
  });

  it('maps HTTP 429 with Retry-After header to RateLimitError', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      statusText: 'Too Many Requests',
      headers: new Headers({ 'Retry-After': '45' }),
      json: async () => ({ detail: 'Rate limit exceeded' }),
    });

    const client = new InterviewApiClient({ fetchFn: mockFetch as any });

    try {
      await client.getInterview('session-123');
      expect.fail('Should have thrown RateLimitError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(RateLimitError);
      expect(err.retryAfterSeconds).toBe(45);
    }
  });

  it('maps HTTP 503 to ProviderUnavailableError', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      json: async () => ({ detail: 'Analysis provider is unavailable' }),
    });

    const client = new InterviewApiClient({ fetchFn: mockFetch as any });

    await expect(
      client.submitAnswer('session-123', {
        question_id: 'q-1',
        expected_version: 1,
        idempotency_key: 'idemp-1',
        text: 'answer text',
      })
    ).rejects.toThrow(ProviderUnavailableError);
  });
});
