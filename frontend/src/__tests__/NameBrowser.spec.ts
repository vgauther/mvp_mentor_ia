import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import NameBrowser from '../components/NameBrowser.vue'
import type { FirstName, NameSearch } from '../types/api'

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

const activeSearch: NameSearch = {
  id: 41,
  title: 'Notre futur prénom',
  genders: ['female', 'male', 'mixed'],
  origins: [],
  min_length: null,
  max_length: null,
  first_letters: [],
  status: 'active',
  status_label: 'Active',
  creator: {
    id: 12,
    username: 'utilisateur',
    display_name: 'Victor',
  },
  participants: [],
  created_at: '2026-08-04T08:00:00Z',
  updated_at: '2026-08-04T08:00:00Z',
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
        search: activeSearch,
        canEditFilters: true,
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Je n’aime pas')
    expect(wrapper.text()).toContain('J’aime')
    expect(wrapper.text()).not.toContain('Passer')
    expect(wrapper.text()).not.toContain('parcouru')
  })

  it('permet d’ouvrir les détails de la recherche depuis le parcours', async () => {
    authenticatedFetchMock.mockResolvedValueOnce(jsonResponse(firstName))

    const wrapper = mount(NameBrowser, {
      props: {
        search: activeSearch,
        canEditFilters: true,
      },
    })

    await flushPromises()
    await wrapper.get('[data-test="open-current-search-details"]').trigger('click')

    expect(wrapper.emitted('details')).toHaveLength(1)
  })

  it('enregistre un choix puis charge le prénom suivant', async () => {
    authenticatedFetchMock
      .mockResolvedValueOnce(jsonResponse(firstName))
      .mockResolvedValueOnce(jsonResponse({ id: 32 }, 201))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    const wrapper = mount(NameBrowser, {
      props: {
        search: activeSearch,
        canEditFilters: true,
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

  it('modifie les filtres depuis le parcours puis recharge une proposition', async () => {
    const origins = [
      {
        id: 'latine',
        label: 'Latine',
        description: 'Origine latine.',
      },
    ]
    const updatedSearch: NameSearch = {
      ...activeSearch,
      genders: ['female'],
      origins: ['latine'],
      min_length: 4,
      max_length: 8,
      first_letters: ['A'],
    }

    authenticatedFetchMock
      .mockResolvedValueOnce(jsonResponse(firstName))
      .mockResolvedValueOnce(jsonResponse(origins))
      .mockResolvedValueOnce(jsonResponse(updatedSearch))
      .mockResolvedValueOnce(jsonResponse({ ...firstName, id: 18, name: 'Alice' }))

    const wrapper = mount(NameBrowser, {
      props: {
        search: activeSearch,
        canEditFilters: true,
      },
    })

    await flushPromises()
    await wrapper.get('[data-test="open-quick-filters"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="quick-filter-gender-male"]').trigger('change')
    await wrapper.get('[data-test="quick-filter-gender-mixed"]').trigger('change')
    await wrapper.get('[data-test="quick-filter-origin-latine"]').trigger('change')
    await wrapper.get('[data-test="quick-filter-min-length"]').setValue('4')
    await wrapper.get('[data-test="quick-filter-max-length"]').setValue('8')
    await wrapper.get('[data-test="quick-filter-first-letter-A"]').trigger('change')
    await wrapper.get('[data-test="save-quick-filters"]').trigger('submit')
    await flushPromises()

    expect(authenticatedFetchMock).toHaveBeenNthCalledWith(3, '/api/searches/41/', {
      method: 'PATCH',
      body: JSON.stringify({
        genders: ['female'],
        origins: ['latine'],
        min_length: 4,
        max_length: 8,
        first_letters: ['A'],
      }),
    })
    expect(authenticatedFetchMock).toHaveBeenNthCalledWith(4, '/api/searches/41/next-first-name/')
    expect(wrapper.find('[data-test="quick-filters-panel"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.emitted('searchUpdated')?.[0]).toEqual([updatedSearch])
  })

  it('masque la modification des filtres pour un participant', async () => {
    authenticatedFetchMock.mockResolvedValueOnce(jsonResponse(firstName))

    const wrapper = mount(NameBrowser, {
      props: {
        search: activeSearch,
        canEditFilters: false,
      },
    })

    await flushPromises()

    expect(wrapper.find('[data-test="open-quick-filters"]').exists()).toBe(false)
  })
})
