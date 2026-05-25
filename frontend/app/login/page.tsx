'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  apiGet,
  apiPost,
  setAuthToken,
  type AuthSession,
  type AuthStatus,
} from '@/lib/api';

export default function LoginPage() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<AuthStatus | undefined>();
  const [session, setSession] = useState<AuthSession | undefined>();
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      setAuthToken(token);
    }
    apiGet<AuthStatus>('/api/v1/auth/status')
      .then(setStatus)
      .catch(() => setStatus(undefined));
    apiGet<AuthSession>('/api/v1/auth/me')
      .then(setSession)
      .catch(() => setSession(undefined));
  }, [searchParams]);

  const mockLogin = async () => {
    setMessage('');
    try {
      const result = await apiPost<AuthSession>('/api/v1/auth/mock-login', {
        actor_id: 'enterprise-user',
        email: 'enterprise-user@example.com',
        role: 'admin',
      });
      setAuthToken(result.token);
      setSession(result);
      setMessage('Mock SSO session created.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Login failed');
    }
  };

  const logout = async () => {
    setMessage('');
    try {
      await apiPost('/api/v1/auth/logout', {});
      setAuthToken(null);
      setSession(undefined);
      setMessage('Signed out.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Logout failed');
    }
  };

  return (
    <main className="page">
      <Card className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Identity</div>
            <h1>Sign in</h1>
            <p className="muted">OIDC SSO scaffolding with mock login for development.</p>
          </div>
        </div>
        <div className="stack">
          {status ? (
            <p className="muted">
              OIDC {status.enabled ? 'enabled' : 'disabled'}
              {status.mock_mode ? ' · mock mode' : ''}
              {status.issuer ? ` · ${status.issuer}` : ''}
            </p>
          ) : null}
          {session ? (
            <>
              <p className="muted">
                Signed in as {session.email || session.actor_id} ({session.role})
              </p>
              <Button variant="outline" onClick={logout}>
                Sign out
              </Button>
            </>
          ) : (
            <Button onClick={mockLogin} disabled={!status?.enabled || !status.mock_mode}>
              Mock SSO login
            </Button>
          )}
          {message ? <p className="muted">{message}</p> : null}
        </div>
      </Card>
    </main>
  );
}
