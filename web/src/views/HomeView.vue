<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import { listResources, ResourceError } from '@/lib/api/resources'
import type { Resource } from '@/lib/api/resources'
import { Input } from '@/components/ui/input'
import DatasetCard from '@/components/dataset/DatasetCard.vue'

const resources = ref<Resource[]>([])
const loading = ref(true)
const search = ref('')

const filteredResources = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) return resources.value
  return resources.value.filter((r) => r.title.toLowerCase().includes(query))
})

onMounted(async () => {
  try {
    const data = await listResources()
    resources.value = data.resources
  } catch (err) {
    toast.error(err instanceof ResourceError ? err.message : 'Failed to load datasets')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-12">
    <div class="flex flex-col items-center gap-1 text-center">
      <h1 class="text-3xl font-bold tracking-tight">GeoNode Demo</h1>
      <p class="text-muted-foreground mt-2 text-sm text-balance">
        Spatial data discovery, powered by GeoNode.
      </p>
    </div>

    <div class="mt-10 flex flex-wrap items-center justify-center gap-3">
      <Input v-model="search" placeholder="Search datasets by title…" class="max-w-sm" />
      <RouterLink to="/search" class="text-muted-foreground text-sm hover:underline">
        Advanced search &rarr;
      </RouterLink>
    </div>

    <p v-if="loading" class="text-muted-foreground mt-8 text-center text-sm">Loading datasets…</p>
    <p v-else-if="filteredResources.length === 0" class="text-muted-foreground mt-8 text-center text-sm">
      No datasets found.
    </p>

    <div v-else class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <DatasetCard v-for="resource in filteredResources" :key="resource.pk" :resource="resource" />
    </div>
  </main>
</template>
