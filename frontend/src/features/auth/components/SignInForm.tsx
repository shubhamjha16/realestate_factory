import { useState } from 'react';
import { Button, Input } from '@/components/ui';
import { useAuth } from '../hooks/useAuth';

export function SignInForm() {
  const { signIn, busy, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        void signIn(email, password);
      }}
    >
      <Input
        label="Email"
        type="email"
        autoComplete="username"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <Input
        label="Password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {error ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <Button type="submit" loading={busy}>
        Sign in
      </Button>
    </form>
  );
}
