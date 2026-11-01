import { useCallback, useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Download, Loader2, RefreshCw } from 'lucide-react'
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

const FUEL = {
  fuel_name: 'Furnace Oil',
  unit: 'litre',
  ncv: 0.0402,
  ef: 0.0774,
  oxidation_factor: 1,
}

const GRID_EF = 0.716

function buildRequest(
  workspace: Workspace,
  allocation: Allocation,
  documents: Record<string, DocumentExtractionResult>,
  overrides: Record<string, FieldOverride>
): DeterministicCalculationRequest {
  const quantities = { electricity: 250000, fuel: 15000, precursor: 520 }
  const confidences = { electricity: 0.96, fuel: 0.95, precursor: 0.95 }

  for (const document of Object.values(documents)) {
    for (const field of document.extracted_fields) {
      const override = overrides[overrideKey(document.document_hash, field.field_name)]
      const value = Number(override?.override_value ?? field.extracted_value)
      if (!Number.isFinite(value)) continue
      const name = field.field_name.toLowerCase()
      if (name.includes('electricity')) {
        quantities.electricity = Math.max(0, value)
        confidences.electricity = field.confidence_score
      } else if (name.includes('furnace') || name.includes('fuel')) {
        quantities.fuel = Math.max(0.001, value)
        confidences.fuel = field.confidence_score
      } else if (name.includes('precursor')) {
        quantities.precursor = Math.max(0.001, value)
        confidences.precursor = field.confidence_score
      }
    }
  }

  const target = Number(allocation.target_production_tonnes) || 500
  const total = Math.max(
    target,
    Number(allocation.total_facility_production_tonnes) || 625
  )

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
        ...FUEL,
        quantity: quantities.fuel,
        confidence_score: confidences.fuel,
        is_shared_utility: true,
      },
    ],
    electricity: {
      source_name: 'State Grid / PPA',
      consumed_quantity: quantities.electricity,
      unit: 'kWh',
      grid_ef_tco2_per_mwh: GRID_EF,
      confidence_score: confidences.electricity,
      is_shared_utility: true,
    },
    precursors: [
      {
        material_name: 'Steel Wire Rod',
        consumed_quantity: quantities.precursor,
        unit: 'tonne',
        embedded_see_tco2_per_tonne: 1.85,
        source_type: 'supplier_actual',
        cn_code: '7228 30',
        confidence_score: confidences.precursor,
      },
    ],
    apply_allocation_to_shared_energy:
      allocation.apply_allocation_to_shared_energy,
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
  const [error, setError] = useState<string | null>(null)
  const [exporting, setExporting] = useState<'pdf' | 'csv' | null>(null)

  const run = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await calculate(
        buildRequest(workspace, allocation, documents, overrides)
      )
      setCalculation(result)
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'Calculation request failed.'
      )
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

  const quality = calculation?.data_quality_rating ?? 'ACTUAL_PRIMARY'
  const fallback = quality === 'FALLBACK_DEFAULT'

  return (
    <>
      <CbamTopBar />
      <Main>
        <StepIndicator current={5} />
        <PageHeader
          title='Emissions Passport'
          description={`${workspace.company_name} · ${workspace.installation_name} · CN ${workspace.cn_code}`}
        >
          <Button variant='outline' onClick={() => void run()} disabled={loading}>
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
              {error}
              <span className='mt-1 block text-xs'>
                Start the backend with{' '}
                <code>uvicorn app.main:app --port 8000</code> and ensure it is
                reachable at {API_URL}.
              </span>
            </AlertDescription>
          </Alert>
        )}

        {!calculation ? (
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

