import { formatLakhCrore, formatMoney } from '@/utils/money';
import type { ValueRange } from './types';

/**
 * A valuation is a range with a conclusion inside it, not a single number — the
 * bar exists so the console never presents the conclusion without its spread.
 */
export function ValueRangeBar({ range }: { range: ValueRange }) {
  const low = Number(range.low);
  const high = Number(range.high);
  const concluded = Number(range.concluded);
  const position = high > low ? ((concluded - low) / (high - low)) * 100 : 50;

  return (
    <figure>
      <div className="relative h-3 rounded-full bg-mist" role="presentation">
        <div
          className="absolute top-1/2 h-5 w-1 -translate-y-1/2 rounded bg-navy"
          style={{ left: `${Math.min(Math.max(position, 0), 100)}%` }}
        />
      </div>
      <figcaption className="mt-2 flex justify-between font-mono text-xs tabular-nums text-ink/70">
        <span>{formatLakhCrore(range.low)}</span>
        <span className="font-medium text-navy">{formatMoney(range.concluded, { whole: true })}</span>
        <span>{formatLakhCrore(range.high)}</span>
      </figcaption>
    </figure>
  );
}
