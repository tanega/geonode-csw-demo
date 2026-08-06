<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import { listResources, ResourceError } from '@/lib/api/resources'
import type { Resource } from '@/lib/api/resources'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

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

    <div class="mt-10">
      <Input v-model="search" placeholder="Search datasets by title…" class="max-w-sm" />
    </div>

    <p v-if="loading" class="text-muted-foreground mt-8 text-center text-sm">Loading datasets…</p>
    <p v-else-if="filteredResources.length === 0" class="text-muted-foreground mt-8 text-center text-sm">
      No datasets found.
    </p>

    <div v-else class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink
        v-for="resource in filteredResources"
        :key="resource.pk"
        :to="{ name: 'dataset-detail', params: { pk: resource.pk } }"
      >
        <Card class="h-full overflow-hidden py-0 transition-shadow hover:shadow-md">
          <img
            v-if="resource.thumbnail_url"
            :src="resource.thumbnail_url"
            :alt="resource.title"
            class="aspect-video w-full object-cover"
          />
          <CardHeader class="py-4">
            <CardTitle class="text-base">{{ resource.title }}</CardTitle>
            <Badge variant="secondary" class="mt-1 w-fit">{{ resource.subtype }}</Badge>
          </CardHeader>
          <CardContent v-if="resource.abstract" class="text-muted-foreground pb-4 text-sm">
            {{ resource.abstract }}
          </CardContent>
        </Card>
      </RouterLink>
    </div>
  </main>
</template>
