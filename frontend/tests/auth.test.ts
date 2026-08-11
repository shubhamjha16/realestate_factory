import { beforeEach, describe, expect, it } from 'vitest';
import { useAuthStore } from '@/features/auth';

/**
 * The MFA token is deliberately not persisted: a reload during the challenge
 * must return to the password form rather than resume a half-authenticated
 * state.
 */
describe('auth store', () => {
  beforeEach(() => useAuthStore.getState().reset());

  it('starts at the password step', () => {
    expect(useAuthStore.getState().stage).toBe('credentials');
    expect(useAuthStore.getState().mfaToken).toBeNull();
  });

  it('moves to the challenge when the engine answers with one', () => {
    useAuthStore.getState().challenge('mfa-token', null);
    expect(useAuthStore.getState().stage).toBe('mfa');
    expect(useAuthStore.getState().mfaToken).toBe('mfa-token');
  });

  it('distinguishes enrolment from an ordinary challenge', () => {
    useAuthStore.getState().challenge('mfa-token', 'otpauth://totp/x');
    expect(useAuthStore.getState().stage).toBe('enrolling');
    expect(useAuthStore.getState().enrolmentUri).toBe('otpauth://totp/x');
  });

  it('clears the challenge token on reset', () => {
    useAuthStore.getState().challenge('mfa-token', 'otpauth://totp/x');
    useAuthStore.getState().reset();
    expect(useAuthStore.getState().mfaToken).toBeNull();
    expect(useAuthStore.getState().enrolmentUri).toBeNull();
    expect(useAuthStore.getState().stage).toBe('credentials');
  });

  it('nothing about the session reaches storage', () => {
    useAuthStore.getState().challenge('mfa-token', null);
    expect(Object.keys(localStorage)).toHaveLength(0);
    expect(Object.keys(sessionStorage)).toHaveLength(0);
  });
});
