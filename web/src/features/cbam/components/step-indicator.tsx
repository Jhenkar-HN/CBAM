import { Link } from '@tanstack/react-router'
import { cn } from '@/lib/utils'

const STEPS = [
  { to: '/workspace', label: 'Workspace' },
  { to: '/upload', label: 'Upload' },
  { to: '/review', label: 'Review' },
  { to: '/allocation', label: 'Allocation' },
  { to: '/passport', label: 'Passport' },
] as const

export function StepIndicator({ current }: { current: number }) {
  return (
    <nav aria-label='Passport workflow' className='mb-6 overflow-x-auto'>
      <ol className='flex min-w-max items-center gap-2'>
        {STEPS.map((step, index) => {
          const number = index + 1
          const isCurrent = number === current
          const isDone = number < current
          return (
            <li key={step.to} className='flex items-center gap-2'>
              <Link
                to={step.to}
                className={cn(
                  'flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors',
                  isCurrent &&
                    'border-primary bg-primary text-primary-foreground',
                  isDone &&
                    'border-primary/40 bg-primary/10 text-primary hover:bg-primary/15',
                  !isCurrent &&
                    !isDone &&
                    'border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
              >
                <span
                  className={cn(
                    'flex size-5 items-center justify-center rounded-full text-xs font-semibold',
                    isCurrent && 'bg-primary-foreground/20',
                    isDone && 'bg-primary/20',
                    !isCurrent && !isDone && 'bg-muted'
                  )}
                >
                  {number}
                </span>
                {step.label}
              </Link>
              {number < STEPS.length && (
                <span aria-hidden className='h-px w-6 bg-border' />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
