/**
 * Location and ownership are sensitive.
 *
 * Exact coordinates, owner names and survey numbers stay out of logs and out of
 * any client-role response. The backend is the enforcement point (S13's
 * `redaction.py`, S20's review); these helpers keep the console from
 * reintroducing what the engine withheld — most obviously in Sentry breadcrumbs
 * and console output during development.
 */

export function redactSurveyNo(value: string | null | undefined): string {
  if (!value) return '—';
  return value.length <= 2 ? '••' : `${value.slice(0, 2)}${'•'.repeat(value.length - 2)}`;
}

export function redactOwnerName(value: string | null | undefined): string {
  if (!value) return '—';
  return value
    .split(/\s+/)
    .map((part) => (part ? `${part[0]}${'•'.repeat(Math.max(part.length - 1, 1))}` : part))
    .join(' ');
}

/** Coarsen to roughly a kilometre — enough to place a comparable on a map, not a door. */
export function coarsenCoordinate(value: number): number {
  return Math.round(value * 100) / 100;
}

/** Strip anything that must never reach an error report. */
export function scrubForTelemetry<T extends Record<string, unknown>>(payload: T): Partial<T> {
  const forbidden = new Set([
    'owner_name', 'ownerName', 'survey_no', 'surveyNo', 'khasra_no', 'khasraNo',
    'geom', 'lat', 'lng', 'latitude', 'longitude', 'address',
  ]);
  return Object.fromEntries(
    Object.entries(payload).filter(([k]) => !forbidden.has(k)),
  ) as Partial<T>;
}
