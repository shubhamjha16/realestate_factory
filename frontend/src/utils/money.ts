/**
 * Money on the console.
 *
 * The engine computes in `Decimal` and sends strings. The console never does
 * arithmetic on money and never calls `toFixed` on it — a rate multiplied in
 * JavaScript is a figure that will not reconcile with the report, and a report
 * whose total contradicts its lines is the failure this repository is built to
 * prevent. Format for display; compute nowhere but the engine.
 */

/** A rupee amount as the API sends it: a decimal string, never a number. */
export type Money = string;

const INR = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const INR_WHOLE = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

export function formatMoney(amount: Money, opts: { whole?: boolean } = {}): string {
  const n = Number(amount);
  if (!Number.isFinite(n)) return '—';
  return (opts.whole ? INR_WHOLE : INR).format(n);
}

/**
 * Indian numbering for figures a valuer reads at a glance. Display only: the
 * exact figure is always available alongside via `formatMoney`.
 *
 * Scaling and rounding happen on the decimal string, not on a float. `toFixed`
 * would be shorter and wrong: ₹1,06,50,000 is 1.065 crore, and `(10650000 / 1e7)
 * .toFixed(2)` gives "1.06" because 1.065 has no exact binary representation.
 * Half-up on the digits, matching the engine's ROUNDING_POLICY.
 */
export function formatLakhCrore(amount: Money): string {
  if (!/^-?\d+(\.\d+)?$/.test(amount.trim())) return '—';
  const negative = amount.trim().startsWith('-');
  const digitsOnly = amount.trim().replace(/^-/, '').replace('.', '');
  const intLength = amount.trim().replace(/^-/, '').split('.')[0]!.length;

  const magnitude = digitsOnly.replace(/^0+/, '').length - (digitsOnly.length - intLength);
  const [shift, suffix] = magnitude > 7 ? [7, ' Cr'] : magnitude > 5 ? [5, ' L'] : [0, ''];
  if (shift === 0) {
    const n = Number(amount);
    return Number.isFinite(n) ? INR_WHOLE.format(n) : '—';
  }
  return `${negative ? '-' : ''}₹${shiftAndRound(digitsOnly, intLength - shift, 2)}${suffix}`;
}

/** Move the decimal point of a digit string to `point`, then round half-up to `dp`. */
function shiftAndRound(digits: string, point: number, dp: number): string {
  let d = digits;
  let p = point;
  if (p <= 0) {
    d = '0'.repeat(1 - p) + d;
    p = 1;
  }
  const kept = `${d.slice(0, p)}${d.slice(p, p + dp).padEnd(dp, '0')}`;
  const next = d.charAt(p + dp);
  const rounded = next && next >= '5' ? addOne(kept) : kept;
  const padded = rounded.padStart(dp + 1, '0');
  return `${padded.slice(0, padded.length - dp)}.${padded.slice(padded.length - dp)}`;
}

function addOne(value: string): string {
  const out = value.split('');
  for (let i = out.length - 1; i >= 0; i -= 1) {
    if (out[i] !== '9') {
      out[i] = String(Number(out[i]) + 1);
      return out.join('');
    }
    out[i] = '0';
  }
  return `1${out.join('')}`;
}

export function formatPercent(pct: string | number, dp = 2): string {
  const n = Number(pct);
  return Number.isFinite(n) ? `${n.toFixed(dp)}%` : '—';
}

/** Compare without parsing to float, so ordering a rent roll never loses paise. */
export function compareMoney(a: Money, b: Money): number {
  const [ai, af = ''] = a.replace('-', '').split('.');
  const [bi, bf = ''] = b.replace('-', '').split('.');
  const sign = (a.startsWith('-') ? -1 : 1) - (b.startsWith('-') ? -1 : 1);
  if (sign !== 0) return sign;
  if (ai!.length !== bi!.length) return ai!.length - bi!.length;
  const cmp = ai!.localeCompare(bi!);
  return cmp !== 0 ? cmp : af.padEnd(2, '0').localeCompare(bf.padEnd(2, '0'));
}
