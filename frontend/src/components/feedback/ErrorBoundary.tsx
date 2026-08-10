import { Component, type ErrorInfo, type ReactNode } from 'react';
import { scrubForTelemetry } from '@/utils/redactDisplay';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Sentry lands in S19. Whatever reports, it reports scrubbed: a stack that
    // carries an owner name or a survey number into a third party is the exact
    // leak S20 exists to prevent.
    console.error('Unhandled error', scrubForTelemetry({ message: error.message, componentStack: info.componentStack }));
  }

  render(): ReactNode {
    if (this.state.error) {
      return this.props.fallback ?? (
        <div role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          Something went wrong in this view. Reload the page; the job itself is unaffected.
        </div>
      );
    }
    return this.props.children;
  }
}
