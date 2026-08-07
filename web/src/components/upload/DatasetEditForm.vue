<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useForm } from '@tanstack/vue-form'
import { z } from 'zod'
import { listTopicCategories } from '@/lib/api/categories'
import type { TopicCategory } from '@/lib/api/categories'
import type { DatasetEditPayload } from '@/composables/useDatasetEdit'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface Props {
  submitting: boolean
  initialValues: DatasetEditPayload
}

interface Emits {
  submit: [payload: DatasetEditPayload]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const categories = ref<TopicCategory[]>([])

onMounted(async () => {
  try {
    categories.value = await listTopicCategories()
  } catch (err) {
    console.error('Failed to load topic categories', err)
  }
})

const metadataSchema = z.object({
  title: z.string().min(1, 'Title is required.').max(255, 'Title must be at most 255 characters.'),
  description: z.string().max(2000, 'Description must be at most 2000 characters.'),
  category: z.string(),
  attribution: z.string().max(2048, 'Provider must be at most 2048 characters.'),
  caution: z.string().max(2000, 'Caution text must be at most 2000 characters.'),
  sourceLink: z.union([z.literal(''), z.string().url('Must be a valid URL.')]),
})

const form = useForm({
  defaultValues: props.initialValues,
  validators: {
    onSubmit: metadataSchema,
  },
  onSubmit: async ({ value }) => {
    emit('submit', value)
  },
})

function isInvalid(field: { state: { meta: { isTouched: boolean; isValid: boolean } } }) {
  return field.state.meta.isTouched && !field.state.meta.isValid
}
</script>

<template>
  <form id="dataset-edit-form" class="flex flex-col gap-6" @submit.prevent="form.handleSubmit">
    <FieldGroup>
      <form.Field name="title">
        <template #default="{ field }">
          <Field :data-invalid="isInvalid(field)">
            <FieldLabel :for="field.name">Title</FieldLabel>
            <Input
              :id="field.name"
              :name="field.name"
              :model-value="field.state.value"
              :aria-invalid="isInvalid(field)"
              @blur="field.handleBlur"
              @input="field.handleChange(($event.target as HTMLInputElement).value)"
            />
            <FieldError v-if="isInvalid(field)" :errors="field.state.meta.errors" />
          </Field>
        </template>
      </form.Field>

      <form.Field name="description">
        <template #default="{ field }">
          <Field :data-invalid="isInvalid(field)">
            <FieldLabel :for="field.name">Description</FieldLabel>
            <Textarea
              :id="field.name"
              :name="field.name"
              :model-value="field.state.value"
              :aria-invalid="isInvalid(field)"
              :rows="3"
              @blur="field.handleBlur"
              @update:model-value="(v) => field.handleChange(String(v))"
            />
            <FieldError v-if="isInvalid(field)" :errors="field.state.meta.errors" />
          </Field>
        </template>
      </form.Field>

      <form.Field name="category">
        <template #default="{ field }">
          <Field :data-invalid="isInvalid(field)">
            <FieldLabel :for="field.name">Topic</FieldLabel>
            <Select
              :model-value="field.state.value"
              @update:model-value="(v) => field.handleChange(v ? String(v) : '')"
            >
              <SelectTrigger :id="field.name" class="w-full" :aria-invalid="isInvalid(field)">
                <SelectValue placeholder="Select a topic (ISO 19115 category)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="category in categories" :key="category.identifier" :value="category.identifier">
                  {{ category.gn_description }}
                </SelectItem>
              </SelectContent>
            </Select>
            <FieldError v-if="isInvalid(field)" :errors="field.state.meta.errors" />
          </Field>
        </template>
      </form.Field>

      <form.Field name="attribution">
        <template #default="{ field }">
          <Field :data-invalid="isInvalid(field)">
            <FieldLabel :for="field.name">Provider / source</FieldLabel>
            <Input
              :id="field.name"
              :name="field.name"
              :model-value="field.state.value"
              :aria-invalid="isInvalid(field)"
              placeholder="Instituto Geográfico Nacional"
              @blur="field.handleBlur"
              @input="field.handleChange(($event.target as HTMLInputElement).value)"
            />
            <FieldError v-if="isInvalid(field)" :errors="field.state.meta.errors" />
          </Field>
        </template>
      </form.Field>

      <form.Field name="caution">
        <template #default="{ field }">
          <Field :data-invalid="isInvalid(field)">
            <FieldLabel :for="field.name">Caution / known limitations</FieldLabel>
            <Textarea
              :id="field.name"
              :name="field.name"
              :model-value="field.state.value"
              :aria-invalid="isInvalid(field)"
              placeholder="E.g. vertical accuracy not validated for this area."
              :rows="3"
              @blur="field.handleBlur"
              @update:model-value="(v) => field.handleChange(String(v))"
            />
            <FieldError v-if="isInvalid(field)" :errors="field.state.meta.errors" />
          </Field>
        </template>
      </form.Field>

      <form.Field name="sourceLink">
        <template #default="{ field }">
          <Field :data-invalid="isInvalid(field)">
            <FieldLabel :for="field.name">Source link (optional)</FieldLabel>
            <Input
              :id="field.name"
              :name="field.name"
              type="url"
              :model-value="field.state.value"
              :aria-invalid="isInvalid(field)"
              placeholder="https://example.org/original-dataset"
              @blur="field.handleBlur"
              @input="field.handleChange(($event.target as HTMLInputElement).value)"
            />
            <FieldDescription>Overwrites the previously saved source link, if any.</FieldDescription>
            <FieldError v-if="isInvalid(field)" :errors="field.state.meta.errors" />
          </Field>
        </template>
      </form.Field>

      <Field>
        <Button type="submit" form="dataset-edit-form" :disabled="submitting">
          {{ submitting ? 'Saving…' : 'Save changes' }}
        </Button>
      </Field>
    </FieldGroup>
  </form>
</template>
