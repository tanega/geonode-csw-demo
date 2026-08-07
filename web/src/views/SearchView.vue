<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useDatasetSearch } from '@/composables/useDatasetSearch'
import { Input } from '@/components/ui/input'
import DatasetCard from '@/components/dataset/DatasetCard.vue'
import FacetFilterGroup from '@/components/dataset/FacetFilterGroup.vue'

const { searchInput, selected, resources, total, facets, loading, error, toggleFacet } = useDatasetSearch()
</script>

<template>
  <main class="mx-auto max-w-6xl px-6 py-12">
    <RouterLink to="/" class="text-muted-foreground text-sm hover:underline">&larr; Back to home</RouterLink>

    <h1 class="mt-4 text-2xl font-bold">Search datasets</h1>

    <Input v-model="searchInput" placeholder="Search by title, abstract, caution…" class="mt-4 max-w-md" />

    <div class="mt-8 grid grid-cols-1 gap-8 md:grid-cols-[16rem_1fr]">
      <aside class="space-y-6">
        <FacetFilterGroup
          title="Type"
          :items="facets?.resourceTypes ?? []"
          :selected="selected.resourceType"
          @toggle="(key) => toggleFacet('resourceType', key)"
        />
        <FacetFilterGroup
          title="Topic"
          :items="facets?.categories ?? []"
          :selected="selected.category"
          @toggle="(key) => toggleFacet('category', key)"
        />
        <FacetFilterGroup
          title="Provider"
          :items="facets?.providers ?? []"
          :selected="selected.provider"
          @toggle="(key) => toggleFacet('provider', key)"
        />
      </aside>

      <div>
        <p v-if="error" class="text-destructive text-sm">{{ error }}</p>
        <p v-else-if="loading" class="text-muted-foreground text-sm">Loading…</p>
        <template v-else>
          <p class="text-muted-foreground text-sm">{{ total }} dataset{{ total === 1 ? '' : 's' }}</p>
          <p v-if="resources.length === 0" class="text-muted-foreground mt-8 text-center text-sm">
            No datasets match these filters.
          </p>
          <div v-else class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <DatasetCard v-for="resource in resources" :key="resource.pk" :resource="resource" />
          </div>
        </template>
      </div>
    </div>
  </main>
</template>
