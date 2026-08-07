<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useDatasetUpload } from '@/composables/useDatasetUpload'
import type { DatasetUploadPayload } from '@/composables/useDatasetUpload'
import DatasetUploadForm from '@/components/upload/DatasetUploadForm.vue'
import { FieldError } from '@/components/ui/field'

const router = useRouter()
const { status, error, submitting, submit } = useDatasetUpload()

async function onSubmit(payload: DatasetUploadPayload) {
  const resourceId = await submit(payload)
  if (resourceId) {
    router.push(`/datasets/${resourceId}`)
  }
}

// status flips to "finished" as soon as the file import completes, but
// metadata/source-link are still being saved at that point (they run
// after, see useDatasetUpload's submit()) -- keep showing progress until
// submitting itself clears, so the page never claims "Done" while a save
// is still in flight.
const statusLabel = computed(() => {
  if (submitting.value) {
    const labels: Record<string, string> = { ready: 'Queued…', running: 'Processing…', finished: 'Saving metadata…', failed: '' }
    return labels[status.value ?? ''] ?? ''
  }
  return status.value === 'finished' ? 'Done — dataset uploaded.' : ''
})
</script>

<template>
  <main class="mx-auto flex min-h-svh max-w-sm flex-col justify-center gap-6 px-6 py-12">
    <div class="flex flex-col items-center gap-1 text-center">
      <h1 class="text-2xl font-bold">Upload dataset</h1>
      <p class="text-muted-foreground text-sm text-balance">
        Add the file and its metadata — both help others discover it later.
      </p>
    </div>

    <DatasetUploadForm :submitting="submitting" @submit="onSubmit" />

    <FieldError v-if="error" :errors="[error]" />
    <p v-if="statusLabel && !error" class="text-muted-foreground text-center text-sm">
      {{ statusLabel }}
    </p>

    <RouterLink to="/dashboard" class="text-muted-foreground text-center text-sm hover:underline">
      Back to dashboard
    </RouterLink>
  </main>
</template>
