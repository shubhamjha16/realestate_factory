import { ADJUSTMENT_FACTORS } from '@/shared/constants/adjustmentFactors';
import type { AdjustedComparable } from './types';

/**
 * The adjustment grid — the report's defensibility, and the thing a reviewer,
 * a bank or a tribunal actually asks to see.
 *
 * Editable in S7, exported to XLSX with live formulas in S15 so a reviewer can
 * change an adjustment and watch the rate move. S1 fixes the column order,
 * which is the order the adjustments are applied in and must match what the
 * report describes.
 */
export interface AdjustmentGridProps {
  items: readonly AdjustedComparable[];
  editable?: boolean;
  onAdjust?: (comparableId: string, factor: string, pct: string, rationale: string) => void;
}

export function AdjustmentGrid({ items }: AdjustmentGridProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs">
        <caption className="pb-2 text-left text-ink/60">
          Every adjustment carries a written rationale. An unadjusted mean is not a valuation.
        </caption>
        <thead>
          <tr className="bg-navy text-white">
            <th scope="col" className="px-2 py-1 text-left">Comparable</th>
            {ADJUSTMENT_FACTORS.map((f) => (
              <th key={f} scope="col" className="px-2 py-1 text-right">{f}</th>
            ))}
            <th scope="col" className="px-2 py-1 text-right">Net</th>
            <th scope="col" className="px-2 py-1 text-right">Adjusted rate</th>
          </tr>
        </thead>
        <tbody>
          {items.map(({ comparable, adjustments, netAdjustmentPct, adjustedRate }) => (
            <tr key={comparable.id} className="border-b border-ink/10">
              <td className="px-2 py-1">{comparable.address}</td>
              {ADJUSTMENT_FACTORS.map((f) => {
                const a = adjustments.find((x) => x.factor === f);
                return (
                  <td key={f} className="px-2 py-1 text-right font-mono tabular-nums" title={a?.rationale}>
                    {a ? `${a.pct}%` : '—'}
                  </td>
                );
              })}
              <td className="px-2 py-1 text-right font-mono tabular-nums">{netAdjustmentPct}%</td>
              <td className="px-2 py-1 text-right font-mono font-medium tabular-nums">{adjustedRate}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
