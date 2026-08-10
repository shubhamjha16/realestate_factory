/**
 * Shapes shared by the property components. These mirror the schema in §4 and
 * are replaced by the generated `packages/api-types` at S3; they exist now so
 * the component signatures are designed against the real data, not invented.
 *
 * Money is a decimal string throughout — see `utils/money.ts`.
 */

import type { AdjustmentFactor } from '@/shared/constants/adjustmentFactors';

export interface Point {
  lat: number;
  lng: number;
}

export interface Comparable {
  id: string;
  address: string;
  geom: Point | null;
  saleDate: string;
  salePrice: string;
  area: string;
  areaUnit: string;
  ratePerUnit: string;
  propertyType: string;
  ageYears: number | null;
  floor: number | null;
  distanceM: number | null;
  verified: boolean;
  note: string | null;
}

export interface ComparableAdjustment {
  id: string;
  comparableId: string;
  factor: AdjustmentFactor;
  /** Signed percentage, as a decimal string. */
  pct: string;
  /** Never optional. The rationale is what makes the grid defensible (S7). */
  rationale: string;
  appliedBy: string;
}

export interface AdjustedComparable {
  comparable: Comparable;
  adjustments: readonly ComparableAdjustment[];
  netAdjustmentPct: string;
  adjustedRate: string;
}

export interface ValueRange {
  low: string;
  concluded: string;
  high: string;
  currency: string;
}

export interface RentRollLine {
  id: string;
  unitNo: string;
  tenant: string | null;
  area: string;
  contractedRent: string;
  effectiveRent: string;
  vacancy: boolean;
  waultMonths: string | null;
  leaseEnd: string | null;
}
