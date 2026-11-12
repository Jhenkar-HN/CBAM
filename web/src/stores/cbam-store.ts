import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type {
  DocumentExtractionResult,
  DeterministicCalculationResult,
} from '@/lib/cbam-api'

export type Workspace = {
  company_name: string
  installation_name: string
  installation_id: string
  country: string
  cn_code: string
  target_product_family: string
  reporting_period: string
  reporting_period_id: number
  includes_indirect: boolean
  fuel_name: string
  precursor_cn_code: string
  precursor_material_name: string
  precursor_country: string
}

export type Allocation = {
  target_production_tonnes: number | null
  total_facility_production_tonnes: number | null
  fuel_is_shared: boolean | null
  electricity_is_shared: boolean | null
}

export type FieldOverride = {
  document_hash: string
  field_name: string
  override_value: number
  override_unit: string
  override_reason: string
  user_id: string
  raw_value: number
  raw_unit: string
  updated_at: string
  api_synced: boolean
}

export type ReviewStatus = 'Draft' | 'User-Confirmed' | 'Expert-Reviewed'

type CbamState = {
  workspace: Workspace
  allocation: Allocation
  documents: Record<string, DocumentExtractionResult>
  overrides: Record<string, FieldOverride>
  calculation: DeterministicCalculationResult | null
  reviewStatus: ReviewStatus
  setWorkspace: (workspace: Partial<Workspace>) => void
  setAllocation: (allocation: Partial<Allocation>) => void
  addDocument: (document: DocumentExtractionResult) => void
  removeDocument: (documentHash: string) => void
  setOverride: (key: string, override: FieldOverride) => void
  clearOverride: (key: string) => void
  setCalculation: (calculation: DeterministicCalculationResult | null) => void
  setReviewStatus: (status: ReviewStatus) => void
  reset: () => void
}

export const DEFAULT_WORKSPACE: Workspace = {
  company_name: '',
  installation_name: '',
  installation_id: '',
  country: '',
  cn_code: '',
  target_product_family: '',
  reporting_period: '',
  reporting_period_id: 0,
  includes_indirect: false,
  fuel_name: '',
  precursor_cn_code: '',
  precursor_material_name: '',
  precursor_country: '',
}

export const DEFAULT_ALLOCATION: Allocation = {
  target_production_tonnes: null,
  total_facility_production_tonnes: null,
  fuel_is_shared: null,
  electricity_is_shared: null,
}

export const overrideKey = (documentHash: string, fieldName: string) =>
  `${documentHash}_${fieldName}`

export const useCbamStore = create<CbamState>()(
  persist(
    (set) => ({
      workspace: DEFAULT_WORKSPACE,
      allocation: DEFAULT_ALLOCATION,
      documents: {},
      overrides: {},
      calculation: null,
      reviewStatus: 'Draft',
      setWorkspace: (workspace) =>
        set((state) => ({ workspace: { ...state.workspace, ...workspace } })),
      setAllocation: (allocation) =>
        set((state) => ({ allocation: { ...state.allocation, ...allocation } })),
      addDocument: (document) =>
        set((state) => ({
          documents: { ...state.documents, [document.document_hash]: document },
          reviewStatus: 'Draft',
        })),
      removeDocument: (documentHash) =>
        set((state) => {
          const documents = { ...state.documents }
          delete documents[documentHash]
          return { documents }
        }),
      setOverride: (key, override) =>
        set((state) => ({
          overrides: { ...state.overrides, [key]: override },
          reviewStatus: 'Draft',
        })),
      clearOverride: (key) =>
        set((state) => {
          const overrides = { ...state.overrides }
          delete overrides[key]
          return { overrides }
        }),
      setCalculation: (calculation) => set({ calculation }),
      setReviewStatus: (reviewStatus) => set({ reviewStatus }),
      reset: () =>
        set({
          workspace: DEFAULT_WORKSPACE,
          allocation: DEFAULT_ALLOCATION,
          documents: {},
          overrides: {},
          calculation: null,
          reviewStatus: 'Draft',
        }),
    }),
    { name: 'cbam-passport-store-real-data-v2', version: 2 },
  ),
)

/** Effective value for a field, preferring a human override when present. */
export function effectiveField(
  document: DocumentExtractionResult,
  fieldName: string,
  overrides: Record<string, FieldOverride>,
) {
  const field = document.extracted_fields.find((f) => f.field_name === fieldName)
  const override = overrides[overrideKey(document.document_hash, fieldName)]
  if (!field) return null
  return {
    field,
    override: override ?? null,
    value: override ? override.override_value : field.extracted_value,
    unit: override ? override.override_unit : field.unit,
  }
}
