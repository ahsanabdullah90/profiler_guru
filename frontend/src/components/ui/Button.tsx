'use client';

import React from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'destructive' | 'link';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-strong)] text-white border border-[var(--brand-primary-strong)] disabled:opacity-40 disabled:cursor-not-allowed',
  secondary:
    'bg-[var(--bg-surface-raised)] hover:bg-[var(--border-subtle)] text-[var(--text-primary)] border border-[var(--border-strong)] disabled:opacity-40 disabled:cursor-not-allowed',
  ghost:
    'bg-transparent hover:bg-[var(--bg-surface-raised)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-transparent disabled:opacity-40 disabled:cursor-not-allowed',
  destructive:
    'bg-[var(--error)] hover:opacity-90 text-white border border-[var(--error)] disabled:opacity-40 disabled:cursor-not-allowed',
  link:
    'bg-transparent text-[var(--brand-primary)] hover:underline border border-transparent disabled:opacity-40',
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'h-7 px-2.5 text-[11px] gap-1.5 rounded-md',
  md: 'h-9 px-3.5 text-xs gap-2 rounded-lg',
  lg: 'h-11 px-5 text-sm gap-2.5 rounded-lg',
};

export default function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  iconLeft,
  iconRight,
  className = '',
  children,
  disabled,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2 ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
      {...rest}
    >
      {loading ? (
        <span
          className="w-3.5 h-3.5 rounded-full border-2 border-current border-t-transparent animate-spin"
          aria-hidden="true"
        />
      ) : (
        iconLeft
      )}
      <span>{children}</span>
      {!loading && iconRight}
    </button>
  );
}
