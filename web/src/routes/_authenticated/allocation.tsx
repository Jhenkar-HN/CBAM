import { createFileRoute } from '@tanstack/react-router'
import { AllocationPage } from '@/features/cbam/allocation'

export const Route = createFileRoute('/_authenticated/allocation')({
  component: AllocationPage,
})

