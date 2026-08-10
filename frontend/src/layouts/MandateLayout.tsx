import { Outlet, useParams } from 'react-router-dom';
import { ErrorBoundary } from '@/components/feedback';

/**
 * Everything inside a mandate is scoped to it. The scoping that matters is
 * enforced at the repository layer (S5) — this only keeps the id in the URL so
 * a reviewer can share a link to exactly what they are looking at.
 */
export function MandateLayout() {
  const { mandateId } = useParams<{ mandateId: string }>();
  return (
    <section aria-label={`Mandate ${mandateId ?? ''}`}>
      <ErrorBoundary>
        <Outlet />
      </ErrorBoundary>
    </section>
  );
}
