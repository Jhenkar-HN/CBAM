import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { Main } from '@/components/layout/main'
import { overrideField, type ExtractedFieldCandidate } from '@/lib/cbam-api'
import {
  overrideKey,
  useCbamStore,
  type FieldOverride,
} from '@/stores/cbam-store'
import { CbamTopBar } from '../components/cbam-top-bar'
import { PageHeader } from '../components/page-header'
import { StatusBadge } from '../components/status-badge'
import { StepIndicator } from '../components/step-indicator'

function confidenceVariant(score: number) {
  if (score >= 0.9) return 'primary' as const
  if (score >= 0.7) return 'human' as const
  return 'fallback' as const
}

function prettyField(name: string) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
}

function FieldReview({
  documentHash,
  field,
}: {
  documentHash: string
  field: ExtractedFieldCandidate
}) {
  const overrides = useCbamStore((state) => state.overrides)
  const setOverride = useCbamStore((state) => state.setOverride)
  const existing = overrides[overrideKey(documentHash, field.field_name)]

  const [value, setValue] = useState(
    String(existing?.override_value ?? field.extracted_value)
  )
  const [unit, setUnit] = useState(existing?.override_unit ?? field.unit)
  const [reason, setReason] = useState(existing?.override_reason ?? '')
  const [reviewer, setReviewer] = useState(existing?.user_id ?? '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    const numeric = Number(value)
    if (!Number.isFinite(numeric)) {
      toast.error('Enter a numeric value.')
      return
    }
    if (numeric === field.extracted_value && unit === field.unit) {
      toast.info('Value matches the extracted candidate; nothing to record.')
      return
    }
    if (!reason.trim()) {
      toast.error('A justification is required for an audit override.')
      return
    }
    if (!reviewer.trim()) {
      toast.error('Enter the actual reviewer name or ID.')
      return
    }
    setSaving(true)
    let synced = false
    try {
      await overrideField({
        document_hash: documentHash,
        field_name: field.field_name,
        override_value: numeric,
        override_unit: unit,
        override_reason: reason.trim(),
        user_id: reviewer.trim(),
      })
      synced = true
    } catch {
      synced = false
    }
    const payload: FieldOverride = {
      document_hash: documentHash,
      field_name: field.field_name,
      override_value: numeric,
      override_unit: unit,
      override_reason: reason.trim(),
      user_id: reviewer.trim(),
      raw_value: field.extracted_value,
      raw_unit: field.unit,
      updated_at: new Date().toISOString(),
      api_synced: synced,
    }
    setOverride(overrideKey(documentHash, field.field_name), payload)
    setSaving(false)
    if (synced) {
      toast.success('Override saved to the backend audit ledger.')
    } else {
      toast.warning(
        'Override applied in this workspace, but the backend did not confirm it.'
      )
    }
  }

  return (
    <Card>
      <CardHeader className='gap-2'>
        <div className='flex flex-wrap items-center justify-between gap-2'>
          <CardTitle className='text-base'>
            {prettyField(field.field_name)}
          </CardTitle>
          <div className='flex flex-wrap items-center gap-2'>
            <StatusBadge
              label={`${Math.round(field.confidence_score * 100)}% confidence`}
              variant={confidenceVariant(field.confidence_score)}
            />
            {existing ? (
              <StatusBadge label='Human overridden' variant='human' />
            ) : (
              <StatusBadge label='AI extracted' variant='primary' />
            )}
          </div>
        </div>
        <CardDescription>
          Page {field.evidence_page} · Category {field.field_category ?? '—'}
        </CardDescription>
      </CardHeader>
      <CardContent className='grid gap-6 md:grid-cols-2'>
        <div className='space-y-3'>
          <p className='text-xs font-semibold tracking-wide text-muted-foreground uppercase'>
            Source evidence
          </p>
          <blockquote className='rounded-md border-s-4 border-muted-foreground/40 bg-muted/40 p-3 text-sm italic'>
            {field.evidence_snippet || 'No snippet captured.'}
          </blockquote>
          <p className='text-sm'>
            Extracted:{' '}
            <span className='font-mono'>
              {field.extracted_value} {field.unit}
            </span>
          </p>
          {existing && (
            <div className='rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100'>
              <p className='font-semibold'>Audit diff</p>
              <p className='font-mono text-xs'>
                raw {existing.raw_value} {existing.raw_unit} → effective{' '}
                {existing.override_value} {existing.override_unit}
              </p>
              <p className='mt-1 text-xs'>
                {existing.user_id} · {existing.override_reason}
              </p>
              {!existing.api_synced && (
                <p className='mt-1 text-xs'>
                  Not synced to the backend ledger.
                </p>
              )}
            </div>
          )}
        </div>

        <div className='space-y-3'>
          <div className='grid grid-cols-2 gap-3'>
            <div className='space-y-2'>
              <Label htmlFor={`value-${field.field_name}`}>Value</Label>
              <Input
                id={`value-${field.field_name}`}
                type='number'
                step='any'
                value={value}
                onChange={(event) => setValue(event.target.value)}
              />
            </div>
            <div className='space-y-2'>
              <Label htmlFor={`unit-${field.field_name}`}>Unit</Label>
              <Input
                id={`unit-${field.field_name}`}
                value={unit}
                onChange={(event) => setUnit(event.target.value)}
              />
            </div>
          </div>
          <div className='space-y-2'>
            <Label htmlFor={`reason-${field.field_name}`}>
              Justification
            </Label>
            <Textarea
              id={`reason-${field.field_name}`}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder='Required when changing the extracted value or unit.'
              rows={2}
            />
          </div>
          <div className='space-y-2'>
            <Label htmlFor={`reviewer-${field.field_name}`}>Reviewer ID</Label>
            <Input
              id={`reviewer-${field.field_name}`}
              value={reviewer}
              onChange={(event) => setReviewer(event.target.value)}
              placeholder='Enter your name or reviewer ID'
            />
          </div>
          <Button onClick={() => void save()} disabled={saving}>
            {saving ? 'Saving…' : 'Save audit override'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function ReviewPage() {
  const documents = useCbamStore((state) => state.documents)
  const reviewStatus = useCbamStore((state) => state.reviewStatus)
  const setReviewStatus = useCbamStore((state) => state.setReviewStatus)
  const hashes = Object.keys(documents)
  const [selected, setSelected] = useState<string>(hashes[0] ?? '')

  const document = documents[selected]

  return (
    <>
      <CbamTopBar />
      <Main>
        <StepIndicator current={3} />
        <PageHeader
          title='Review extraction'
          description='Compare each candidate against its source snippet. Corrections are logged with a reviewer and justification for verifiers.'
        >
          <StatusBadge
            label={reviewStatus}
            variant={reviewStatus === 'Draft' ? 'neutral' : 'primary'}
          />
        </PageHeader>

        {hashes.length === 0 ? (
          <Card>
            <CardContent className='py-10 text-center text-sm text-muted-foreground'>
              No documents uploaded yet.{' '}
              <Link to='/upload' className='text-primary underline'>
                Upload a record
              </Link>{' '}
              to begin review.
            </CardContent>
          </Card>
        ) : (
          <>
            <div className='mb-4 max-w-xl space-y-2'>
              <Label>Source document</Label>
              <Select value={selected} onValueChange={setSelected}>
                <SelectTrigger>
                  <SelectValue placeholder='Select a document' />
                </SelectTrigger>
                <SelectContent>
                  {hashes.map((hash) => (
                    <SelectItem key={hash} value={hash}>
                      {documents[hash].filename} · {hash.slice(0, 10)}…
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {document && (
              <div className='space-y-4'>
                <Card>
                  <CardContent className='grid gap-4 py-4 sm:grid-cols-3'>
                    <div>
                      <p className='text-xs font-semibold tracking-wide text-muted-foreground uppercase'>
                        File
                      </p>
                      <p className='text-sm font-medium'>
                        {document.filename}
                      </p>
                    </div>
                    <div>
                      <p className='text-xs font-semibold tracking-wide text-muted-foreground uppercase'>
                        Fields
                      </p>
                      <p className='text-sm font-medium'>
                        {document.extracted_fields.length}
                      </p>
                    </div>
                    <div className='min-w-0'>
                      <p className='text-xs font-semibold tracking-wide text-muted-foreground uppercase'>
                        SHA-256
                      </p>
                      <p className='truncate font-mono text-xs'>
                        {document.document_hash}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {document.extracted_fields.length === 0 ? (
                  <Card>
                    <CardContent className='py-8 text-sm text-muted-foreground'>
                      No activity fields were extracted from this file. Check
                      document quality or upload a text-based record.
                    </CardContent>
                  </Card>
                ) : (
                  document.extracted_fields.map((field) => (
                    <FieldReview
                      key={`${selected}-${field.field_name}`}
                      documentHash={selected}
                      field={field}
                    />
                  ))
                )}

                <Separator />
                <div className='flex flex-wrap items-center justify-between gap-3'>
                  <p className='text-sm text-muted-foreground'>
                    Confirming marks this evidence pack as reviewed by a named
                    person. It does not certify emissions.
                  </p>
                  <div className='flex gap-2'>
                    <Button
                      variant='outline'
                      onClick={() => {
                        setReviewStatus('Draft')
                        toast.success('Marked as draft.')
                      }}
                    >
                      Mark draft
                    </Button>
                    <Button
                      onClick={() => {
                        setReviewStatus('User-Confirmed')
                        toast.success('Evidence pack marked user-confirmed.')
                      }}
                    >
                      Mark user-confirmed
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </Main>
    </>
  )
}

