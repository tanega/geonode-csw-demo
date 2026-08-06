import type { Page } from '@playwright/test'

export interface SeedUser {
  sub: string
  email: string
  preferred_username: string
  groups: string[]
}

export const CONTRIBUTOR_USER: SeedUser = {
  sub: '1',
  email: 'admin@example.com',
  preferred_username: 'admin',
  groups: ['contributors'],
}

// Seeds the auth Pinia store's localStorage-backed state directly, so tests
// can start authenticated without depending on the real backend/CORS setup.
export async function seedAuthenticatedSession(page: Page, user: SeedUser = CONTRIBUTOR_USER) {
  await page.goto('/')
  await page.evaluate((seededUser) => {
    localStorage.setItem('auth:access-token', 'fake-token')
    localStorage.setItem('auth:refresh-token', 'fake-refresh')
    localStorage.setItem('auth:user', JSON.stringify(seededUser))
  }, user)
}
