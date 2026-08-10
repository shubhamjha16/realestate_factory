import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

const STYLES: Record<Variant, string> = {
  primary: 'bg-navy text-white hover:bg-navy/90',
  secondary: 'bg-mist text-navy hover:bg-mist/70',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  ghost: 'bg-transparent text-navy hover:bg-mist',
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
  children: ReactNode;
}

export function Button({ variant = 'primary', loading, children, disabled, ...rest }: Props) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`rounded px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${STYLES[variant]}`}
    >
      {loading ? 'Working…' : children}
    </button>
  );
}
