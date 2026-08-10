/**
 * Typed, validated access to the compiled-in environment.
 *
 * Mirrors the backend's fail-fast posture: a missing base URL is a boot failure
 * that names the variable, not a stream of requests to `undefined/jobs`.
 */

function required(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(
      `Missing ${name}. Copy frontend/.env.example to frontend/.env and set it.`,
    );
  }
  return value;
}

export const env = {
  apiBaseUrl: required('VITE_API_BASE_URL', import.meta.env.VITE_API_BASE_URL),
  mapStyleUrl: import.meta.env.VITE_MAP_STYLE_URL ?? '',
  sentryDsn: import.meta.env.VITE_SENTRY_DSN ?? '',
  isDev: import.meta.env.DEV,
} as const;
