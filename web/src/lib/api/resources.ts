const API_BASE = import.meta.env.VITE_GEONODE_API_BASE

export class ResourceError extends Error {}

export interface ResourceLink {
  extension: string
  link_type: string
  name: string
  mime: string
  url: string
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
  owner: { username: string }
  links: ResourceLink[]
}

interface ResourceListResponse {
  total: number
  page: number
  page_size: number
  resources: Resource[]
}

// GeoNode's own /api/v2/resources/ REST endpoint -- public/anonymous reads
// return only publicly-permissioned resources, no auth needed. Used here
// instead of CSW (this project's primary discovery protocol, see
// docs/architecture.md) because it returns ready-to-use JSON (thumbnails,
// grouped OGC/download links) instead of requiring XML parsing -- a
// deliberate shortcut for this first "quickly built" pass.
export async function listResources(page = 1, pageSize = 20): Promise<ResourceListResponse> {
  const response = await fetch(
    `${API_BASE}/api/v2/resources/?page=${page}&page_size=${pageSize}`,
  )
  if (!response.ok) throw new ResourceError('Failed to fetch datasets')
  return response.json()
}

export async function getResource(pk: string): Promise<Resource> {
  const response = await fetch(`${API_BASE}/api/v2/resources/${pk}/`)
  if (!response.ok) throw new ResourceError('Failed to fetch dataset')
  const data: { resource: Resource } = await response.json()
  return data.resource
}
