'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { useAuth } from '@/lib/auth';

export default function LoginPage() {
  const { login, register, user } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace('/projects');
  }, [user, router]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password, fullName || undefined);
      }
      router.push('/projects');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-3xl font-bold text-slate-900">
        {mode === 'login' ? 'Sign in' : 'Create account'}
      </h1>
      <p className="mt-2 text-sm text-slate-600">
        Authenticate to bind projects to your organization.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {mode === 'register' && (
          <label className="block text-sm">
            <span className="font-medium">Full name</span>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
        )}
        <label className="block text-sm">
          <span className="font-medium">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Password</span>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          />
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-brand-600 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Register'}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-slate-600">
        {mode === 'login' ? 'No account?' : 'Already registered?'}{' '}
        <button
          type="button"
          onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          className="font-medium text-brand-700 hover:underline"
        >
          {mode === 'login' ? 'Register' : 'Sign in'}
        </button>
      </p>

      <p className="mt-6 text-center text-sm">
        <Link href="/projects" className="text-slate-500 hover:underline">
          Continue without signing in
        </Link>
      </p>
    </div>
  );
}
