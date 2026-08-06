import { test, expect } from '@playwright/test'
import { seedAuthenticatedSession } from './support/auth'

const API_ERROR_MESSAGE = 'Total upload size exceeds 100,0 Mio. Please try again with smaller files.'

// Regression test: uploads.ts used to read a nonexistent `detail` field and
// always show a generic "Upload failed", swallowing GeoNode's actual
// {success, errors, code} error payload.
test('upload failure surfaces the API error message in a toast', async ({ page }) => {
  await page.route('**/api/v2/uploads/upload', (route) =>
    route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        errors: [API_ERROR_MESSAGE],
        code: 'total_upload_size_exceeded',
      }),
    }),
  )

  await seedAuthenticatedSession(page)
  await page.goto('/upload')

  await page.locator('#file').setInputFiles({
    name: 'big.gpkg',
    mimeType: 'application/octet-stream',
    buffer: Buffer.from('fake file content'),
  })
  await page.getByRole('button', { name: 'Upload' }).click()

  await expect(page.locator('[data-sonner-toast]')).toHaveText(API_ERROR_MESSAGE)
})
