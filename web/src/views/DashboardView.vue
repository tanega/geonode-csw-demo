<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'

const router = useRouter()
const auth = useAuthStore()

function onLogout() {
  auth.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <main class="mx-auto flex min-h-svh max-w-2xl flex-col items-center justify-center gap-4 px-6 text-center">
    <h1 class="text-2xl font-bold">Dashboard</h1>
    <p class="text-muted-foreground text-sm">
      Signed in as <span class="font-medium text-foreground">{{ auth.user?.preferred_username }}</span>
    </p>
    <span class="bg-secondary text-secondary-foreground rounded-full px-3 py-1 text-xs font-medium">
      {{ auth.isContributor ? 'Contributor' : 'Reader' }}
    </span>
    <Button variant="outline" @click="onLogout">Log out</Button>
  </main>
</template>
