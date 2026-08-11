import { ADJUSTMENT_FACTORS, ADJUSTMENT_FACTOR_LABELS } from '@/shared/constants/adjustmentFactors';
import { formatMoney } from '@/utils/money';
import { useAdjustmentDraft } from '../hooks/useAdjustmentDraft';
import type { ComparableDraft } from '../types';

/**
 * The grid a valuer works in, and a reviewer reads line by line.
 *
 * Every cell is two things: a percentage and the reason for it. The reason is
 * not a tooltip afterthought — it is what makes the adjustment reviewable, and
 * the engine refuses a percentage that arrives without one.
 *
 * Adjusted rates are not shown here until the engine returns them. A rate the
 * console multiplied out would be a figure the report cannot trace to a
 * valuation line, which is precisely what S11 blocks.
 */
interface Props {
  comparables: ComparableDraft[];
  adjustedRates?: Record<string, string>;
  onSubmit?: (drafts: ComparableDraft[]) => void;
}

export function EditableAdjustmentGrid({ comparables, adjustedRates, onSubmit }: Props) {
  const { drafts, setAdjustment, problems, canSubmit } = useAdjustmentDraft(comparables);

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <caption className="pb-2 text-left text-ink/70">
            Every adjustment carries a written rationale. An unadjusted mean is not a valuation.
          </caption>
          <thead>
            <tr className="bg-navy text-white">
              <th scope="col" className="px-2 py-1 text-left">Comparable</th>
              <th scope="col" className="px-2 py-1 text-right">Raw rate</th>
              {ADJUSTMENT_FACTORS.map((f) => (
                <th key={f} scope="col" className="px-2 py-1 text-right" title={ADJUSTMENT_FACTOR_LABELS[f]}>
                  {ADJUSTMENT_FACTOR_LABELS[f]}
                </th>
              ))}
              <th scope="col" className="px-2 py-1 text-right">Adjusted rate</th>
            </tr>
          </thead>
          <tbody>
            {drafts.map((c) => (
              <tr key={c.id} className="border-b border-ink/10 align-top">
                <td className="px-2 py-1">
                  <span className="font-medium text-navy">{c.address}</span>
                  <span className="block text-ink/60">{c.saleDate}</span>
                </td>
                <td className="px-2 py-1 text-right font-mono tabular-nums">
                  {formatMoney(c.salePrice, { whole: true })}
                </td>

                {ADJUSTMENT_FACTORS.map((factor) => {
                  const existing = c.adjustments.find((a) => a.factor === factor);
                  const missingReason = Boolean(existing?.pct) && !existing?.rationale.trim();
                  return (
                    <td key={factor} className="px-1 py-1">
                      <label className="sr-only" htmlFor={`${c.id}-${factor}-pct`}>
                        {ADJUSTMENT_FACTOR_LABELS[factor]} adjustment for {c.address}
                      </label>
                      <input
                        id={`${c.id}-${factor}-pct`}
                        inputMode="decimal"
                        value={existing?.pct ?? ''}
                        placeholder="—"
                        onChange={(e) => setAdjustment(c.id, factor, { pct: e.target.value })}
                        className="w-16 rounded border border-ink/20 px-1 py-0.5 text-right font-mono tabular-nums"
                      />
                      <label className="sr-only" htmlFor={`${c.id}-${factor}-why`}>
                        Rationale for the {ADJUSTMENT_FACTOR_LABELS[factor]} adjustment
                      </label>
                      <textarea
                        id={`${c.id}-${factor}-why`}
                        rows={2}
                        value={existing?.rationale ?? ''}
                        placeholder="Why?"
                        aria-invalid={missingReason}
                        onChange={(e) => setAdjustment(c.id, factor, { rationale: e.target.value })}
                        className={`mt-1 w-28 rounded border px-1 py-0.5 ${
                          missingReason ? 'border-red-600' : 'border-ink/20'
                        }`}
                      />
                    </td>
                  );
                })}

                <td className="px-2 py-1 text-right font-mono font-medium tabular-nums">
                  {adjustedRates?.[c.id] ? formatMoney(adjustedRates[c.id]!) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {problems.length > 0 ? (
        <ul role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      ) : null}

      <button
        type="button"
        disabled={!canSubmit}
        onClick={() => onSubmit?.(drafts)}
        className="self-start rounded bg-navy px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        Apply adjustments
      </button>
    </div>
  );
}
