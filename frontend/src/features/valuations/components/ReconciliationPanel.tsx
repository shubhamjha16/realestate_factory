import { ValueRangeBar } from '@/components/property';
import { formatMoney } from '@/utils/money';
import { ApproachCard } from './ApproachCard';
import type { ReconciliationView } from '../types';

/**
 * The three approaches side by side, and the figure they reconcile to.
 *
 * The weights are displayed and summed on screen. If they do not sum to 1 the
 * engine has already refused the conclusion — showing the sum here is so a
 * valuer sees why before they submit, not so the console decides.
 */
export function ReconciliationPanel({ view }: { view: ReconciliationView }) {
  const weightSum = view.approaches.reduce((total, a) => total + Number(a.weight), 0);
  const weightsBalance = Math.abs(weightSum - 1) < 0.0001;

  return (
    <section className="flex flex-col gap-6">
      <header>
        <h2 className="text-lg font-medium text-navy">Reconciliation</h2>
        <p className="text-sm text-ink/70">
          {view.basis.replace(/_/g, ' ')} value on an {view.premise.replace(/_/g, ' ')} premise
          {view.divergencePct ? ` · approaches diverge by ${view.divergencePct}%` : null}
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {view.approaches.map((a) => (
          <ApproachCard key={a.method} approach={a} />
        ))}
      </div>

      {!weightsBalance ? (
        <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          The weights sum to {weightSum.toFixed(4)}, not 1. Weights that do not sum to 1 are not
          weights, and the engine will refuse this conclusion.
        </p>
      ) : null}

      <div className="rounded border border-navy/20 p-4">
        <ValueRangeBar
          range={{
            low: view.valueRangeLow,
            concluded: view.concludedValue,
            high: view.valueRangeHigh,
            currency: 'INR',
          }}
        />
        <p className="mt-4 text-center font-mono text-2xl tabular-nums text-navy">
          {formatMoney(view.concludedValue, { whole: true })}
        </p>
        <p className="text-center text-xs text-ink/60">
          Concluded on the weighted evidence above. Draft — not for reliance until signed.
        </p>
      </div>
    </section>
  );
}
