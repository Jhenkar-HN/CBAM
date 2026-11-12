import { useCallback, useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  ArrowRight,
  Circle,
  ClipboardList,
  Download,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Main } from '@/components/layout/main'
import {
  API_URL,
  calculate,
  downloadPassportCsv,
  downloadPassportPdf,
  saveBlob,
  type DeterministicCalculationRequest,
  type PassportExportPayload,
} from '@/lib/cbam-api'
import {
  overrideKey,
  useCbamStore,
  type Allocation,
  type FieldOverride,
  type Workspace,
} from '@/stores/cbam-store'
import type { DocumentExtractionResult } from '@/lib/cbam-api'
import { CbamTopBar } from '../components/cbam-top-bar'
import { PageHeader } from '../components/page-header'
import { StatusBadge } from '../components/status-badge'
import { StepIndicator } from '../components/step-indicator'

type StepRoute = '/workspace' | '/upload' | '/allocation'
type MissingInput = { label: string; step: StepRoute }

const STEP_NAMES: Record<StepRoute, string> = {
  '/workspace': '1 · Workspace',
  '/upload': '2 · Upload',
  '/allocation': '4 · Allocation',
}

/** Inputs the operator still has to provide; shown as a checklist, not as a failure. */
class MissingInputsError extends Error {
  constructor(public readonly items: MissingInput[]) {
    super(`Calculation needs actual records for: ${items.map((item) => item.label.toLowerCase()).join(', ')}.`)
    this.name = 'MissingInputsError'
  }
}

function MissingInputsCard({ items }: { items: MissingInput[] }) {
  const groups = (Object.keys(STEP_NAMES) as StepRoute[])
    .map((step) => ({ step, items: items.filter((item) => item.step === step) }))
    .filter((group) => group.items.length > 0)
  return (
    <Card className='border-amber-300/60 bg-amber-50/60 dark:border-amber-500/30 dark:bg-amber-500/5'>
      <CardHeader>
        <CardTitle className='flex items-center gap-2'>
          <ClipboardList className='size-5 text-amber-600 dark:text-amber-400' />
          A few inputs are still needed
        </CardTitle>
        <CardDescription>
          The passport is calculated only from your actual records. Complete
          these items and it will calculate automatically.
        </CardDescription>
      </CardHeader>
      <CardContent className='grid gap-4 md:grid-cols-3'>
        {groups.map((group) => (
          <div key={group.step} className='rounded-lg border bg-card p-4'>
            <div className='mb-3 flex items-center justify-between gap-2'>
              <p className='text-sm font-semibold'>{STEP_NAMES[group.step]}</p>
              <Button asChild size='sm' variant='outline' className='h-7'>
                <Link to={group.step}>
                  Open <ArrowRight className='size-3.5' />
                </Link>
              </Button>
            </div>
            <ul className='space-y-1.5'>
              {group.items.map((item) => (
                <li key={item.label} className='flex items-start gap-2 text-sm text-muted-foreground'>
                  <Circle className='mt-1 size-2.5 shrink-0 text-amber-500' />
                  {item.label}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function buildRequest(
  workspace: Workspace,
  allocation: Allocation,
  documents: Record<string, DocumentExtractionResult>,
  overrides: Record<string, FieldOverride>
): DeterministicCalculationRequest {
  const fields = Object.values(documents).flatMap((document) =>
    document.extracted_fields.map((field) => {
      const override = overrides[overrideKey(document.document_hash, field.field_name)]
      return {
        name: field.field_name.toLowerCase(),
        value: Number(override?.override_value ?? field.extracted_value),
        unit: override?.override_unit || field.unit,
        confidence: field.confidence_score,
      }
    })
  )
  const first = (predicate: (name: string) => boolean) =>
    fields.find((field) => predicate(field.name) && Number.isFinite(field.value))
  const electricity = first((name) => name.includes('electricity'))
  const fuel = first((name) => name.includes('fuel') || name.includes('furnace_oil') || name.includes('diesel') || name.includes('gas_quantity'))
  const precursor = first((name) => (name.includes('precursor') || name.includes('wire_rod')) && name.includes('quantity'))
  const precursorSee = first((name) => (name.includes('precursor') || name.includes('wire_rod')) && (name.includes('see') || name.includes('emission') || name.includes('factor')))
  const target = Number(allocation.target_production_tonnes)
  const total = Number(allocation.total_facility_production_tonnes)

  const checks: [boolean, MissingInput][] = [
    [!workspace.company_name.trim(), { label: 'Company details', step: '/workspace' }],
    [!workspace.installation_id.trim(), { label: 'Installation details', step: '/workspace' }],
    [!workspace.cn_code.trim(), { label: 'Product CN code', step: '/workspace' }],
    [!workspace.fuel_name, { label: 'Fuel type recorded on the bill', step: '/workspace' }],
    [!workspace.precursor_cn_code, { label: 'Precursor CN code from the supplier record', step: '/workspace' }],
    [!workspace.precursor_material_name, { label: 'Precursor material name from the supplier record', step: '/workspace' }],
    [!workspace.precursor_country, { label: 'Precursor country of origin', step: '/workspace' }],
    [!electricity, { label: 'Electricity consumption from an uploaded record', step: '/upload' }],
    [!fuel, { label: 'Fuel consumption from an uploaded record', step: '/upload' }],
    [!precursor, { label: 'Precursor quantity from a supplier record', step: '/upload' }],
    [!precursorSee, { label: 'Supplier-declared precursor SEE', step: '/upload' }],
    [!(target > 0), { label: 'Target production quantity', step: '/allocation' }],
    [!(total > 0), { label: 'Total installation production quantity', step: '/allocation' }],
    [allocation.fuel_is_shared === null, { label: 'Fuel allocation basis', step: '/allocation' }],
    [allocation.electricity_is_shared === null, { label: 'Electricity allocation basis', step: '/allocation' }],
  ]
  const missing = checks.filter(([isMissing]) => isMissing).map(([, item]) => item)
  if (missing.length) throw new MissingInputsError(missing)
  if (target > total) throw new Error('Target production cannot exceed total installation production.')
  if (workspace.country.trim().toLowerCase() !== 'india') {
    throw new Error('Select a country with an applicable sourced grid factor. This pilot currently has a sourced factor for India only.')
  }

  return {
    reporting_period_id: workspace.reporting_period_id,
    cn_code: workspace.cn_code,
    production: {
      target_product_family: workspace.target_product_family,
      target_production_quantity: target,
      target_production_unit: 'tonne',
      total_facility_production_quantity: total,
      total_facility_production_unit: 'tonne',
    },
    fuels: [
      {
        fuel_name: workspace.fuel_name,
        quantity: fuel!.value,
        unit: fuel!.unit,
        confidence_score: fuel!.confidence,
        is_shared_utility: allocation.fuel_is_shared!,
      },
    ],
    electricity: {
      source_name: 'Indian National Grid (CEA v19 Baseline)',
      consumed_quantity: electricity!.value,
      unit: electricity!.unit,
      confidence_score: electricity!.confidence,
      is_shared_utility: allocation.electricity_is_shared!,
    },
    precursors: [
      {
        material_name: workspace.precursor_material_name,
        consumed_quantity: precursor!.value,
        unit: precursor!.unit,
        embedded_see_tco2_per_tonne: precursorSee!.value,
        source_type: 'supplier_actual',
        cn_code: workspace.precursor_cn_code,
        country_of_origin: workspace.precursor_country,
        confidence_score: precursorSee!.confidence,
      },
    ],
    apply_allocation_to_shared_energy: true,
    run_monte_carlo: true,
    monte_carlo_iterations: 2000,
  }
}

function fmt(value: number, digits = 2) {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function UncertaintyBand({
  p5,
  p50,
  p95,
  see,
}: {
  p5: number
  p50: number
  p95: number
  see: number
}) {
  const low = Math.min(p5, p50, p95, see)
  const high = Math.max(p5, p50, p95, see)
  const span = Math.max(high - low, Math.abs(high) * 0.04, 1e-6)
  const start = ((p5 - low) / span) * 100
  const end = ((p95 - low) / span) * 100
  const median = ((p50 - low) / span) * 100
  const point = ((see - low) / span) * 100
  const clamp = (n: number) => Math.max(0, Math.min(100, n))

  return (
    <div className='space-y-3'>
      <div className='relative h-3 rounded-full bg-muted'>
        <div
          className='absolute inset-y-0 rounded-full bg-emerald-500/70'
          style={{ left: `${clamp(start)}%`, width: `${clamp(end - start)}%` }}
        />
        <div
          className='absolute -top-1 h-5 w-0.5 bg-slate-900 dark:bg-slate-100'
          style={{ left: `${clamp(median)}%` }}
        />
        <div
          className='absolute -top-1.5 size-3 rounded-full border-2 border-background bg-primary'
          style={{ left: `calc(${clamp(point)}% - 6px)` }}
        />
      </div>
      <div className='grid grid-cols-3 gap-3 text-center'>
        <div>
          <p className='text-xs text-muted-foreground uppercase'>P5 low</p>
          <p className='font-semibold tabular-nums'>{fmt(p5, 4)}</p>
        </div>
        <div>
          <p className='text-xs text-muted-foreground uppercase'>P50 median</p>
          <p className='font-semibold tabular-nums'>{fmt(p50, 4)}</p>
        </div>
        <div>
          <p className='text-xs text-muted-foreground uppercase'>P95 high</p>
          <p className='font-semibold tabular-nums'>{fmt(p95, 4)}</p>
        </div>
      </div>
    </div>
  )
}

export function PassportPage() {
  const workspace = useCbamStore((state) => state.workspace)
  const allocation = useCbamStore((state) => state.allocation)
  const documents = useCbamStore((state) => state.documents)
  const overrides = useCbamStore((state) => state.overrides)
  const reviewStatus = useCbamStore((state) => state.reviewStatus)
  const calculation = useCbamStore((state) => state.calculation)
  const setCalculation = useCbamStore((state) => state.setCalculation)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<{ message: string; backend: boolean } | null>(null)
  const [missing, setMissing] = useState<MissingInput[]>([])
  const [exporting, setExporting] = useState<'pdf' | 'csv' | null>(null)

  const run = useCallback(async () => {
    setError(null)
    setMissing([])
    let request: DeterministicCalculationRequest
    try {
      request = buildRequest(workspace, allocation, documents, overrides)
    } catch (cause) {
      if (cause instanceof MissingInputsError) setMissing(cause.items)
      else setError({ message: cause instanceof Error ? cause.message : 'Inputs are invalid.', backend: false })
      return
    }
    setLoading(true)
    try {
      setCalculation(await calculate(request, false))
    } catch (cause) {
      setError({
        message: cause instanceof Error ? cause.message : 'Calculation request failed.',
        backend: true,
      })
    } finally {
      setLoading(false)
    }
  }, [workspace, allocation, documents, overrides, setCalculation])

  useEffect(() => {
    void run()
    // Re-run only when the effective inputs change.
  }, [run])

  const exportPack = async (kind: 'pdf' | 'csv') => {
    if (!calculation) return
    setExporting(kind)
    const payload: PassportExportPayload = {
      workspace: { ...workspace },
      calculation,
      uploaded_documents: documents,
      overrides,
      review_status: reviewStatus,
    }
    const suffix = workspace.cn_code.replace(/ /g, '_')
    try {
      if (kind === 'pdf') {
        const blob = await downloadPassportPdf(payload)
        saveBlob(blob, `CBAM_Emissions_Passport_${suffix}.pdf`)
      } else {
        const blob = await downloadPassportCsv(payload)
        saveBlob(blob, `CBAM_Audit_Evidence_Ledger_${suffix}.csv`)
      }
    } catch (cause) {
      toast.error(
        cause instanceof Error ? cause.message : 'Export failed.'
      )
    } finally {
      setExporting(null)
    }
  }

  const quality = calculation?.data_quality_rating ?? 'UNKNOWN'
  const fallback = quality === 'FALLBACK_DEFAULT'

  return (
    <>
      <CbamTopBar />
      <Main>
        <StepIndicator current={5} />
        <PageHeader
          title='Emissions Passport'
          description={
            workspace.company_name.trim()
              ? [
                  workspace.company_name,
                  workspace.installation_name,
                  workspace.cn_code && `CN ${workspace.cn_code}`,
                ]
                  .filter(Boolean)
                  .join(' · ')
              : 'Embedded-emissions summary with traceable inputs, deterministic calculations, and uncertainty ranges.'
          }
        >
          <Button variant='outline' onClick={() => void run()} disabled={loading || missing.length > 0}>
            {loading ? (
              <Loader2 className='size-4 animate-spin' />
            ) : (
              <RefreshCw className='size-4' />
            )}
            Recalculate
          </Button>
        </PageHeader>

        {error && (
          <Alert variant='destructive' className='mb-4'>
            <AlertTitle>Calculation unavailable</AlertTitle>
            <AlertDescription>
              {error.message}
              {error.backend && (
                <span className='mt-1 block text-xs'>
                  Check that the backend is running (
                  <code>uvicorn app.main:app --port 8000</code>) and reachable
                  at {API_URL}.
                </span>
              )}
            </AlertDescription>
          </Alert>
        )}

        {missing.length > 0 ? (
          <MissingInputsCard items={missing} />
        ) : !calculation ? (
          <Card>
            <CardContent className='flex flex-col items-center gap-3 py-12 text-sm text-muted-foreground'>
              {loading ? (
                <>
                  <Loader2 className='size-6 animate-spin' />
                  Calculating emissions and uncertainty interval…
                </>
              ) : (
                <>
                  No calculation yet.
                  <Button variant='outline' onClick={() => void run()}>
                    Run calculation
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        ) : (
          <>
            <div className='mb-4 flex flex-wrap items-center gap-2'>
              <StatusBadge
                label={fallback ? 'Default fallback used' : quality.replace(/_/g, ' ')}
                variant={fallback ? 'fallback' : 'primary'}
              />
              <StatusBadge
                label={
                  calculation.includes_indirect_delta_cn
                    ? 'Scope 2 included'
                    : 'Scope 2 exempt'
                }
                variant='neutral'
              />
              <StatusBadge
                label={reviewStatus}
                variant={reviewStatus === 'Draft' ? 'human' : 'primary'}
              />
            </div>

            <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
              <Card>
                <CardHeader className='pb-2'>
                  <CardDescription>Specific embedded emissions</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className='text-2xl font-bold tabular-nums'>
                    {fmt(calculation.specific_embedded_emissions_see, 4)}
                  </p>
                  <p className='text-xs text-muted-foreground'>tCO₂e / tonne</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className='pb-2'>
                  <CardDescription>Scope 1 · direct</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className='text-2xl font-bold tabular-nums'>
                    {fmt(calculation.allocated_scope1_direct_tco2)}
                  </p>
                  <p className='text-xs text-muted-foreground'>tCO₂</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className='pb-2'>
                  <CardDescription>Scope 2 · indirect</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className='text-2xl font-bold tabular-nums'>
                    {fmt(calculation.allocated_scope2_indirect_tco2)}
                  </p>
                  <p className='text-xs text-muted-foreground'>tCO₂</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className='pb-2'>
                  <CardDescription>Precursor emissions</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className='text-2xl font-bold tabular-nums'>
                    {fmt(calculation.precursor_emissions_tco2)}
                  </p>
                  <p className='text-xs text-muted-foreground'>tCO₂</p>
                </CardContent>
              </Card>
            </div>

            <div className='mt-4 grid gap-4 lg:grid-cols-3'>
              <Card className='lg:col-span-2'>
                <CardHeader>
                  <CardTitle>Statistical uncertainty</CardTitle>
                  <CardDescription>
                    Monte Carlo interval from input confidence and fallback
                    assumptions.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {calculation.uncertainty ? (
                    <UncertaintyBand
                      p5={calculation.uncertainty.p5}
                      p50={calculation.uncertainty.p50}
                      p95={calculation.uncertainty.p95}
                      see={calculation.specific_embedded_emissions_see}
                    />
                  ) : (
                    <p className='text-sm text-muted-foreground'>
                      No uncertainty distribution was returned.
                    </p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Allocation</CardTitle>
                </CardHeader>
                <CardContent className='space-y-3 text-sm'>
                  <div className='flex items-center justify-between'>
                    <span className='text-muted-foreground'>αₚ</span>
                    <span className='font-semibold tabular-nums'>
                      {fmt(calculation.allocation_factor_alpha, 4)}
                    </span>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span className='text-muted-foreground'>
                      Net target production
                    </span>
                    <span className='font-semibold tabular-nums'>
                      {fmt(calculation.net_target_production_tonnes)} t
                    </span>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span className='text-muted-foreground'>
                      Total embedded
                    </span>
                    <span className='font-semibold tabular-nums'>
                      {fmt(calculation.total_embedded_emissions_tco2)} tCO₂
                    </span>
                  </div>
                  <Separator />
                  <Link
                    to='/allocation'
                    className='text-sm text-primary underline'
                  >
                    Adjust allocation
                  </Link>
                </CardContent>
              </Card>
            </div>

            {(calculation.fallback_notes?.length ?? 0) > 0 && (
              <Alert className='mt-4 border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100'>
                <AlertTitle>Fallback disclosure</AlertTitle>
                <AlertDescription>
                  <ul className='list-inside list-disc text-sm'>
                    {calculation.fallback_notes?.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            <Card className='mt-4'>
              <CardHeader>
                <CardTitle>Calculation formula</CardTitle>
                <CardDescription>
                  Deterministic output. No language model participates in the
                  arithmetic.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <pre className='overflow-x-auto rounded-md bg-muted p-3 text-xs'>
                  {calculation.formula_latex || 'Formula unavailable.'}
                </pre>
              </CardContent>
            </Card>

            <Alert className='mt-4 border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100'>
              <AlertTitle>Decision-support prototype</AlertTitle>
              <AlertDescription>
                This passport does not certify emissions or replace an
                accredited independent verifier under EU CBAM rules.
              </AlertDescription>
            </Alert>

            <div className='mt-4 flex flex-wrap gap-2'>
              <Button
                onClick={() => void exportPack('pdf')}
                disabled={exporting !== null}
              >
                <Download className='size-4' />
                {exporting === 'pdf' ? 'Generating…' : 'Download passport PDF'}
              </Button>
              <Button
                variant='outline'
                onClick={() => void exportPack('csv')}
                disabled={exporting !== null}
              >
                <Download className='size-4' />
                {exporting === 'csv' ? 'Generating…' : 'Download evidence CSV'}
              </Button>
            </div>
          </>
        )}
      </Main>
    </>
  )
}

