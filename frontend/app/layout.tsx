import type { ReactNode } from 'react';

import './globals.css';
import AppShell from '@/components/layout/AppShell';
import { AuthProvider } from '@/lib/auth';

export const metadata = {
  title: 'ProjectForge AI',
  description: 'Universal Agentic Project Management OS',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
