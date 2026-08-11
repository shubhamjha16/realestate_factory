/** Types local to `valuations`. Money is a decimal string throughout. */

import type { ValuationApproach, ValuationBasis, ValuationPremise } from '@/shared/constants/propertyTypes';

export interface ApproachView {
  method: ValuationApproach;
  indicatedValue: string;
  /** Decimal string in 0–1. The set must sum to 1; the engine refuses otherwise. */
  weight: string;
  weightPct: string;
  /** Never optional. A weight is a judgement, and a judgement carries a reason. */
  rationale: string;
}

export interface ReconciliationView {
  concludedValue: string;
  valueRangeLow: string;
  valueRangeHigh: string;
  divergencePct: string | null;
  basis: ValuationBasis;
  premise: ValuationPremise;
  approaches: ApproachView[];
}
