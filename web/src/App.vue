<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <header class="border-border flex items-center justify-between border-b px-6 py-4">
    <RouterLink to="/" class="font-semibold">GeoNode Demo</RouterLink>
    <nav class="flex items-center gap-4 text-sm">
      <template v-if="auth.isAuthenticated">
        <RouterLink to="/dashboard">Dashboard</RouterLink>
      </template>
      <template v-else>
        <RouterLink to="/login">Login</RouterLink>
        <RouterLink to="/signup">Sign up</RouterLink>
      </template>
    </nav>
  </header>
  <RouterView />
</template>
