<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { getResource, ResourceError } from '@/lib/api/resources'
import { useDatasetEdit } from '@/composables/useDatasetEdit'
import type { DatasetEditPayload } from '@/composables/useDatasetEdit'
import DatasetEditForm from '@/components/upload/DatasetEditForm.vue'
import { FieldError } from '@/components/ui/field'

const route = useRoute()
const router = useRouter()
const pk = route.params.pk as string

const loading = ref(true)
const notFound = ref(false)
const initialValues = ref<DatasetEditPayload | null>(null)

const { error, submitting, submit } = useDatasetEdit(Number(pk))

onMounted(async () => {
  try {
    const resource = await getResource(pk)
    const sourceLink = resource.links.find((l) => l.link_type === 'metadata' && l.name === 'Source')
    initialValues.value = {
      title: resource.title,
      description: resource.abstract ?? '',
      category: resource.category?.identifier ?? '',
      attribution: resource.attribution ?? '',
      caution: resource.data_quality_statement ?? '',
      sourceLink: sourceLink?.url ?? '',
    }
  } catch (err) {
    notFound.value = true
    toast.error(err instanceof ResourceError ? err.message : 'Failed to load dataset')
  } finally {
    loading.value = false
  }
})

async function onSubmit(payload: DatasetEditPayload) {
  const ok = await submit(payload)
  if (ok) router.push(`/datasets/${pk}`)
}
</script>

<template>
  <main class="mx-auto flex min-h-svh max-w-sm flex-col justify-center gap-6 px-6 py-12">
    <div class="flex flex-col items-center gap-1 text-center">
      <h1 class="text-2xl font-bold">Edit dataset</h1>
      <p class="text-muted-foreground text-sm text-balance">Update this dataset's metadata.</p>
    </div>

    <p v-if="loading" class="text-muted-foreground text-center text-sm">Loading…</p>
    <p v-else-if="notFound || !initialValues" class="text-muted-foreground text-center text-sm">Dataset not found.</p>

    <DatasetEditForm v-else :submitting="submitting" :initial-values="initialValues" @submit="onSubmit" />

    <FieldError v-if="error" :errors="[error]" />

    <RouterLink :to="`/datasets/${pk}`" class="text-muted-foreground text-center text-sm hover:underline">
      Back to dataset
    </RouterLink>
  </main>
</template>
