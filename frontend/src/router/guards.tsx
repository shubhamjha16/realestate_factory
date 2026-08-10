import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useSessionStore } from '@/store';
import { ROUTES } from '@/shared/constants/routes';
import type { Role } from '@/shared/constants/roles';

/**
 * Presentation only. Every one of these decisions is made again, and made
 * properly, at the repository layer (S5) — a guard that the console enforces and
 * the engine does not is not access control.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const user = useSessionStore((s) => s.user);
  return user ? <>{children}</> : <Navigate to={ROUTES.signin} replace />;
}

export function RequireRole({ roles, children }: { roles: readonly Role[]; children: ReactNode }) {
  const user = useSessionStore((s) => s.user);
  if (!user) return <Navigate to={ROUTES.signin} replace />;
  return roles.includes(user.role) ? <>{children}</> : <Navigate to={ROUTES.dashboard} replace />;
}
