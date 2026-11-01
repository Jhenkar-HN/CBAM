import { createFileRoute } from '@tanstack/react-router'
import { ReviewPage } from '@/features/cbam/review'

export const Route = createFileRoute('/_authenticated/review')({
  component: ReviewPage,
})

