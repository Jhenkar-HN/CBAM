import { createFileRoute } from '@tanstack/react-router'
import { UploadPage } from '@/features/cbam/upload'

export const Route = createFileRoute('/_authenticated/upload')({
  component: UploadPage,
})

