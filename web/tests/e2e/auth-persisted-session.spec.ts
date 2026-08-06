import { test, expect } from '@playwright/test'
import { seedAuthenticatedSession } from './support/auth'

// Regression test: useStorage's `user` ref used to serialize via the wrong
// (`any`) fallback, corrupting localStorage into "[object Object]". Reading
// that back on a hard navigation crashed isContributor's .groups.includes()
// and left DashboardView rendering only its header.
test('direct hard navigation to /dashboard renders fully for a persisted session', async ({
  page,
}) => {
  const pageErrors: Error[] = []
  page.on('pageerror', (error) => pageErrors.push(error))

  await seedAuthenticatedSession(page)

  await page.goto('/dashboard')

  await expect(page.getByText('Signed in as admin')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Upload dataset' })).toBeVisible()
  expect(pageErrors).toEqual([])
})
