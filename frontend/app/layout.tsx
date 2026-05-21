import type { ReactNode } from 'react';

export const metadata = {
  title: 'ProjectForge AI',
  description: 'Universal Agentic Project Management OS',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-100 text-slate-900 antialiased">{children}</body>
    </html>
  );
}
