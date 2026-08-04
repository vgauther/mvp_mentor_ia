import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import SearchDetail from '../components/SearchDetail.vue'
import type { NameSearch } from '../types/api'

const { authenticatedFetchMock, getErrorMessageMock } = vi.hoisted(() => ({
  authenticatedFetchMock: vi.fn<(path: string, options?: RequestInit) => Promise<Response>>(),
  getErrorMessageMock: vi.fn<(response: Response, fallbackMessage: string) => Promise<string>>(),
}))

vi.mock('../api/client', () => ({
  authenticatedFetch: authenticatedFetchMock,
  getErrorMessage: getErrorMessageMock,
}))

const activeSearch: NameSearch = {
  id: 41,
  title: 'Notre futur prénom',
  genders: ['female', 'male', 'mixed'],
  status: 'active',
  status_label: 'Active',
  creator: {
    id: 12,
    username: 'utilisateur',
    display_name: 'Victor',
  },
  participants: [
    {
      id: 91,
      profile: {
        id: 12,
        username: 'utilisateur',
        display_name: 'Victor',
      },
      role: 'owner',
      role_label: 'Propriétaire',
      invitation_status: 'accepted',
      invitation_status_label: 'Acceptée',
      created_at: '2026-08-04T08:00:00Z',
      updated_at: '2026-08-04T08:00:00Z',
    },
  ],
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
})

describe('SearchDetail', () => {
  it('permet au propriétaire de modifier le titre et les genres', async () => {
    const updatedSearch: NameSearch = {
      ...activeSearch,
      title: 'Notre nouvelle recherche',
      genders: ['female'],
      updated_at: '2026-08-04T10:00:00Z',
    }

    authenticatedFetchMock.mockResolvedValueOnce(jsonResponse(updatedSearch))

    const wrapper = mount(SearchDetail, {
      props: {
        search: activeSearch,
        userId: 12,
      },
    })

    await wrapper.get('[data-test="edit-search-button"]').trigger('click')
    await wrapper.get('[data-test="edit-search-title"]').setValue('  Notre nouvelle recherche  ')
    await wrapper.get('[data-test="edit-search-gender-male"]').trigger('change')
    await wrapper.get('[data-test="edit-search-gender-mixed"]').trigger('change')
    await wrapper.get('[data-test="edit-search-form"]').trigger('submit')
    await flushPromises()

    expect(authenticatedFetchMock).toHaveBeenCalledTimes(1)
    expect(authenticatedFetchMock).toHaveBeenCalledWith('/api/searches/41/', {
      method: 'PATCH',
      body: JSON.stringify({
        title: 'Notre nouvelle recherche',
        genders: ['female'],
      }),
    })
    expect(wrapper.text()).toContain('Notre nouvelle recherche')
    expect(wrapper.text()).toContain('Les informations de la recherche ont bien été enregistrées.')
    expect(wrapper.find('[data-test="edit-search-form"]').exists()).toBe(false)
    expect(wrapper.emitted('searchUpdated')?.[0]).toEqual([updatedSearch])
  })

  it('refuse localement une modification sans genre', async () => {
    const wrapper = mount(SearchDetail, {
      props: {
        search: activeSearch,
        userId: 12,
      },
    })

    await wrapper.get('[data-test="edit-search-button"]').trigger('click')
    await wrapper.get('[data-test="edit-search-gender-female"]').trigger('change')
    await wrapper.get('[data-test="edit-search-gender-male"]').trigger('change')
    await wrapper.get('[data-test="edit-search-gender-mixed"]').trigger('change')
    await wrapper.get('[data-test="edit-search-form"]').trigger('submit')
    await flushPromises()

    expect(authenticatedFetchMock).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"]').text()).toBe('Sélectionne au moins un type de prénom.')
  })

  it('ne propose pas la modification à un simple participant', () => {
    const memberSearch: NameSearch = {
      ...activeSearch,
      creator: {
        id: 25,
        username: 'proprietaire',
        display_name: 'Propriétaire',
      },
      participants: [
        {
          ...activeSearch.participants[0]!,
          role: 'member',
          role_label: 'Participant',
        },
      ],
    }

    const wrapper = mount(SearchDetail, {
      props: {
        search: memberSearch,
        userId: 12,
      },
    })

    expect(wrapper.find('[data-test="edit-search-button"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Partagée avec moi')
  })
})