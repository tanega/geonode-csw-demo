<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import { getResource, ResourceError } from '@/lib/api/resources'
import type { Resource, ResourceLink } from '@/lib/api/resources'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const route = useRoute()

const resource = ref<Resource | null>(null)
const loading = ref(true)
const notFound = ref(false)

// Group the resource's raw link list into sections useful for exploring
// what a GeoNode dataset actually exposes -- OGC services, downloadable
// data, cloud-native mirrors, and metadata records -- matching this
// project's CSW/OGC discovery focus (see docs/architecture.md).
function isCloudNative(link: ResourceLink) {
  return link.name.toLowerCase().includes('cloud-native') || link.url.includes('minio')
}

const linkGroups = computed(() => {
  const links = resource.value?.links ?? []
  const groups: [string, ResourceLink[]][] = [
    ['OGC services', links.filter((l) => l.link_type.startsWith('OGC:'))],
    ['Cloud-native', links.filter((l) => !l.link_type.startsWith('OGC:') && isCloudNative(l))],
    ['Data downloads', links.filter((l) => l.link_type === 'data' && !isCloudNative(l))],
    ['Metadata', links.filter((l) => l.link_type === 'metadata')],
  ]
  return groups.filter(([, items]) => items.length > 0)
})

onMounted(async () => {
  const pk = route.params.pk as string
  try {
    resource.value = await getResource(pk)
  } catch (err) {
    notFound.value = true
    toast.error(err instanceof ResourceError ? err.message : 'Failed to load dataset')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="mx-auto max-w-3xl px-6 py-12">
    <RouterLink to="/" class="text-muted-foreground text-sm hover:underline">&larr; Back to datasets</RouterLink>

    <p v-if="loading" class="text-muted-foreground mt-8 text-center text-sm">Loading…</p>
    <p v-else-if="notFound || !resource" class="text-muted-foreground mt-8 text-center text-sm">
      Dataset not found.
    </p>

    <div v-else class="mt-6">
      <div class="flex flex-wrap items-center gap-3">
        <h1 class="text-2xl font-bold">{{ resource.title }}</h1>
        <Badge variant="secondary">{{ resource.subtype }}</Badge>
      </div>
      <p class="text-muted-foreground mt-1 text-sm">
        Published {{ new Date(resource.date).toLocaleDateString() }} by {{ resource.owner.username }}
      </p>

      <img
        v-if="resource.thumbnail_url"
        :src="resource.thumbnail_url"
        :alt="resource.title"
        class="mt-6 w-full max-w-md rounded-md border"
      />

      <p v-if="resource.abstract" class="mt-6 text-sm">{{ resource.abstract }}</p>

      <div v-for="[groupName, links] in linkGroups" :key="groupName" class="mt-8">
        <h2 class="text-sm font-semibold">{{ groupName }}</h2>
        <div class="mt-2 flex flex-wrap gap-2">
          <Button v-for="link in links" :key="link.url" as="a" :href="link.url" target="_blank" variant="outline" size="sm">
            {{ link.name }}
          </Button>
        </div>
      </div>
    </div>
  </main>
</template>
