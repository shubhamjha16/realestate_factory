/** Error shapes the console distinguishes, and the mapping from HTTP status. */

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
    readonly url: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

/** A tenancy denial is a 404 by design (S5), so it reads as "no such thing". */
export const isNotFound = (e: unknown): boolean =>
  e instanceof ApiError && e.status === 404;

/** S18 returns 429 on an exhausted quota; the console shows a real state for it. */
export const isQuotaExhausted = (e: unknown): boolean =>
  e instanceof ApiError && e.status === 429;

export const isValidationError = (e: unknown): boolean =>
  e instanceof ApiError && (e.status === 400 || e.status === 422);

export function messageFor(e: unknown): string {
  if (e instanceof ApiError) return e.detail;
  if (e instanceof Error) return e.message;
  return 'Something went wrong.';
}
