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
const password = ref('')
const error = ref<string | null>(null)
const submitting = ref(false)

async function onSubmit() {
  error.value = null
  submitting.value = true
  try {
    await auth.login(username.value, password.value)
    const redirect = router.currentRoute.value.query.redirect
    await router.push(typeof redirect === 'string' ? redirect : { name: 'dashboard' })
  } catch (err) {
    error.value = err instanceof AuthError ? err.message : 'Login failed'
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
          Login to your account
        </h1>
        <p class="text-muted-foreground text-sm text-balance">
          Enter your username below to login to your account
        </p>
      </div>
      <Field>
        <FieldLabel for="username">
          Username
        </FieldLabel>
        <Input id="username" v-model="username" type="text" autocomplete="username" required />
      </Field>
      <Field>
        <FieldLabel for="password">
          Password
        </FieldLabel>
        <Input
          id="password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
        />
      </Field>
      <FieldError v-if="error" :errors="[error]" />
      <Field>
        <Button type="submit" :disabled="submitting">
          {{ submitting ? 'Logging in…' : 'Login' }}
        </Button>
        <FieldDescription class="text-center">
          Don't have an account?
          <RouterLink to="/signup">Sign up</RouterLink>
        </FieldDescription>
      </Field>
    </FieldGroup>
  </form>
</template>
