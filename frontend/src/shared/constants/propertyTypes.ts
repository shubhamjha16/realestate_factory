export const PROPERTY_TYPES = [
  'residential_apartment',
  'residential_plot',
  'independent_house',
  'commercial_office',
  'commercial_retail',
  'industrial',
  'warehouse',
  'agricultural_land',
  'hospitality',
  'institutional',
  'mixed_use',
] as const;

export type PropertyType = (typeof PROPERTY_TYPES)[number];

export const TENURES = ['freehold', 'leasehold'] as const;
export type Tenure = (typeof TENURES)[number];

/** Basis of value. Drives which approaches the mandate requires — S9. */
export const VALUATION_BASES = [
  'market',
  'fair',
  'liquidation',
  'distress',
  'insurable',
] as const;
export type ValuationBasis = (typeof VALUATION_BASES)[number];

export const VALUATION_PREMISES = ['existing_use', 'highest_best_use'] as const;
export type ValuationPremise = (typeof VALUATION_PREMISES)[number];

export const VALUATION_APPROACHES = ['sales', 'income', 'cost'] as const;
export type ValuationApproach = (typeof VALUATION_APPROACHES)[number];
