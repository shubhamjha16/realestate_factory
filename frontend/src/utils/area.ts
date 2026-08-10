/**
 * Area conversion.
 *
 * The etl frontend this scaffold mirrors never converts units. Here a wrong
 * conversion silently multiplies a valuation, so unit handling is a first-class
 * utility with its own tests, and the factors come from the same shared table
 * the engine uses (`backend/app/utils/geo.py`, S6).
 *
 * S1 holds the unambiguous factors and, more importantly, refuses the ambiguous
 * ones. A bigha is not one area: it differs by state and, within a state, by
 * district. Guessing is worse than failing.
 */

import { AMBIGUOUS_LOCAL_UNITS } from '@/shared/constants/states';

export const AREA_UNITS = ['sqft', 'sqm', 'sqyd', 'acre', 'hectare', 'guntha', 'cent'] as const;
export type AreaUnit = (typeof AREA_UNITS)[number];

/** Square feet per unit. Exact where the definition is exact. */
const SQFT_PER: Record<AreaUnit, number> = {
  sqft: 1,
  sqm: 10.763910416709722,
  sqyd: 9,
  acre: 43560,
  hectare: 107639.10416709722,
  guntha: 1089, // 1/40 acre — uniform where used
  cent: 435.6, // 1/100 acre
};

export const AREA_UNIT_LABELS: Record<AreaUnit, string> = {
  sqft: 'sq ft',
  sqm: 'sq m',
  sqyd: 'sq yd',
  acre: 'acre',
  hectare: 'hectare',
  guntha: 'guntha',
  cent: 'cent',
};

export class AmbiguousUnitError extends Error {
  constructor(readonly unit: string) {
    super(
      `"${unit}" has no single conversion factor — it varies by state and district. ` +
        `Resolve it against the notified factor for the property's jurisdiction.`,
    );
    this.name = 'AmbiguousUnitError';
  }
}

export function isAmbiguousUnit(unit: string): boolean {
  return (AMBIGUOUS_LOCAL_UNITS as readonly string[]).includes(unit.toLowerCase());
}

export function convertArea(value: number, from: string, to: string): number {
  const f = from.toLowerCase();
  const t = to.toLowerCase();
  if (isAmbiguousUnit(f)) throw new AmbiguousUnitError(f);
  if (isAmbiguousUnit(t)) throw new AmbiguousUnitError(t);
  if (!(f in SQFT_PER)) throw new Error(`Unknown area unit "${from}"`);
  if (!(t in SQFT_PER)) throw new Error(`Unknown area unit "${to}"`);
  return (value * SQFT_PER[f as AreaUnit]) / SQFT_PER[t as AreaUnit];
}

export function formatArea(value: number, unit: AreaUnit, dp = 2): string {
  return `${value.toLocaleString('en-IN', {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  })} ${AREA_UNIT_LABELS[unit]}`;
}
