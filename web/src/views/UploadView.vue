<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import { useAuthStore } from '@/stores/auth'
import { uploadDataset, getExecutionStatus, UploadError } from '@/lib/api/uploads'
import type { ExecutionStatus } from '@/lib/api/uploads'
import { Button } from '@/components/ui/button'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'

const auth = useAuthStore()

const file = ref<File | null>(null)
const status = ref<ExecutionStatus | null>(null)
const error = ref<string | null>(null)
const submitting = ref(false)

const POLL_INTERVAL_MS = 2000

function onFileChange(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function pollStatus(executionId: string) {
  const token = auth.accessToken
  if (!token) return

  const result = await getExecutionStatus(executionId, token)
  status.value = result.status

  if (result.status === 'failed') {
    error.value = result.log ?? 'Upload processing failed'
    toast.error(error.value)
    submitting.value = false
    return
  }

  if (result.status === 'finished') {
    submitting.value = false
    toast.success('Dataset uploaded.')
    return
  }

  setTimeout(() => pollStatus(executionId), POLL_INTERVAL_MS)
}

async function onSubmit() {
  if (!file.value || !auth.accessToken) return

  error.value = null
  status.value = null
  submitting.value = true

  try {
    const executionId = await uploadDataset(file.value, auth.accessToken)
    status.value = 'ready'
    await pollStatus(executionId)
  } catch (err) {
    error.value = err instanceof UploadError ? err.message : 'Upload failed'
    toast.error(error.value)
    submitting.value = false
  }
}
</script>

<template>
  <main class="mx-auto flex min-h-svh max-w-sm flex-col justify-center gap-6 px-6">
    <div class="flex flex-col items-center gap-1 text-center">
      <h1 class="text-2xl font-bold">Upload dataset</h1>
      <p class="text-muted-foreground text-sm text-balance">
        Vector (GeoPackage, Shapefile) or raster (GeoTIFF) files
      </p>
    </div>
    <form class="flex flex-col gap-6" @submit.prevent="onSubmit">
      <FieldGroup>
        <Field>
          <FieldLabel for="file">File</FieldLabel>
          <input
            id="file"
            type="file"
            required
            class="border-input file:text-foreground rounded-md border px-3 py-2 text-sm file:mr-3 file:rounded-sm file:border-0 file:bg-transparent file:text-sm file:font-medium"
            @change="onFileChange"
          />
        </Field>
        <FieldError v-if="error" :errors="[error]" />
        <p v-if="status && !error" class="text-muted-foreground text-center text-sm">
          {{ { ready: 'Queued…', running: 'Processing…', finished: 'Done — dataset uploaded.', failed: '' }[status] }}
        </p>
        <Field>
          <Button type="submit" :disabled="submitting || !file">
            {{ submitting ? 'Uploading…' : 'Upload' }}
          </Button>
        </Field>
      </FieldGroup>
    </form>
    <RouterLink to="/dashboard" class="text-muted-foreground text-center text-sm hover:underline">
      Back to dashboard
    </RouterLink>
  </main>
</template>
