import { formatLakhCrore, formatMoney } from '@/utils/money';
import type { ApproachView } from '../types';

const METHOD_LABELS: Record<string, string> = {
  sales: 'Sales comparison',
  income: 'Income capitalisation',
  cost: 'Depreciated replacement cost',
};

/**
 * One approach, with its weight and the reason for it.
 *
 * A zero-weighted approach is shown, not hidden: "computed and not relied upon"
 * is itself a finding, and hiding it would make the report look like it
 * considered fewer methods than it did.
 */
export function ApproachCard({ approach }: { approach: ApproachView }) {
  const relied = Number(approach.weight) > 0;

  return (
    <article
      className={`rounded border p-4 ${relied ? 'border-navy/30' : 'border-ink/15 bg-ink/5'}`}
    >
      <header className="flex items-baseline justify-between gap-3">
        <h3 className="font-medium text-navy">{METHOD_LABELS[approach.method] ?? approach.method}</h3>
        <span className="font-mono text-xs tabular-nums text-ink/70">
          {relied ? `${approach.weightPct}%` : 'not relied upon'}
        </span>
      </header>

      <p className="mt-2 font-mono text-lg tabular-nums text-navy">
        {formatMoney(approach.indicatedValue, { whole: true })}
      </p>
      <p className="font-mono text-xs tabular-nums text-ink/60">
        {formatLakhCrore(approach.indicatedValue)}
      </p>

      <p className="mt-3 text-sm text-ink">{approach.rationale}</p>
    </article>
  );
}
