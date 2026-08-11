/**
 * `auth` feature barrel.
 *
 * Another feature imports from here and nowhere else (§3 boundary rule,
 * lint-enforced).
 */

export { SignInPage } from './components/SignInPage';
export { useAuth } from './hooks/useAuth';
export { authApi } from './services/authApi';
export { useAuthStore } from './store';
export type { AuthResponse, AuthStage, SessionUser } from './types';
