import { DataGrid, type Column } from '@/components/ui';
import { EmptyState } from '@/components/feedback';
import { formatMoney } from '@/utils/money';
import { formatDate } from '@/utils/format';
import type { RentRollLine } from './types';

/**
 * The total must tie to the sum of the lines to the rupee (S16). That tie is
 * computed by the engine and displayed here; the console never sums money.
 */
interface Props {
  lines: readonly RentRollLine[];
  totalContracted: string;
  totalEffective: string;
}

const COLUMNS: readonly Column<RentRollLine>[] = [
  { key: 'unit', header: 'Unit', render: (r) => r.unitNo },
  { key: 'tenant', header: 'Tenant', render: (r) => r.tenant ?? '—' },
  { key: 'area', header: 'Area', numeric: true, render: (r) => r.area },
  { key: 'contracted', header: 'Contracted', numeric: true, render: (r) => formatMoney(r.contractedRent) },
  { key: 'effective', header: 'Effective', numeric: true, render: (r) => formatMoney(r.effectiveRent) },
  { key: 'expiry', header: 'Expiry', render: (r) => formatDate(r.leaseEnd) },
  { key: 'wault', header: 'WAULT (m)', numeric: true, render: (r) => r.waultMonths ?? '—' },
];

export function RentRollTable({ lines, totalContracted, totalEffective }: Props) {
  return (
    <div>
      <DataGrid
        columns={COLUMNS}
        rows={lines}
        rowKey={(r) => r.id}
        empty={<EmptyState title="No rent roll lines" description="Import a lease schedule to build one." />}
      />
      <p className="mt-2 text-right font-mono text-sm tabular-nums">
        Contracted {formatMoney(totalContracted)} · Effective {formatMoney(totalEffective)}
      </p>
    </div>
  );
}
