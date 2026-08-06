import { computed } from 'vue'
import { defineStore } from 'pinia'
import { StorageSerializers, useStorage } from '@vueuse/core'
import { login as apiLogin, signup as apiSignup, fetchUserInfo } from '@/lib/api/auth'
import type { SignupPayload, UserInfo } from '@/lib/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = useStorage<string | null>('auth:access-token', null)
  const refreshToken = useStorage<string | null>('auth:refresh-token', null)
  // Explicit `object` serializer: with a `null` default, useStorage can't
  // infer the type and falls back to the `any` serializer, which writes
  // objects as "[object Object]" instead of JSON — corrupting `user` on
  // the next page load and crashing `isContributor` below.
  const user = useStorage<UserInfo | null>('auth:user', null, undefined, {
    serializer: StorageSerializers.object,
  })

  const isAuthenticated = computed(() => !!accessToken.value)
  const isContributor = computed(() => user.value?.groups.includes('contributors') ?? false)

  async function login(username: string, password: string) {
    const tokens = await apiLogin(username, password)
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token
    user.value = await fetchUserInfo(tokens.access_token)
  }

  async function signup(payload: SignupPayload) {
    await apiSignup(payload)
    await login(payload.username, payload.password1)
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    isContributor,
    login,
    signup,
    logout,
  }
})
