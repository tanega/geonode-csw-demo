import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'

import { mount } from '@vue/test-utils'
import App from '../App.vue'
import router from '../router'

describe('App', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('mounts renders properly', async () => {
    const testRouter = createRouter({
      history: createWebHistory(),
      routes: router.getRoutes(),
    })
    testRouter.push('/')
    await testRouter.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [testRouter],
      },
    })
    expect(wrapper.text()).toContain('GeoNode Demo')
  })
})
