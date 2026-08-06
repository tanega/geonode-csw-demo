import { test, expect } from '@playwright/test'

const LIST_RESPONSE = {
  total: 1,
  page: 1,
  page_size: 20,
  resources: [
    {
      pk: '1',
      uuid: 'fake-uuid',
      resource_type: 'dataset',
      subtype: 'raster',
      title: 'lisbon_elevation',
      abstract: 'Elevation raster for Lisbon.',
      thumbnail_url: '',
      detail_url: '',
      srid: 'EPSG:4326',
      date: '2026-01-01T00:00:00Z',
      owner: { username: 'admin' },
      links: [
        { extension: 'html', link_type: 'OGC:WMS', name: 'OGC WMS: geonode Service', mime: 'text/html', url: 'http://geoserver/ows' },
        { extension: 'tif', link_type: 'data', name: 'GeoTIFF', mime: 'image/tiff', url: 'http://geoserver/wcs' },
        { extension: 'tif', link_type: 'data', name: 'Cloud-Optimized GeoTIFF (COG) on MinIO', mime: 'image/tiff', url: 'http://minio/cog.tif' },
      ],
    },
  ],
}

test('browsing datasets from the homepage to a detail page', async ({ page }) => {
  await page.route('**/api/v2/resources/?page=*', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(LIST_RESPONSE) }),
  )
  await page.route('**/api/v2/resources/1/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ resource: LIST_RESPONSE.resources[0] }),
    }),
  )

  await page.goto('/')
  await expect(page.getByText('lisbon_elevation')).toBeVisible()

  await page.getByText('lisbon_elevation').click()
  await expect(page).toHaveURL(/\/datasets\/1$/)
  await expect(page.getByRole('heading', { name: 'lisbon_elevation' })).toBeVisible()
  await expect(page.getByText('OGC services')).toBeVisible()
  await expect(page.getByRole('link', { name: 'OGC WMS: geonode Service' })).toBeVisible()
  await expect(page.getByText('Cloud-native')).toBeVisible()
})

test('filtering datasets by title on the homepage', async ({ page }) => {
  await page.route('**/api/v2/resources/?page=*', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(LIST_RESPONSE) }),
  )

  await page.goto('/')
  await expect(page.getByText('lisbon_elevation')).toBeVisible()

  await page.getByPlaceholder('Search datasets by title…').fill('nonexistent')
  await expect(page.getByText('No datasets found.')).toBeVisible()
})
