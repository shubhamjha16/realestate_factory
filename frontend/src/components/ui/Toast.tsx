import type { ReactNode } from 'react';

export type ToastTone = 'info' | 'success' | 'error';

const TONES: Record<ToastTone, string> = {
  info: 'bg-mist text-navy',
  success: 'bg-green-100 text-green-900',
  error: 'bg-red-100 text-red-900',
};

export function Toast({ tone = 'info', children }: { tone?: ToastTone; children: ReactNode }) {
  return (
    <div role="status" aria-live="polite" className={`rounded px-4 py-3 text-sm ${TONES[tone]}`}>
      {children}
    </div>
  );
}
