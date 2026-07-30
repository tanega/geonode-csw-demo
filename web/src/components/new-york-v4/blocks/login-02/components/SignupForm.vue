<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { ref } from "vue"
import { useRouter } from "vue-router"
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { AuthError } from '@/lib/api/auth'
import { Button } from '@/components/ui/button'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'

const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const email = ref('')
const password1 = ref('')
const password2 = ref('')
const error = ref<string | null>(null)
const submitting = ref(false)

async function onSubmit() {
  error.value = null

  if (password1.value !== password2.value) {
    error.value = 'Passwords do not match'
    return
  }

  submitting.value = true
  try {
    await auth.signup({
      username: username.value,
      email: email.value,
      password1: password1.value,
      password2: password2.value,
    })
    await router.push({ name: 'dashboard' })
  } catch (err) {
    error.value = err instanceof AuthError ? err.message : 'Signup failed'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form :class="cn('flex flex-col gap-6', props.class)" @submit.prevent="onSubmit">
    <FieldGroup>
      <div class="flex flex-col items-center gap-1 text-center">
        <h1 class="text-2xl font-bold">
          Create an account
        </h1>
        <p class="text-muted-foreground text-sm text-balance">
          Enter your details below to create your account
        </p>
      </div>
      <Field>
        <FieldLabel for="username">
          Username
        </FieldLabel>
        <Input id="username" v-model="username" type="text" autocomplete="username" required />
      </Field>
      <Field>
        <FieldLabel for="email">
          Email
        </FieldLabel>
        <Input id="email" v-model="email" type="email" autocomplete="email" required />
      </Field>
      <Field>
        <FieldLabel for="password1">
          Password
        </FieldLabel>
        <Input
          id="password1"
          v-model="password1"
          type="password"
          autocomplete="new-password"
          required
        />
      </Field>
      <Field>
        <FieldLabel for="password2">
          Confirm password
        </FieldLabel>
        <Input
          id="password2"
          v-model="password2"
          type="password"
          autocomplete="new-password"
          required
        />
      </Field>
      <FieldError v-if="error" :errors="[error]" />
      <Field>
        <Button type="submit" :disabled="submitting">
          {{ submitting ? 'Creating account…' : 'Sign up' }}
        </Button>
        <FieldDescription class="text-center">
          Already have an account?
          <RouterLink to="/login">Login</RouterLink>
        </FieldDescription>
      </Field>
    </FieldGroup>
  </form>
</template>
