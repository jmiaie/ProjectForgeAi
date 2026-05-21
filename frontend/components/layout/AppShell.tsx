'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import { useAuth } from '@/lib/auth';

const NAV = [
  { href: '/projects', label: 'Projects' },
  { href: '/settings/connections', label: 'Connections' },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-8">
            <Link href="/" className="text-lg font-bold text-brand-900">
              ProjectForge AI
            </Link>
            <nav className="hidden gap-1 sm:flex">
              {NAV.map((item) => {
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`rounded-md px-3 py-2 text-sm font-medium ${
                      active
                        ? 'bg-brand-50 text-brand-700'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {user ? (
              <>
                <span className="hidden text-slate-600 sm:inline">{user.email}</span>
                <button
                  type="button"
                  onClick={logout}
                  className="rounded-md border border-slate-200 px-3 py-1.5 hover:bg-slate-50"
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="rounded-md bg-brand-600 px-3 py-1.5 font-medium text-white hover:bg-brand-700"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
    </div>
  );
}
