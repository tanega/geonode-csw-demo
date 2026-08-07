<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Resource } from '@/lib/api/resources'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

defineProps<{ resource: Resource }>()
</script>

<template>
  <RouterLink :to="{ name: 'dataset-detail', params: { pk: resource.pk } }">
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
</template>
