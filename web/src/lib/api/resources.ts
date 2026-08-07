const API_BASE = import.meta.env.VITE_GEONODE_API_BASE

export class ResourceError extends Error {}

export interface ResourceLink {
  extension: string
  link_type: string
  name: string
  mime: string
  url: string
}

export interface ExtraMetadataEntry {
  id: number
  filter_header: string
  field_name: string
  field_label: string
  field_value: string
}

export interface Resource {
  pk: string
  uuid: string
  resource_type: string
  subtype: string
  title: string
  abstract: string
  thumbnail_url: string
  detail_url: string
  srid: string | null
  date: string
  date_type: string
  attribution: string | null
  data_quality_statement: string | null
  category: { identifier: string; gn_description: string } | null
  owner: { username: string }
  links: ResourceLink[]
  // Deferred field on GeoNode's DynamicModelSerializer -- only present
  // when requested via `include[]=metadata` (see getResource).
  metadata?: ExtraMetadataEntry[]
}

interface ResourceListResponse {
  total: number
  page: number
  page_size: number
  resources: Resource[]
}

// The literal query keys GeoNode's dynamic-rest filter backend expects
// for each facet -- also used to forward the currently-applied filters
// into facet count requests (see lib/api/facets.ts), so counts stay in
// sync with whatever's already selected. `resourceType` targets the
// nested `subtype` (vector/raster), not the parent `resource_type`
// (every resource here is a "dataset"). `provider` matches the custom
// endpoint's own `filter` field (geonode-custom/uploads_api/views.py::
// ProviderFacetView).
export const FACET_FILTER_KEYS = {
  resourceType: 'filter{subtype.in}',
  category: 'filter{category.identifier.in}',
  provider: 'filter{attribution.in}',
} as const

export type FacetKey = keyof typeof FACET_FILTER_KEYS

export function appendFilterParams(params: URLSearchParams, filters: Partial<Record<FacetKey, string[]>>) {
  for (const key of Object.keys(filters) as FacetKey[]) {
    for (const value of filters[key] ?? []) {
      params.append(FACET_FILTER_KEYS[key], value)
    }
  }
}

export interface ListResourcesParams {
  page?: number
  pageSize?: number
  search?: string
  // Comma-separated `search_fields` 500s (GeoNode expects the param
  // repeated once per field) -- verified against the live API.
  searchFields?: string[]
  filters?: Partial<Record<FacetKey, string[]>>
}

// GeoNode's own /api/v2/resources/ REST endpoint -- public/anonymous reads
// return only publicly-permissioned resources, no auth needed. Used here
// instead of CSW (this project's primary discovery protocol, see
// docs/architecture.md) because it returns ready-to-use JSON (thumbnails,
// grouped OGC/download links) instead of requiring XML parsing -- a
// deliberate shortcut for this first "quickly built" pass.
export async function listResources(params: ListResourcesParams = {}): Promise<ResourceListResponse> {
  const { page = 1, pageSize = 20, search, searchFields, filters } = params

  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (search) {
    query.set('search', search)
    for (const field of searchFields ?? []) query.append('search_fields', field)
  }
  if (filters) appendFilterParams(query, filters)

  const response = await fetch(`${API_BASE}/api/v2/resources/?${query}`)
  if (!response.ok) throw new ResourceError('Failed to fetch datasets')
  return response.json()
}

export async function getResource(pk: string): Promise<Resource> {
  // `metadata` (the ExtraMetadata list -- e.g. "data last updated") is a
  // deferred field on GeoNode's DynamicModelSerializer: omitted unless
  // explicitly requested.
  const response = await fetch(`${API_BASE}/api/v2/resources/${pk}/?include[]=metadata`)
  if (!response.ok) throw new ResourceError('Failed to fetch dataset')
  const data: { resource: Resource } = await response.json()
  return data.resource
}
