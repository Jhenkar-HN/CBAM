import { createFileRoute } from '@tanstack/react-router'
import { WorkspacePage } from '@/features/cbam/workspace'

export const Route = createFileRoute('/_authenticated/workspace')({
  component: WorkspacePage,
})

