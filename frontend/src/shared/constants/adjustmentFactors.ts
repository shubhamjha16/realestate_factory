/**
 * The comparable adjustment grid's factors, in the order they are applied.
 *
 * Mirrors `comparable_adjustments.factor` in the schema. S7 builds the engine
 * and the editable grid; the order matters because adjustments compound, and a
 * grid applied in a different order than the report describes is not defensible.
 */

export const ADJUSTMENT_FACTORS = [
  'time',
  'location',
  'tenure',
  'size',
  'age',
  'floor',
  'frontage',
  'view',
  'condition',
  'distress',
] as const;

export type AdjustmentFactor = (typeof ADJUSTMENT_FACTORS)[number];

export const ADJUSTMENT_FACTOR_LABELS: Record<AdjustmentFactor, string> = {
  time: 'Transaction date',
  location: 'Location',
  tenure: 'Tenure',
  size: 'Size',
  age: 'Age',
  floor: 'Floor',
  frontage: 'Frontage',
  view: 'View',
  condition: 'Condition',
  distress: 'Distress',
};

/** Every adjustment carries a written rationale. The grid is the defensibility. */
export const RATIONALE_REQUIRED = true;
