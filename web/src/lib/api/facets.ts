import { appendFilterParams, type FacetKey } from '@/lib/api/resources'

const API_BASE = import.meta.env.VITE_GEONODE_API_BASE

export interface FacetItem {
  key: string
  label: string
  count: number
}

export interface DatasetFacets {
  resourceTypes: FacetItem[]
  categories: FacetItem[]
  providers: FacetItem[]
}

interface RawFacetTopicItem {
  key: string
  label: string
  count: number
  items?: RawFacetTopicItem[]
}

interface RawFacet {
  name: string
  topics?: { items: RawFacetTopicItem[] }
}

interface RawFacetsResponse {
  facets: RawFacet[]
}

function toFacetItems(items: RawFacetTopicItem[] = []): FacetItem[] {
  return items.map(({ key, label, count }) => ({ key, label, count }))
}

// Fetches the three facets this app exposes -- resource type
// (vector/raster), category/topic, and provider -- prefiltered by
// whatever's already selected so counts stay accurate as the user narrows
// down (GeoNode's /api/v2/facets supports this natively via the same
// filter{...} params used to filter the resource list itself; the
// provider facet is a custom endpoint that mirrors that behavior, see
// geonode-custom/uploads_api/views.py::ProviderFacetView).
export async function getFacets(filters: Partial<Record<FacetKey, string[]>> = {}): Promise<DatasetFacets> {
  const params = new URLSearchParams({ include_topics: 'true' })
  appendFilterParams(params, filters)

  const [builtinResponse, providerResponse] = await Promise.all([
    fetch(`${API_BASE}/api/v2/facets?${params}`),
    fetch(`${API_BASE}/api/v2/custom/facets/provider/?${params}`),
  ])
  if (!builtinResponse.ok || !providerResponse.ok) {
    throw new Error('Failed to fetch facets')
  }

  const builtin: RawFacetsResponse = await builtinResponse.json()
  const provider: RawFacet = await providerResponse.json()

  const resourceTypeFacet = builtin.facets.find((f) => f.name === 'resourcetype')
  const categoryFacet = builtin.facets.find((f) => f.name === 'category')

  // resourcetype is hierarchical (dataset -> vector/raster); this app only
  // has "dataset" resources, so flatten straight to the subtype children.
  const resourceTypes = toFacetItems(
    resourceTypeFacet?.topics?.items.flatMap((item) => item.items ?? []) ?? [],
  )
  const categories = toFacetItems(categoryFacet?.topics?.items)
  const providers = toFacetItems(provider.topics?.items)

  return { resourceTypes, categories, providers }
}
