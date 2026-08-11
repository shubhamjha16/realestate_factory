import { useState } from 'react';
import { Button, Input } from '@/components/ui';
import { useAuth } from '../hooks/useAuth';

/**
 * The second step. Not optional: the engine issues a challenge rather than a
 * session, so there is nothing to skip to.
 */
export function MfaChallenge() {
  const { verifyMfa, cancel, busy, error, stage, enrolmentUri } = useAuth();
  const [code, setCode] = useState('');
  const enrolling = stage === 'enrolling';

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        void verifyMfa(code);
      }}
    >
      {enrolling && enrolmentUri ? (
        <div className="rounded bg-mist p-3 text-sm text-ink">
          <p className="font-medium text-navy">Set up your authenticator</p>
          <p className="mt-1">
            Add this account to your authenticator app, then enter the code it shows.
          </p>
          {/* Shown once, at enrolment, and never stored — it carries the secret. */}
          <code className="mt-2 block break-all font-mono text-xs">{enrolmentUri}</code>
        </div>
      ) : (
        <p className="text-sm text-ink/70">Enter the code from your authenticator app.</p>
      )}

      <Input
        label="Authentication code"
        inputMode="numeric"
        autoComplete="one-time-code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        required
      />
      {error ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <Button type="submit" loading={busy}>
        {enrolling ? 'Confirm and finish setup' : 'Verify'}
      </Button>
      <Button type="button" variant="ghost" onClick={cancel}>
        Start again
      </Button>
    </form>
  );
}
