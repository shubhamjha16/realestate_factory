import { useCallback, useState } from 'react';
import { messageFor } from '@/global/errors';
import { useSessionStore } from '@/store';
import { authApi } from '../services/authApi';
import { useAuthStore } from '../store';
import type { AuthResponse } from '../types';

/**
 * Drives the two-step sign-in.
 *
 * Everything this hook decides is presentation. The engine makes the same
 * decisions again, and makes them properly: a console that lets someone past a
 * check the backend does not enforce has not enforced anything.
 */
export function useAuth() {
  const [busy, setBusy] = useState(false);
  const signInSession = useSessionStore((s) => s.signIn);
  const { challenge, fail, reset, stage, mfaToken, enrolmentUri, error } = useAuthStore();

  const settle = useCallback(
    (response: AuthResponse) => {
      if (response.mfa_required) {
        challenge(response.mfa_token ?? '', response.totp_enrolment_uri ?? null);
        return;
      }
      if (!response.access_token || !response.user) {
        fail('The server returned an incomplete session.');
        return;
      }
      signInSession(
        {
          id: response.user.id,
          firmId: response.user.firm_id,
          email: response.user.email,
          role: response.user.role as never,
          ibbiRegNo: response.user.ibbi_reg_no ?? null,
          valuerAssetClass: response.user.valuer_asset_class ?? null,
          mfaEnabled: response.user.mfa_enabled ?? false,
        },
        response.access_token,
      );
      reset();
    },
    [challenge, fail, reset, signInSession],
  );

  const run = useCallback(
    async (work: () => Promise<AuthResponse>) => {
      setBusy(true);
      try {
        settle(await work());
      } catch (e) {
        fail(messageFor(e));
      } finally {
        setBusy(false);
      }
    },
    [fail, settle],
  );

  return {
    stage,
    error,
    busy,
    enrolmentUri,
    signIn: (email: string, password: string) => run(() => authApi.signIn(email, password)),
    signInWithGoogle: (idToken: string) => run(() => authApi.signInWithGoogle(idToken)),
    verifyMfa: (code: string) => run(() => authApi.verifyMfa(mfaToken ?? '', code)),
    cancel: reset,
  };
}
