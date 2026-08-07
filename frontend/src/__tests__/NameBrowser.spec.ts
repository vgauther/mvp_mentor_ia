import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import NameBrowser from '../components/NameBrowser.vue'
import type { FirstName } from '../types/api'

const { authenticatedFetchMock, getErrorMessageMock } = vi.hoisted(() => ({
  authenticatedFetchMock: vi.fn<(path: string, options?: RequestInit) => Promise<Response>>(),
  getErrorMessageMock: vi.fn<(response: Response, fallbackMessage: string) => Promise<string>>(),
}))

vi.mock('../api/client', () => ({
  authenticatedFetch: authenticatedFetchMock,
  getErrorMessage: getErrorMessageMock,
}))

const firstName: FirstName = {
  id: 17,
  name: 'Élodie',
  gender: 'female',
  gender_label: 'Féminin',
  origin: 'francaise',
  origin_label: 'Française',
  origin_description: 'Origine française.',
  meaning: 'Richesse',
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

afterEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
})

describe('NameBrowser', () => {
  it('ne propose que les choix aimer et ne pas aimer', async () => {
    authenticatedFetchMock.mockResolvedValueOnce(jsonResponse(firstName))

    const wrapper = mount(NameBrowser, {
      props: {
        searchId: 41,
        searchTitle: 'Notre futur prénom',
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Je n’aime pas')
    expect(wrapper.text()).toContain('J’aime')
    expect(wrapper.text()).not.toContain('Passer')
    expect(wrapper.text()).not.toContain('parcouru')
  })

  it('enregistre un choix puis charge le prénom suivant', async () => {
    authenticatedFetchMock
      .mockResolvedValueOnce(jsonResponse(firstName))
      .mockResolvedValueOnce(jsonResponse({ id: 32 }, 201))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    const wrapper = mount(NameBrowser, {
      props: {
        searchId: 41,
        searchTitle: 'Notre futur prénom',
      },
    })

    await flushPromises()
    await wrapper.get('.like-button').trigger('click')
    await flushPromises()

    expect(authenticatedFetchMock).toHaveBeenNthCalledWith(2, '/api/searches/41/decisions/', {
      method: 'POST',
      body: JSON.stringify({
        first_name_id: 17,
        choice: 'liked',
      }),
    })
    expect(authenticatedFetchMock).toHaveBeenNthCalledWith(3, '/api/searches/41/next-first-name/')
  })
})
