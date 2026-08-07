import { computed, ref, watch } from 'vue'
import { useRoute, useRouter, type LocationQueryValue } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { listResources, ResourceError } from '@/lib/api/resources'
import type { Resource, FacetKey } from '@/lib/api/resources'
import { getFacets } from '@/lib/api/facets'
import type { DatasetFacets } from '@/lib/api/facets'

// data_quality_statement is included despite living on the Dataset table
// (modeltranslation shadow, see uploads.ts) -- that only breaks writes
// through the generic resources endpoint, reads/search are unaffected
// (verified against the live API).
const SEARCH_FIELDS = ['title', 'abstract', 'data_quality_statement']
const PAGE_SIZE = 24
const SEARCH_DEBOUNCE_MS = 300

function toArray(value: LocationQueryValue | LocationQueryValue[] | undefined): string[] {
  const values = Array.isArray(value) ? value : [value]
  return values.filter((v): v is string => typeof v === 'string' && v.length > 0)
}

// The URL's query string is the single source of truth for search/filter
// state (not a separate reactive copy kept in sync by hand): every read
// comes from `route.query`, every write goes through `updateQuery`. That
// makes back/forward navigation and shared links work for free, since
// they're just a route.query change like any other.
export function useDatasetSearch() {
  const route = useRoute()
  const router = useRouter()

  const searchInput = ref(toArray(route.query.q)[0] ?? '')
  const resources = ref<Resource[]>([])
  const total = ref(0)
  const facets = ref<DatasetFacets | null>(null)
  const loading = ref(true)
  const error = ref<string | null>(null)

  const selected = computed<Record<FacetKey, string[]>>(() => ({
    resourceType: toArray(route.query.resourceType),
    category: toArray(route.query.category),
    provider: toArray(route.query.provider),
  }))

  function updateQuery(patch: Record<string, string | string[] | undefined>) {
    router.replace({ query: { ...route.query, ...patch } })
  }

  const commitSearch = useDebounceFn((value: string) => {
    updateQuery({ q: value || undefined })
  }, SEARCH_DEBOUNCE_MS)

  watch(searchInput, commitSearch)

  function toggleFacet(facet: FacetKey, key: string) {
    const current = selected.value[facet]
    const next = current.includes(key) ? current.filter((k) => k !== key) : [...current, key]
    updateQuery({ [facet]: next.length ? next : undefined })
  }

  async function fetchResults() {
    loading.value = true
    error.value = null
    const search = toArray(route.query.q)[0] ?? ''
    const filters = selected.value

    try {
      const [resourceData, facetData] = await Promise.all([
        listResources({
          pageSize: PAGE_SIZE,
          search: search || undefined,
          searchFields: search ? SEARCH_FIELDS : undefined,
          filters,
        }),
        getFacets(filters),
      ])
      resources.value = resourceData.resources
      total.value = resourceData.total
      facets.value = facetData
    } catch (err) {
      error.value = err instanceof ResourceError ? err.message : 'Failed to load datasets'
    } finally {
      loading.value = false
    }
  }

  watch(() => route.query, fetchResults, { immediate: true })

  return {
    searchInput,
    selected,
    resources,
    total,
    facets,
    loading,
    error,
    toggleFacet,
  }
}
