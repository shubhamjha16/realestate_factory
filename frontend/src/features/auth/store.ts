/**
 * Client state for `auth` — the half-finished sign-in, and nothing else.
 *
 * The session itself lives in `store/sessionStore.ts`, because every feature
 * needs it. What is local here is the MFA token: short-lived, single-purpose,
 * and deliberately not persisted — a reload during the challenge should return
 * to the password form, not resume a half-authenticated state.
 */

import { create } from 'zustand';
import type { AuthStage } from './types';

interface AuthState {
  stage: AuthStage;
  mfaToken: string | null;
  /** Present only while enrolling. Carries the shared secret; never stored. */
  enrolmentUri: string | null;
  error: string | null;

  challenge: (mfaToken: string, enrolmentUri: string | null) => void;
  fail: (message: string) => void;
  reset: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  stage: 'credentials',
  mfaToken: null,
  enrolmentUri: null,
  error: null,

  challenge: (mfaToken, enrolmentUri) =>
    set({
      stage: enrolmentUri ? 'enrolling' : 'mfa',
      mfaToken,
      enrolmentUri,
      error: null,
    }),

  fail: (message) => set({ error: message }),

  reset: () => set({ stage: 'credentials', mfaToken: null, enrolmentUri: null, error: null }),
}));
