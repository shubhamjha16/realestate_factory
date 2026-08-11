/**
 * `comparables` feature barrel.
 *
 * Another feature imports from here and nowhere else (§3 boundary rule,
 * lint-enforced).
 */

export { EditableAdjustmentGrid } from './components/EditableAdjustmentGrid';
export { SampleAdequacy } from './components/SampleAdequacy';
export { useAdjustmentDraft } from './hooks/useAdjustmentDraft';
export { comparablesApi } from './services/comparablesApi';
export type { AdjustmentDraft, ComparableDraft, GridStats } from './types';
