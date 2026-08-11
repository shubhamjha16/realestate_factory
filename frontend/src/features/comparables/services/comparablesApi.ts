import { api } from '@/global/apiClient';
import type { AdjustmentDraft } from '../types';

/**
 * The engine computes; the console displays.
 *
 * Every adjusted rate on screen comes back from `services/valuation/adjust.py`.
 * The console never multiplies a rate by a percentage itself — a figure computed
 * here would be a figure the report cannot trace, and S11 blocks exactly that.
 */
export const comparablesApi = {
  list: (propertyId: string, radiusM?: number) =>
    api.get<unknown>(
      `/comparables?property_id=${encodeURIComponent(propertyId)}` +
        (radiusM ? `&radius_m=${radiusM}` : ''),
    ),

  addAdjustment: (comparableId: string, body: AdjustmentDraft) =>
    api.post<unknown>(`/comparables/${encodeURIComponent(comparableId)}/adjustments`, {
      factor: body.factor,
      pct: body.pct,
      rationale: body.rationale,
    }),

  verify: (comparableId: string, verified: boolean, reason?: string) =>
    api.patch<unknown>(`/comparables/${encodeURIComponent(comparableId)}`, {
      verified,
      rejected_reason: reason ?? null,
    }),
};
