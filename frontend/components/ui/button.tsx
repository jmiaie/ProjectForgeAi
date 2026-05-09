import * as React from 'react';

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'default' | 'outline';
};

export function Button({ className = '', variant = 'default', ...props }: ButtonProps) {
  return <button className={`button button-${variant} ${className}`} {...props} />;
}
