import { readonly, ref } from 'vue'
import { toast } from 'vue-sonner'
import { useAuthStore } from '@/stores/auth'
import {
  uploadDataset,
  getExecutionStatus,
  getFinishedResourceId,
  patchResourceMetadata,
  createSourceLink,
  UploadError,
} from '@/lib/api/uploads'
import type { ExecutionRequest, ExecutionStatus } from '@/lib/api/uploads'

const POLL_INTERVAL_MS = 2000

export interface DatasetUploadPayload {
  file: File
  title: string
  description: string
  category: string
  attribution: string
  caution: string
  sourceLink: string
}

export function useDatasetUpload() {
  const auth = useAuthStore()

  const status = ref<ExecutionStatus | null>(null)
  const error = ref<string | null>(null)
  const submitting = ref(false)

  // GeoNode's orchestrator flips status to "finished" and populates
  // output_params.resources (perform_last_step, see
  // geonode/upload/handlers/base.py) in two separate saves -- a poll can
  // land between them and see "finished" with no resource id yet. Keep
  // polling a bit past "finished" until it shows up, capped so a resource
  // type that genuinely never populates it (if any) doesn't spin forever.
  const MAX_SETTLE_POLLS_AFTER_FINISHED = 10

  async function pollUntilSettled(
    executionId: string,
    accessToken: string,
    pollsAfterFinished = 0,
  ): Promise<ExecutionRequest> {
    const result = await getExecutionStatus(executionId, accessToken)
    status.value = result.status

    if (result.status === 'failed') return result
    if (result.status === 'finished') {
      if (getFinishedResourceId(result) || pollsAfterFinished >= MAX_SETTLE_POLLS_AFTER_FINISHED) return result
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
      return pollUntilSettled(executionId, accessToken, pollsAfterFinished + 1)
    }

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
    return pollUntilSettled(executionId, accessToken)
  }

  // Metadata is applied after the dataset already imported successfully,
  // so a failure here is a warning, not a failed upload -- it stays
  // editable later from the dataset page either way.
  async function applyMetadata(resourceId: number, payload: DatasetUploadPayload, accessToken: string) {
    try {
      await patchResourceMetadata(resourceId, accessToken, {
        title: payload.title,
        ...(payload.description && { abstract: payload.description }),
        ...(payload.attribution && { attribution: payload.attribution }),
        ...(payload.caution && { data_quality_statement: payload.caution }),
        ...(payload.category && { category: { identifier: payload.category } }),
      })
      if (payload.sourceLink) {
        await createSourceLink(resourceId, accessToken, payload.sourceLink)
      }
    } catch (err) {
      toast.warning('Dataset uploaded, but some metadata could not be saved. Edit it from the dataset page.')
      console.error(err)
    }
  }

  async function submit(payload: DatasetUploadPayload): Promise<number | null> {
    const accessToken = auth.accessToken
    if (!accessToken) return null

    error.value = null
    status.value = null
    submitting.value = true

    try {
      const executionId = await uploadDataset(payload.file, accessToken)
      status.value = 'ready'
      const result = await pollUntilSettled(executionId, accessToken)

      if (result.status === 'failed') {
        throw new UploadError(result.log ?? 'Upload processing failed')
      }

      const resourceId = getFinishedResourceId(result)
      if (resourceId) {
        await applyMetadata(resourceId, payload, accessToken)
      } else {
        toast.warning('Dataset uploaded, but metadata could not be saved. Edit it from the dataset page.')
      }

      toast.success('Dataset uploaded.')
      return resourceId
    } catch (err) {
      error.value = err instanceof UploadError ? err.message : 'Upload failed'
      toast.error(error.value)
      return null
    } finally {
      submitting.value = false
    }
  }

  return {
    status: readonly(status),
    error: readonly(error),
    submitting: readonly(submitting),
    submit,
  }
}
