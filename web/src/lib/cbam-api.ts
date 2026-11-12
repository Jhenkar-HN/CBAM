/**
 * Typed client for the CBAM-Ready Emissions Passport FastAPI backend.
 *
 * Configure the backend origin in .env (Vite):
 *   VITE_API_URL=http://localhost:8000
 */

export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
const V1 = `${API_URL}/api/v1`;

export type FieldCategory =
  | "scope1_fuel"
  | "scope2_electricity"
  | "precursor"
  | "production";

export interface ExtractedFieldCandidate {
  field_name: string;
  extracted_value: number;
  unit: string;
  confidence_score: number;
  evidence_page: number;
  evidence_snippet: string;
  bounding_box: string | null;
  field_category: FieldCategory | string | null;
}

export interface DocumentExtractionResult {
  document_hash: string;
  filename: string;
  page_count: number;
  extracted_fields: ExtractedFieldCandidate[];
  file_size_bytes?: number;
}

export interface ExtractedFieldAuditRead {
  id: number;
  document_hash: string;
  field_name: string;
  raw_extracted_value: string | null;
  raw_unit: string | null;
  confidence_score: number;
  evidence_page: number | null;
  evidence_snippet: string | null;
  effective_value: string | null;
  effective_unit: string | null;
  was_overridden: boolean;
  user_override_value: string | null;
  user_override_unit: string | null;
  modified_by_user_id: string | null;
  override_reason: string | null;
  created_at: string;
}

export interface DocumentRecordRead {
  id: number;
  document_hash: string;
  filename: string;
  workspace_id: string;
  page_count: number;
  file_size_bytes: number;
  created_at: string;
}

export interface HumanOverrideRequest {
  document_hash: string;
  field_name: string;
  override_value: number;
  override_unit?: string | null;
  override_reason: string;
  user_id: string;
}

export interface HumanOverrideResponse {
  status: string;
  message: string;
  field_name: string;
  raw_value: string;
  effective_value: string;
  effective_unit: string;
  was_overridden: boolean;
  modified_by: string;
  override_reason: string;
}

export interface FuelCombustionItem {
  fuel_name: string;
  quantity: number;
  unit: string;
  ncv?: number | null;
  ef?: number | null;
  oxidation_factor?: number; // backend default 1.0
  confidence_score?: number;
  is_shared_utility?: boolean;
}

export interface ElectricityConsumptionItem {
  source_name: string;
  consumed_quantity: number;
  unit: string;
  grid_ef_tco2_per_mwh?: number | null;
  confidence_score?: number;
  is_shared_utility?: boolean;
}

export interface PrecursorMaterialItem {
  material_name: string;
  consumed_quantity: number;
  unit: string;
  embedded_see_tco2_per_tonne?: number | null;
  source_type?: string;
  cn_code?: string;
  country_of_origin?: string;
  confidence_score?: number;
  is_fallback?: boolean;
  fallback_markup_pct?: number;
}

export interface ProductionAllocationInput {
  target_product_family: string;
  target_production_quantity: number;
  target_production_unit: string;
  total_facility_production_quantity: number;
  total_facility_production_unit: string;
}

export interface DeterministicCalculationRequest {
  reporting_period_id: number;
  cn_code: string;
  production: ProductionAllocationInput;
  fuels: FuelCombustionItem[];
  electricity: ElectricityConsumptionItem;
  precursors: PrecursorMaterialItem[];
  apply_allocation_to_shared_energy?: boolean;
  run_monte_carlo?: boolean;
  monte_carlo_iterations?: number;
}

export interface UncertaintyBand {
  p5: number;
  p50: number;
  p95: number;
  iterations?: number;
  confidence_interval_pct?: number;
}

export interface DeterministicCalculationResult {
  specific_embedded_emissions_see: number;
  see_unit: string;
  allocated_scope1_direct_tco2: number;
  allocated_scope2_indirect_tco2: number;
  precursor_emissions_tco2: number;
  total_embedded_emissions_tco2: number;
  facility_gross_scope1_tco2: number;
  facility_gross_scope2_tco2: number;
  net_target_production_tonnes: number;
  allocation_factor_alpha: number;
  includes_indirect_delta_cn: boolean;
  data_quality_rating: "ACTUAL_PRIMARY" | "HYBRID_ESTIMATED" | "FALLBACK_DEFAULT" | string;
  uncertainty: UncertaintyBand | null;
  formula_latex: string;
  fallback_notes?: string[];
  input_snapshot?: Record<string, unknown>;
}

export interface RAGCitation {
  document_title: string;
  section_reference: string;
  publication_year: number | null;
  source_url: string | null;
  excerpt: string;
  score: number;
}

export interface RAGQueryResponse {
  query: string;
  answer: string;
  citations: RAGCitation[];
}

export interface PassportExportPayload {
  workspace: Record<string, unknown>;
  calculation: DeterministicCalculationResult;
  uploaded_documents: Record<string, DocumentExtractionResult>;
  overrides?: Record<string, Record<string, unknown>>;
  review_status?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${V1}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function checkHealth(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as { status: string; version: string };
}

export function uploadDocument(
  file: File,
  workspaceId: string,
): Promise<DocumentExtractionResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("workspace_id", workspaceId);
  return request<DocumentExtractionResult>(
    "/documents/upload",
    { method: "POST", body: form },
  );
}

export function overrideField(payload: HumanOverrideRequest): Promise<HumanOverrideResponse> {
  return request<HumanOverrideResponse>("/documents/override", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getDocumentFields(documentHash: string): Promise<ExtractedFieldAuditRead[]> {
  return request<ExtractedFieldAuditRead[]>(`/documents/${documentHash}/fields`);
}

export function listWorkspaceDocuments(workspaceId: string): Promise<DocumentRecordRead[]> {
  return request<DocumentRecordRead[]>(`/documents/workspace/${workspaceId}`);
}

export function calculate(
  payload: DeterministicCalculationRequest,
  saveToDb = true,
): Promise<DeterministicCalculationResult> {
  return request<DeterministicCalculationResult>(
    `/calculations/calculate?save_to_db=${saveToDb}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export function getLatestCalculation(reportingPeriodId: number): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/calculations/period/${reportingPeriodId}/latest`);
}

export function queryRegulatory(
  query: string,
  topK = 3,
  cnCodeFilter?: string,
): Promise<RAGQueryResponse> {
  return request<RAGQueryResponse>("/rag/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK, cn_code_filter: cnCodeFilter ?? null }),
  });
}

async function download(path: string, payload: PassportExportPayload): Promise<Blob> {
  const response = await fetch(`${V1}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`Export failed: HTTP ${response.status}`);
  return response.blob();
}

export function downloadPassportPdf(payload: PassportExportPayload): Promise<Blob> {
  return download("/passport/download-pdf", payload);
}

export function downloadPassportCsv(payload: PassportExportPayload): Promise<Blob> {
  return download("/passport/download-csv", payload);
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
