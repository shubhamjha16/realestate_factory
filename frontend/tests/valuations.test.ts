import { describe, expect, it } from 'vitest';
import { ADJUSTMENT_FACTORS } from '@/shared/constants/adjustmentFactors';
import { VALUATION_APPROACHES, VALUATION_BASES } from '@/shared/constants/propertyTypes';

/**
 * These mirror the engine by hand until `packages/api-types` covers them.
 * The order of the adjustment factors is not cosmetic: adjustments compound, so
 * the console must show them in the order the engine applies them, which is the
 * order the report describes.
 */
describe('valuation constants mirror the engine', () => {
  it('holds the three approaches', () => {
    expect([...VALUATION_APPROACHES]).toEqual(['sales', 'income', 'cost']);
  });

  it('holds the five bases of value', () => {
    expect([...VALUATION_BASES]).toEqual([
      'market', 'fair', 'liquidation', 'distress', 'insurable',
    ]);
  });

  it('lists the adjustment factors in the order the engine applies them', () => {
    // services/valuation/adjust.py ADJUSTMENT_ORDER: market-level first, then
    // physical differences against the subject.
    expect([...ADJUSTMENT_FACTORS]).toEqual([
      'time', 'location', 'tenure', 'size', 'age',
      'floor', 'frontage', 'view', 'condition', 'distress',
    ]);
  });
});
