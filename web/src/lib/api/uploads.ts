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
  output_params: Record<string, unknown>
  step: string
  log: string | null
}

export async function uploadDataset(file: File, accessToken: string): Promise<string> {
  const body = new FormData()
  body.append('base_file', file)

  const response = await fetch(`${API_BASE}/api/v2/uploads/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body,
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new UploadError(data?.detail ?? 'Upload failed')
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
