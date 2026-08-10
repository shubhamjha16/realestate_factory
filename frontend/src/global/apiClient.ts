/**
 * The single way this console talks to the engine.
 *
 * Auth header, retry, SSE and error mapping live here so that no feature writes
 * `fetch` directly. From S3 the request and response types come from
 * `packages/api-types`, generated from the backend's OpenAPI spec, so a schema
 * change that breaks the console fails the build.
 */

import { env } from './env';
import { ApiError } from './errors';

type Json = Record<string, unknown>;

let authToken: string | null = null;
export const setAuthToken = (token: string | null): void => {
  authToken = token;
};

const IDEMPOTENT = new Set(['GET', 'HEAD']);
const RETRY_STATUSES = new Set([502, 503, 504]);

interface RequestOptions {
  method?: string;
  body?: Json;
  signal?: AbortSignal;
  retries?: number;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal, retries = IDEMPOTENT.has(method) ? 2 : 0 } = options;
  const url = `${env.apiBaseUrl}${path}`;

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body) headers['Content-Type'] = 'application/json';
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(url, {
        method,
        headers,
        signal,
        body: body ? JSON.stringify(body) : undefined,
      });

      if (!response.ok) {
        if (RETRY_STATUSES.has(response.status) && attempt < retries) {
          await backoff(attempt);
          continue;
        }
        throw new ApiError(response.status, await detailOf(response), url);
      }

      return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
    } catch (e) {
      if (e instanceof ApiError || signal?.aborted) throw e;
      lastError = e;
      if (attempt < retries) await backoff(attempt);
    }
  }
  throw lastError instanceof Error ? lastError : new Error(`Request to ${url} failed`);
}

async function detailOf(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === 'string') return payload.detail;
    if (payload.detail) return JSON.stringify(payload.detail);
  } catch {
    /* a non-JSON error body is still an error */
  }
  return response.statusText || `HTTP ${response.status}`;
}

const backoff = (attempt: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, 2 ** attempt * 250));

/**
 * Server-sent job progress. The endpoint lands in S18
 * (`parsed 34 comparables`, `drafting section 4/9`); the transport is here so
 * that features never open an EventSource themselves.
 */
export function streamJobEvents(
  jobId: string,
  onEvent: (event: { node: string; message: string }) => void,
): () => void {
  const source = new EventSource(`${env.apiBaseUrl}/jobs/${jobId}/events`);
  source.onmessage = (e) => onEvent(JSON.parse(e.data as string));
  source.onerror = () => source.close();
  return () => source.close();
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, body: Json, signal?: AbortSignal) =>
    request<T>(path, { method: 'POST', body, signal }),
  patch: <T>(path: string, body: Json) => request<T>(path, { method: 'PATCH', body }),
};
