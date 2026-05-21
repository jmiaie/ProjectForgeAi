'use client';

import { useState } from 'react';
import { apiFetch, setAuthToken } from '@/lib/api';

export default function AuthPanel() {
  const [email, setEmail] = useState('dev@example.com');
  const [password, setPassword] = useState('changeme');
  const [name, setName] = useState('Dev User');
  const [message, setMessage] = useState<string | null>(null);

  async function register() {
    try {
      const data = await apiFetch<{ access_token: string }>('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name: name }),
      });
      setAuthToken(data.access_token);
      setMessage('Registered and signed in.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Register failed');
    }
  }

  async function login() {
    try {
      const data = await apiFetch<{ access_token: string }>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setAuthToken(data.access_token);
      setMessage('Signed in.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Login failed');
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold">Sign in</h2>
      <div className="flex flex-col gap-2 text-sm">
        <input
          className="rounded border px-2 py-1"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
        />
        <input
          className="rounded border px-2 py-1"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
        />
        <input
          className="rounded border px-2 py-1"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
        />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={register}
            className="rounded bg-slate-800 px-3 py-1 text-white"
          >
            Register
          </button>
          <button
            type="button"
            onClick={login}
            className="rounded border border-slate-300 px-3 py-1"
          >
            Login
          </button>
        </div>
        {message && <p className="text-slate-600">{message}</p>}
      </div>
    </div>
  );
}
