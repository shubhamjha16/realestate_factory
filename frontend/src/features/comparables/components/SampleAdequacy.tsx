import type { GridStats } from '../types';

/**
 * What the engine will refuse, shown before it refuses it.
 *
 * These are not warnings the valuer can dismiss. The spread check in particular
 * is blocking: if the adjusted rates still disagree, the adjustments did not
 * explain the differences between the sales, and their mean has nothing
 * underneath it.
 */
interface Props {
  stats: GridStats;
  minSample: number;
  maxSpreadPct: number;
}

export function SampleAdequacy({ stats, minSample, maxSpreadPct }: Props) {
  const tooFew = stats.count < minSample;
  const spread = stats.spreadPct === null ? null : Number(stats.spreadPct);
  const tooWide = spread !== null && spread > maxSpreadPct;

  if (!tooFew && !tooWide) {
    return (
      <p className="rounded bg-green-50 px-3 py-2 text-sm text-green-900">
        {stats.count} comparables, adjusted rates within {stats.spreadPct}%. The evidence supports
        a conclusion.
      </p>
    );
  }

  return (
    <div role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-900">
      {tooFew ? (
        <p>
          {stats.count} comparable{stats.count === 1 ? '' : 's'} is below the minimum of {minSample}.
          A rate derived from fewer is not supported by the evidence, and no adjustment makes it so.
        </p>
      ) : null}
      {tooWide ? (
        <p>
          The adjusted rates span {stats.spreadPct}%, beyond the {maxSpreadPct}% threshold. After
          adjustment these sales still disagree, which means the adjustments did not explain the
          differences between them.
        </p>
      ) : null}
    </div>
  );
}
