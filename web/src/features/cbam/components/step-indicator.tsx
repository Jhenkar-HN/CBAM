import { Link } from '@tanstack/react-router'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useCbamStore } from '@/stores/cbam-store'

const STEPS = [
  { to: '/workspace', label: 'Workspace' },
  { to: '/upload', label: 'Upload' },
  { to: '/review', label: 'Review' },
  { to: '/allocation', label: 'Allocation' },
  { to: '/passport', label: 'Passport' },
] as const

/** Which steps already hold the data they are responsible for (not just "earlier than current"). */
function useStepCompletion(): boolean[] {
  const workspace = useCbamStore((state) => state.workspace)
  const documents = useCbamStore((state) => state.documents)
  const reviewStatus = useCbamStore((state) => state.reviewStatus)
  const allocation = useCbamStore((state) => state.allocation)
  const calculation = useCbamStore((state) => state.calculation)
  const hasDocuments = Object.keys(documents).length > 0
  return [
    Boolean(workspace.company_name.trim() && workspace.cn_code.trim()),
    hasDocuments,
    hasDocuments && reviewStatus !== 'Draft',
    Number(allocation.target_production_tonnes) > 0 &&
      Number(allocation.total_facility_production_tonnes) > 0 &&
      allocation.fuel_is_shared !== null &&
      allocation.electricity_is_shared !== null,
    calculation !== null,
  ]
}

export function StepIndicator({ current }: { current: number }) {
  const done = useStepCompletion()
  const completed = done.filter(Boolean).length
  const percent = (completed / STEPS.length) * 100

  return (
    <nav aria-label='Passport workflow' className='mb-6'>
      <div className='mb-2 flex items-center justify-between text-xs font-medium text-muted-foreground'>
        <span>
          Step {current} of {STEPS.length}
        </span>
        <span>
          {completed} of {STEPS.length} complete
        </span>
      </div>
      <div className='mb-3 h-1 overflow-hidden rounded-full bg-muted'>
        <div
          className='h-full rounded-full bg-primary transition-[width] duration-500'
          style={{ width: `${percent}%` }}
        />
      </div>
      <ol className='grid grid-cols-5 gap-1.5 sm:gap-2'>
        {STEPS.map((step, index) => {
          const number = index + 1
          const isCurrent = number === current
          const isDone = done[index]
          return (
            <li key={step.to} className='min-w-0'>
              <Link
                to={step.to}
                aria-current={isCurrent ? 'step' : undefined}
                className={cn(
                  'flex h-10 items-center justify-center gap-2 rounded-lg border px-2 text-sm font-medium transition-colors sm:justify-start sm:px-3',
                  isCurrent &&
                    'border-primary bg-primary text-primary-foreground shadow-sm',
                  !isCurrent &&
                    isDone &&
                    'border-primary/30 bg-primary/5 text-foreground hover:bg-primary/10',
                  !isCurrent &&
                    !isDone &&
                    'border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
              >
                <span
                  className={cn(
                    'flex size-5 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                    isCurrent && 'bg-primary-foreground/20',
                    !isCurrent && isDone && 'bg-primary text-primary-foreground',
                    !isCurrent && !isDone && 'bg-muted'
                  )}
                >
                  {isDone && !isCurrent ? (
                    <Check className='size-3' strokeWidth={3} />
                  ) : (
                    number
                  )}
                </span>
                <span className='hidden truncate sm:inline'>{step.label}</span>
              </Link>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
