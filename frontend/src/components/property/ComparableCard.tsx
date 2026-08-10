import { formatMoney } from '@/utils/money';
import { formatDate } from '@/utils/format';
import type { AdjustedComparable } from './types';

interface Props {
  item: AdjustedComparable;
  selected?: boolean;
  onSelect?: () => void;
}

export function ComparableCard({ item, selected, onSelect }: Props) {
  const { comparable: c, adjustedRate, netAdjustmentPct } = item;
  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      className={`w-full rounded border p-3 text-left text-sm ${selected ? 'border-navy bg-mist' : 'border-ink/15'}`}
    >
      <p className="font-medium text-navy">{c.address}</p>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <dt className="text-ink/60">Sale</dt>
        <dd className="text-right font-mono tabular-nums">{formatMoney(c.salePrice, { whole: true })}</dd>
        <dt className="text-ink/60">Date</dt>
        <dd className="text-right">{formatDate(c.saleDate)}</dd>
        <dt className="text-ink/60">Raw rate</dt>
        <dd className="text-right font-mono tabular-nums">{formatMoney(c.ratePerUnit)}</dd>
        <dt className="text-ink/60">Net adjustment</dt>
        <dd className="text-right font-mono tabular-nums">{netAdjustmentPct}%</dd>
        <dt className="font-medium text-ink">Adjusted rate</dt>
        <dd className="text-right font-mono font-medium tabular-nums">{formatMoney(adjustedRate)}</dd>
      </dl>
      {!c.verified ? <p className="mt-2 text-xs text-amber-700">Unverified</p> : null}
    </button>
  );
}
