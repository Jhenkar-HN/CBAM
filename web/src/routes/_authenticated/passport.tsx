import { createFileRoute } from '@tanstack/react-router'
import { PassportPage } from '@/features/cbam/passport'

export const Route = createFileRoute('/_authenticated/passport')({
  component: PassportPage,
})

