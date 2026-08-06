const API_BASE = import.meta.env.VITE_GEONODE_API_BASE

export interface TopicCategory {
  identifier: string
  gn_description: string
  is_choice: boolean
}

interface CategoriesResponse {
  categories: TopicCategory[]
}

// AllowAny endpoint, no auth needed. is_choice filters out entries GeoNode
// keeps around for other purposes but doesn't offer as a selectable topic
// (see ResourceBase.category's limit_choices_to=Q(is_choice=True)).
export async function listTopicCategories(): Promise<TopicCategory[]> {
  const response = await fetch(`${API_BASE}/api/v2/categories/?page_size=100`)
  if (!response.ok) throw new Error('Failed to fetch topic categories')

  const data: CategoriesResponse = await response.json()
  return data.categories.filter((category) => category.is_choice)
}
