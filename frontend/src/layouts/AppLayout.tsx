import { Outlet } from 'react-router-dom';
import { ErrorBoundary } from '@/components/feedback';

export function AppLayout() {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-ink/10 px-6 py-3">
        <span className="font-semibold text-navy">Real Estate Factory</span>
      </header>
      <main className="p-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
