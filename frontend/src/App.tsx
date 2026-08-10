import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppRouter } from '@/router';
import { ErrorBoundary } from '@/components/feedback';

/**
 * Server state is not client state: everything fetched lives here, in TanStack
 * Query. Zustand holds only what the user is doing right now.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        // A 404 is how the engine denies a cross-firm read (S5). Retrying it is
        // pointless and looks like probing.
        const status = (error as { status?: number }).status;
        if (status && status < 500) return false;
        return failureCount < 2;
      },
    },
  },
});

export function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppRouter />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
