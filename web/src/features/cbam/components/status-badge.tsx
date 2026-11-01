import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type StatusBadgeProps = {
  label: string
  variant?: 'primary' | 'human' | 'fallback' | 'neutral'
  className?: string
}

const VARIANTS: Record<NonNullable<StatusBadgeProps['variant']>, string> = {
  primary:
    'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200',
  human:
    'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200',
  fallback:
    'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200',
  neutral: 'border-border bg-muted text-muted-foreground',
}

export function StatusBadge({
  label,
  variant = 'neutral',
  className,
}: StatusBadgeProps) {
  return (
    <Badge
      variant='outline'
      className={cn(
        'rounded-md text-[0.7rem] font-semibold tracking-wide uppercase',
        VARIANTS[variant],
        className
      )}
    >
      {label}
    </Badge>
  )
}
