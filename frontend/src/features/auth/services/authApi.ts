import { api, request, setAuthToken } from '@/global/apiClient';
import type { AuthResponse, SessionUser } from '../types';

export const authApi = {
  signIn: (email: string, password: string) =>
    api.post<AuthResponse>('/auth/signin', { email, password }),

  signUp: (body: Record<string, unknown>) => api.post<AuthResponse>('/auth/signup', body),

  signInWithGoogle: (idToken: string) =>
    api.post<AuthResponse>('/auth/google', { id_token: idToken }),

  /**
   * The MFA step authenticates with the short-lived challenge token, not the
   * session token — there is no session yet. The engine rejects it against any
   * other endpoint, so it cannot be replayed.
   */
  verifyMfa: async (mfaToken: string, code: string) => {
    setAuthToken(mfaToken);
    try {
      return await request<AuthResponse>('/auth/mfa', { method: 'POST', body: { code } });
    } finally {
      setAuthToken(null);
    }
  },

  me: () => api.get<SessionUser>('/auth/me'),
};
