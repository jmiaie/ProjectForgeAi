import * as React from 'react';

type ButtonVariant = 'default' | 'outline';

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

export function Button({ variant = 'default', className = '', ...props }: ButtonProps) {
  const variantClasses =
    variant === 'outline'
      ? 'border border-slate-300 bg-white text-slate-900'
      : 'bg-slate-900 text-white';

  return (
    <button
      className={`rounded-md px-4 py-2 text-sm font-medium transition hover:opacity-90 ${variantClasses} ${className}`}
      {...props}
    />
  );
}
