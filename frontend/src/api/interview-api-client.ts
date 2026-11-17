import {
  AbandonPayload,
  AnswerResponse,
  SkipQuestionSubmission,
  AnswerSubmission,
  AssessmentResult,
  InterviewSession,
  ProgressionResponse,
  Question,
  StartInterviewPayload,
} from '../types/interview';

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly details?: unknown;
  readonly retryAfterSeconds?: number;

  constructor(status: number, message: string, code?: string, details?: unknown, retryAfterSeconds?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export class AuthenticationError extends ApiError {
  constructor(message = 'Authentication credentials were not provided or are invalid.') {
    super(401, message, 'unauthorized');
    this.name = 'AuthenticationError';
  }
}

export class ForbiddenError extends ApiError {
  constructor(message = 'Access forbidden or stage not eligible.') {
    super(403, message, 'forbidden');
    this.name = 'ForbiddenError';
  }
}

export class NotFoundError extends ApiError {
  constructor(message = 'The requested interview resource was not found.') {
    super(404, message, 'not_found');
    this.name = 'NotFoundError';
  }
}

export class ConflictError extends ApiError {
  constructor(message = 'Interview version conflict or duplicate request with differing payload.') {
    super(409, message, 'conflict');
    this.name = 'ConflictError';
  }
}

export class RateLimitError extends ApiError {
  constructor(message = 'Too many requests. Please wait before retrying.', retryAfterSeconds?: number) {
    super(429, message, 'rate_limit_exceeded', undefined, retryAfterSeconds);
    this.name = 'RateLimitError';
  }
}

export class ProviderUnavailableError extends ApiError {
  constructor(message = 'The interview analysis provider is temporarily unavailable.') {
    super(503, message, 'provider_unavailable');
    this.name = 'ProviderUnavailableError';
  }
}

export interface ApiClientConfig {
  baseUrl?: string;
  bearerToken?: string;
  devUserId?: string;
  fetchFn?: typeof fetch;
}

/**
 * Robust API Client communicating with FINXL FastAPI backend (/api/v1).
 *
 * Enforces ownership, authentication headers, error mapping, and idempotency.
 */
export class InterviewApiClient {
  private _baseUrl: string;
  private _bearerToken?: string;
  private _devUserId?: string;
  private _fetch: typeof fetch;

  constructor(config?: ApiClientConfig) {
    this._baseUrl = config?.baseUrl ? config.baseUrl.replace(/\/+$/, '') : '/api/v1';
    this._bearerToken = config?.bearerToken;
    this._devUserId = config?.devUserId;
    this._fetch = config?.fetchFn || (typeof fetch !== 'undefined' ? fetch.bind(window) : (null as unknown as typeof fetch));
  }

  setBearerToken(token: string | undefined): void {
    this._bearerToken = token;
  }

  setDevUserId(devUserId: string | undefined): void {
    this._devUserId = devUserId;
  }

  hasBearerToken(): boolean {
    return Boolean(this._bearerToken);
  }

  private _getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };

    if (this._bearerToken) {
      headers['Authorization'] = `Bearer ${this._bearerToken}`;
    } else if (this._devUserId) {
      headers['X-Dev-User-ID'] = this._devUserId;
    }

    return headers;
  }

  private async _request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this._baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
    const mergedHeaders = { ...this._getHeaders(), ...(options.headers as Record<string, string>) };

    let response: Response;
    try {
      response = await this._fetch(url, { ...options, headers: mergedHeaders });
    } catch (networkErr) {
      throw new ApiError(0, 'Network request failed: ' + (networkErr instanceof Error ? networkErr.message : String(networkErr)));
    }

    if (!response.ok) {
      let errorBody: { detail?: string; error?: { code?: string; message?: string } } = {};
      try {
        errorBody = await response.json();
      } catch {
        // Non-JSON error body
      }

      const message = errorBody.detail || errorBody.error?.message || response.statusText || 'Request failed';
      const code = errorBody.error?.code;

      if (response.status === 401) {
        throw new AuthenticationError(message);
      }
      if (response.status === 403) {
        throw new ForbiddenError(message);
      }
      if (response.status === 404) {
        throw new NotFoundError(message);
      }
      if (response.status === 409) {
        throw new ConflictError(message);
      }
      if (response.status === 429) {
        const retryHeader = response.headers.get('Retry-After');
        const retryAfter = retryHeader ? parseInt(retryHeader, 10) : undefined;
        throw new RateLimitError(message, isNaN(retryAfter || NaN) ? undefined : retryAfter);
      }
      if (response.status === 503) {
        throw new ProviderUnavailableError(message);
      }

      throw new ApiError(response.status, message, code, errorBody);
    }

    return (await response.json()) as T;
  }

  async startInterview(payload: StartInterviewPayload): Promise<InterviewSession> {
    return this._request<InterviewSession>('/interviews', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getInterview(sessionId: string): Promise<InterviewSession> {
    return this._request<InterviewSession>(`/interviews/${sessionId}`, {
      method: 'GET',
    });
  }

  async getActiveInterview(): Promise<InterviewSession | null> {
    return this._request<InterviewSession | null>('/interviews/active', {
      method: 'GET',
    });
  }

  async getActiveQuestion(sessionId: string): Promise<Question> {
    return this._request<Question>(`/interviews/${sessionId}/question`, {
      method: 'GET',
    });
  }

  async submitAnswer(sessionId: string, payload: AnswerSubmission): Promise<AnswerResponse> {
    return this._request<AnswerResponse>(`/interviews/${sessionId}/answers`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async skipQuestion(sessionId: string, payload: SkipQuestionSubmission): Promise<AnswerResponse> {
    return this._request<AnswerResponse>(`/interviews/${sessionId}/skip`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async abandonInterview(sessionId: string, payload: AbandonPayload): Promise<InterviewSession> {
    return this._request<InterviewSession>(`/interviews/${sessionId}/abandon`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getAssessment(sessionId: string): Promise<AssessmentResult> {
    return this._request<AssessmentResult>(`/interviews/${sessionId}/assessment`, {
      method: 'GET',
    });
  }

  async getProgression(courseId?: string): Promise<ProgressionResponse> {
    const query = courseId ? `?course_id=${encodeURIComponent(courseId)}` : '';
    return this._request<ProgressionResponse>(`/progression${query}`, {
      method: 'GET',
    });
  }
}
