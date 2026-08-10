import { create } from 'zustand';
import { setAuthToken } from '@/global/apiClient';
import type { Role } from '@/shared/constants/roles';

export interface SessionUser {
  id: string;
  firmId: string;
  email: string;
  role: Role;
  /** Present only on registered valuers; the sign-off gate reads it (S13). */
  ibbiRegNo: string | null;
  valuerAssetClass: string | null;
  mfaEnabled: boolean;
}

interface SessionState {
  user: SessionUser | null;
  token: string | null;
  signIn: (user: SessionUser, token: string) => void;
  signOut: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  user: null,
  token: null,
  signIn: (user, token) => {
    setAuthToken(token);
    set({ user, token });
  },
  signOut: () => {
    setAuthToken(null);
    set({ user: null, token: null });
  },
}));
