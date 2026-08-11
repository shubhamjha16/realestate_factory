/**
 * Types local to `comparables`.
 *
 * The adjustment factors and their order mirror `services/valuation/adjust.py`.
 * The order is not cosmetic: adjustments compound, so applying them in a
 * different order than the report describes produces a different number than the
 * report explains.
 */

import type { AdjustmentFactor } from '@/shared/constants/adjustmentFactors';

export interface AdjustmentDraft {
  factor: AdjustmentFactor;
  /** Signed, as a decimal string. Never a number — see utils/money.ts. */
  pct: string;
  /** Never optional. A percentage nobody explained cannot be reviewed. */
  rationale: string;
}

export interface ComparableDraft {
  id: string;
  address: string;
  saleDate: string;
  salePrice: string;
  areaSqft: string;
  adjustments: AdjustmentDraft[];
}

export interface GridStats {
  count: number;
  meanAdjustedRate: string | null;
  medianAdjustedRate: string | null;
  spreadPct: string | null;
  meanGrossAdjustmentPct: string | null;
}
