import { readonly, ref } from 'vue'
import { toast } from 'vue-sonner'
import { useAuthStore } from '@/stores/auth'
import { patchResourceMetadata, createSourceLink, UploadError } from '@/lib/api/uploads'

export interface DatasetEditPayload {
  title: string
  description: string
  category: string
  attribution: string
  caution: string
  sourceLink: string
}

export function useDatasetEdit(resourceId: number) {
  const auth = useAuthStore()

  const error = ref<string | null>(null)
  const submitting = ref(false)

  async function submit(payload: DatasetEditPayload): Promise<boolean> {
    const accessToken = auth.accessToken
    if (!accessToken) return false

    error.value = null
    submitting.value = true

    try {
      // GeoNode's serializer rejects an explicit blank string on
      // abstract/attribution/data_quality_statement ("This field may not
      // be blank.") even though the model itself allows blank -- verified
      // against the running API. So, same as upload, a field only goes in
      // the payload when non-empty; there's no way to clear one of these
      // back to blank once set (a backend limitation, not a UI choice).
      await patchResourceMetadata(resourceId, accessToken, {
        title: payload.title,
        ...(payload.description && { abstract: payload.description }),
        ...(payload.attribution && { attribution: payload.attribution }),
        ...(payload.caution && { data_quality_statement: payload.caution }),
        ...(payload.category && { category: { identifier: payload.category } }),
      })
      if (payload.sourceLink) {
        // SourceLinkView upserts (update_or_create on resource+link_type+name),
        // so re-submitting the same endpoint updates the existing link too.
        await createSourceLink(resourceId, accessToken, payload.sourceLink)
      }
      toast.success('Dataset updated.')
      return true
    } catch (err) {
      error.value = err instanceof UploadError ? err.message : 'Failed to save changes'
      toast.error(error.value)
      return false
    } finally {
      submitting.value = false
    }
  }

  return {
    error: readonly(error),
    submitting: readonly(submitting),
    submit,
  }
}
