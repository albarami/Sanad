import React from 'react';
import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'secondary';
  className?: string;
  style?: React.CSSProperties;
}

export function Badge({ children, variant = 'default', className = '', style }: BadgeProps) {
  const baseClasses = 'inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium';
  const variantClasses = {
    default: 'bg-blue-100 text-blue-800',
    secondary: 'bg-gray-100 text-gray-800'
  };

  return (
    <span 
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      style={style}
    >
      {children}
    </span>
  );
} 