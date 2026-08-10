import { isNotFound, isQuotaExhausted, messageFor } from '@/global/errors';

/**
 * A tenancy denial is a 404 by design (S5), so it reads as "no such thing"
 * rather than "exists, but not yours" — which would itself leak.
 */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = isNotFound(error)
    ? 'Not found.'
    : isQuotaExhausted(error)
      ? 'Your plan’s limit for this period is used up. Nothing was charged for this request.'
      : messageFor(error);

  return (
    <div role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-900">
      <p>{message}</p>
      {onRetry ? (
        <button onClick={onRetry} className="mt-2 underline">
          Try again
        </button>
      ) : null}
    </div>
  );
}
