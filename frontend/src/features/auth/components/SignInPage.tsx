import { useAuth } from '../hooks/useAuth';
import { MfaChallenge } from './MfaChallenge';
import { SignInForm } from './SignInForm';

export function SignInPage() {
  const { stage } = useAuth();
  const challenging = stage === 'mfa' || stage === 'enrolling';

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-lg font-medium text-navy">
        {challenging ? 'Two-factor authentication' : 'Sign in'}
      </h2>
      {challenging ? <MfaChallenge /> : <SignInForm />}
    </div>
  );
}
