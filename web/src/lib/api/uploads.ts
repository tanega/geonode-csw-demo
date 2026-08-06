const API_BASE = import.meta.env.VITE_GEONODE_API_BASE

export class UploadError extends Error {}

export type ExecutionStatus = 'ready' | 'running' | 'finished' | 'failed'

export interface ExecutionRequest {
  user: string
  status: ExecutionStatus
  func_name: string
  created: string
  finished: string | null
  last_updated: string
  input_params: Record<string, unknown>
  // Populated by the importer's perform_last_step once processing
  // finishes (geonode/upload/handlers/base.py) -- this is the only place
  // the newly-created resource's pk shows up.
  output_params: { resources?: { id: number; detail_url: string }[] } & Record<string, unknown>
  step: string
  log: string | null
}

export function getFinishedResourceId(execution: ExecutionRequest): number | null {
  return execution.output_params.resources?.[0]?.id ?? null
}

export interface ResourceMetadataPayload {
  title?: string
  abstract?: string
  attribution?: string
  data_quality_statement?: string
  category?: { identifier: string }
}

// title/abstract/attribution/data_quality_statement/category are all
// writable on the general resource endpoint (confirmed against
// ResourceBaseSerializer). No metadata-specific endpoint exists or is
// needed for these.
export async function patchResourceMetadata(
  resourceId: number,
  accessToken: string,
  payload: ResourceMetadataPayload,
): Promise<void> {
  // /api/v2/datasets/<pk>/, not the generic /api/v2/resources/<pk>/: GeoNode
  // uses django-modeltranslation for title/abstract/data_quality_statement,
  // which shadows them with per-language columns (title_en, ...) added to
  // the Dataset model's own table (layers_dataset). The generic resources
  // endpoint operates on the plain ResourceBase model and writes the
  // legacy, untranslated column on base_resourcebase instead -- silently
  // accepted (200, echoed back correctly) but never actually read back by
  // Dataset.title/.abstract/.data_quality_statement or anything else in
  // the app. Verified by direct DB round-trip during development.
  const response = await fetch(`${API_BASE}/api/v2/datasets/${resourceId}/`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new UploadError(data?.detail ?? 'Failed to save metadata')
  }
}

// No public GeoNode API creates Links (ResourceBaseSerializer's `links`
// field is read-only) -- goes through the custom endpoint added alongside
// this feature (geonode-custom/uploads_api/views.py::SourceLinkView),
// which stores it the same way the GeoParquet auto-mirror does.
export async function createSourceLink(resourceId: number, accessToken: string, url: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v2/custom/source-link/`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ resource: resourceId, url }),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new UploadError(data?.detail ?? 'Failed to save source link')
  }
}

const PARQUET_EXTENSIONS = ['.parquet', '.geoparquet']

export function isParquetFile(file: File): boolean {
  const name = file.name.toLowerCase()
  return PARQUET_EXTENSIONS.some((ext) => name.endsWith(ext))
}

export async function uploadDataset(file: File, accessToken: string): Promise<string> {
  const body = new FormData()
  body.append('base_file', file)

  // GeoNode's importer has no handler for GeoParquet: it's routed through
  // a custom endpoint that converts to GeoPackage first (see
  // geonode-custom/uploads_api/views.py::ConvertParquetView), then
  // forwards into the same importer flow every other format uses.
  const endpoint = isParquetFile(file)
    ? `${API_BASE}/api/v2/custom/convert-parquet/`
    : `${API_BASE}/api/v2/uploads/upload`

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body,
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new UploadError(data?.errors?.join(', ') ?? data?.detail ?? 'Upload failed')
  }

  const data = await response.json()
  return data.execution_id
}

export async function getExecutionStatus(
  executionId: string,
  accessToken: string,
): Promise<ExecutionRequest> {
  const response = await fetch(`${API_BASE}/api/v2/resource-service/execution-status/${executionId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })

  if (!response.ok) throw new UploadError('Failed to fetch upload status')

  return response.json()
}
