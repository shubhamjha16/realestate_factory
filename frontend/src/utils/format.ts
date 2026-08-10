export { formatMoney, formatLakhCrore, formatPercent } from './money';
export { formatArea } from './area';

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? '—'
    : d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function formatJobType(jobType: string): string {
  return jobType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** "Draft — not for reliance" until a registered valuer signs it (S13). */
export function statusLabel(status: string): string {
  return status === 'signed' ? 'Signed' : `${formatJobType(status)} — not for reliance`;
}
