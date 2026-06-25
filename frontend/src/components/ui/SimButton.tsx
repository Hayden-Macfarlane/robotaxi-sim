import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'ghost' | 'danger'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-600',
  ghost:
    'bg-surface-raised hover:bg-surface-header text-text-primary border-border-default',
  danger:
    'bg-transparent hover:bg-red-950 text-red-400 border-red-800 hover:border-red-700',
}

/** Simulation control button with fleet-console styling. */
export function SimButton({ variant = 'ghost', className = '', children, ...props }: Props) {
  return (
    <button
      type="button"
      className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
