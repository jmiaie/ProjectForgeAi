import * as React from 'react';

type CardProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ className = '', ...props }: CardProps) {
  return <div className={`rounded-lg border border-slate-200 bg-white shadow-sm ${className}`} {...props} />;
}
