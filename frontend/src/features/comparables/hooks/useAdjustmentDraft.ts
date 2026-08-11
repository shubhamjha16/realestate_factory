import { useCallback, useMemo, useState } from 'react';
import { ADJUSTMENT_FACTORS, type AdjustmentFactor } from '@/shared/constants/adjustmentFactors';
import type { AdjustmentDraft, ComparableDraft } from '../types';

/**
 * The editable grid's local state.
 *
 * It holds what the valuer is typing and validates what can be validated on the
 * client — a percentage out of range, a missing rationale. It computes no rates:
 * the adjusted rate comes from the engine, because a figure the console derived
 * is a figure the report cannot trace back to a valuation line.
 */
export function useAdjustmentDraft(initial: ComparableDraft[]) {
  const [drafts, setDrafts] = useState<ComparableDraft[]>(initial);

  const setAdjustment = useCallback(
    (comparableId: string, factor: AdjustmentFactor, patch: Partial<AdjustmentDraft>) => {
      setDrafts((current) =>
        current.map((c) => {
          if (c.id !== comparableId) return c;
          const existing = c.adjustments.find((a) => a.factor === factor);
          const next: AdjustmentDraft = {
            factor,
            pct: patch.pct ?? existing?.pct ?? '0',
            rationale: patch.rationale ?? existing?.rationale ?? '',
          };
          const others = c.adjustments.filter((a) => a.factor !== factor);
          return {
            ...c,
            adjustments: [...others, next].sort(
              (a, b) =>
                ADJUSTMENT_FACTORS.indexOf(a.factor) - ADJUSTMENT_FACTORS.indexOf(b.factor),
            ),
          };
        }),
      );
    },
    [],
  );

  const removeAdjustment = useCallback((comparableId: string, factor: AdjustmentFactor) => {
    setDrafts((current) =>
      current.map((c) =>
        c.id === comparableId
          ? { ...c, adjustments: c.adjustments.filter((a) => a.factor !== factor) }
          : c,
      ),
    );
  }, []);

  /**
   * What the engine would refuse, surfaced before the round trip. The engine
   * refuses it again regardless — this only saves the valuer a submission.
   */
  const problems = useMemo(() => {
    const found: string[] = [];
    for (const c of drafts) {
      for (const a of c.adjustments) {
        if (!a.rationale.trim()) {
          found.push(`${c.address}: the ${a.factor} adjustment has no rationale`);
        }
        const pct = Number(a.pct);
        if (!Number.isFinite(pct)) {
          found.push(`${c.address}: the ${a.factor} adjustment is not a number`);
        } else if (Math.abs(pct) > 50) {
          found.push(
            `${c.address}: a ${a.factor} adjustment of ${a.pct}% means this is not a comparable`,
          );
        }
      }
    }
    return found;
  }, [drafts]);

  return { drafts, setAdjustment, removeAdjustment, problems, canSubmit: problems.length === 0 };
}
