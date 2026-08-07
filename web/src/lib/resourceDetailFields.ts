import type { Resource } from '@/lib/api/resources'

export interface DetailField {
  label: string
  value: string
}

// Derives the contributor-supplied metadata fields (see
// DatasetUploadForm.vue) plus the auto-stamped "data last updated" entry
// (geonode-custom/uploads_api/signals.py) into a flat label/value list for
// display. All of these are optional -- fields left blank at upload time
// are omitted rather than shown empty.
export function formatDetailFields(resource: Resource): DetailField[] {
  const fields: DetailField[] = []

  if (resource.category?.gn_description) {
    fields.push({ label: 'Topic', value: resource.category.gn_description })
  }
  if (resource.attribution) {
    fields.push({ label: 'Provider', value: resource.attribution })
  }

  const dataLastUpdated = resource.metadata?.find((m) => m.field_name === 'data_last_updated')
  if (dataLastUpdated) {
    fields.push({
      label: dataLastUpdated.field_label || 'Data last updated',
      value: new Date(dataLastUpdated.field_value).toLocaleDateString(),
    })
  }

  if (resource.data_quality_statement) {
    fields.push({ label: 'Caution', value: resource.data_quality_statement })
  }

  return fields
}
