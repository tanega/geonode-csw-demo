<script setup lang="ts">
import type { FacetItem } from '@/lib/api/facets'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

defineProps<{
  title: string
  items: FacetItem[]
  selected: string[]
}>()

const emit = defineEmits<{ toggle: [key: string] }>()
</script>

<template>
  <div v-if="items.length" class="space-y-2">
    <h3 class="text-sm font-semibold">{{ title }}</h3>
    <div v-for="item in items" :key="item.key" class="flex items-center gap-2">
      <Checkbox
        :id="`${title}-${item.key}`"
        :model-value="selected.includes(item.key)"
        @update:model-value="emit('toggle', item.key)"
      />
      <Label :for="`${title}-${item.key}`" class="flex-1 text-sm font-normal">
        {{ item.label }}
        <span class="text-muted-foreground">({{ item.count }})</span>
      </Label>
    </div>
  </div>
</template>
