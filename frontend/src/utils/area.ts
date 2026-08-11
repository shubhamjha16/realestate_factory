/**
 * Area conversion.
 *
 * Factors come from `packages/units/units.json` — the same file
 * `backend/app/utils/geo.py` reads. Neither app holds a factor of its own,
 * because a console that converts square metres differently from the engine
 * produces a report whose area and rate contradict its total.
 *
 * A state-dependent unit without a state throws. A bigha is not one area: it
 * differs by state and, within a state, by district, and a wrong conversion
 * silently multiplies a valuation with nothing downstream able to tell.
 */

import table from '@realestate-factory/units/units.json';

type UniversalEntry = { sqft_per_unit: string; label: string; verified: boolean; source: string };
type StateEntry = { sqft_per_unit: string; verified: boolean; source: string };

const UNIVERSAL = table.universal as Record<string, UniversalEntry>;
const STATE_DEPENDENT = table.state_dependent as Record<
  string,
  { label: string; by_state: Record<string, StateEntry> }
>;

export const AREA_UNITS = Object.keys(UNIVERSAL);
export const STATE_DEPENDENT_UNITS = Object.keys(STATE_DEPENDENT);

const ALIASES: Record<string, string> = {
  'sq ft': 'sqft', 'square feet': 'sqft', 'square foot': 'sqft', ft2: 'sqft',
  'sq m': 'sqm', 'square metre': 'sqm', 'square meter': 'sqm', m2: 'sqm',
  'sq yd': 'sqyd', 'square yard': 'sqyd', gaj: 'sqyd',
  acres: 'acre', hectares: 'hectare', ha: 'hectare',
  gunta: 'guntha', gunthas: 'guntha', cents: 'cent', grounds: 'ground',
  kanals: 'kanal', marlas: 'marla',
  bighas: 'bigha', biswas: 'biswa', kathas: 'katha', cottah: 'katha', vighas: 'vigha',
};

export function normaliseUnit(unit: string): string {
  const cleaned = unit.trim().toLowerCase().replace(/[._-]/g, ' ').replace(/\s+/g, ' ');
  return ALIASES[cleaned] ?? cleaned.replace(/\s/g, '');
}

export class UnknownUnitError extends Error {
  constructor(readonly unit: string) {
    super(`Unknown area unit "${unit}".`);
    this.name = 'UnknownUnitError';
  }
}

export class AmbiguousUnitError extends Error {
  constructor(readonly unit: string, readonly knownStates: string[]) {
    super(
      `"${unit}" varies by state and district; a jurisdiction is required. ` +
        `Known: ${knownStates.join(', ') || 'none'}.`,
    );
    this.name = 'AmbiguousUnitError';
  }
}

export class UnverifiedFactorError extends Error {
  constructor(readonly unit: string, readonly state: string, readonly source: string) {
    super(
      `The "${unit}" factor for ${state} is not verified against a notified schedule ` +
        `(${source}). A figure that reaches a signed report must not depend on one.`,
    );
    this.name = 'UnverifiedFactorError';
  }
}

export function isStateDependent(unit: string): boolean {
  return normaliseUnit(unit) in STATE_DEPENDENT;
}

export interface FactorOptions {
  state?: string;
  allowUnverified?: boolean;
}

export function sqftPerUnit(unit: string, options: FactorOptions = {}): number {
  const key = normaliseUnit(unit);

  const universal = UNIVERSAL[key];
  if (universal) return Number(universal.sqft_per_unit);

  const stateDependent = STATE_DEPENDENT[key];
  if (!stateDependent) throw new UnknownUnitError(unit);

  const states = Object.keys(stateDependent.by_state);
  if (!options.state) throw new AmbiguousUnitError(key, states);

  const entry = stateDependent.by_state[options.state.trim().toUpperCase()];
  if (!entry) throw new AmbiguousUnitError(key, states);
  if (!entry.verified && !options.allowUnverified) {
    throw new UnverifiedFactorError(key, options.state, entry.source);
  }
  return Number(entry.sqft_per_unit);
}

export function convertArea(
  value: number,
  from: string,
  to: string,
  options: FactorOptions = {},
): number {
  return (value * sqftPerUnit(from, options)) / sqftPerUnit(to, options);
}

export function unitLabel(unit: string): string {
  const key = normaliseUnit(unit);
  return UNIVERSAL[key]?.label ?? STATE_DEPENDENT[key]?.label ?? key;
}

export function formatArea(value: number, unit: string, dp = 2): string {
  return `${value.toLocaleString('en-IN', {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  })} ${unitLabel(unit)}`;
}
