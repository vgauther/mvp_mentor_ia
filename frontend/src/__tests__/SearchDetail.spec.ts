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

const acceptedMember = {
  id: 92,
  profile: {
    id: 25,
    username: 'partenaire',
    display_name: 'Camille',
  },
  role: 'member' as const,
  role_label: 'Participant',
  invitation_status: 'accepted' as const,
  invitation_status_label: 'Acceptée',
  created_at: '2026-08-04T09:00:00Z',
  updated_at: '2026-08-04T09:00:00Z',
}

const pendingMember = {
  ...acceptedMember,
  id: 93,
  invitation_status: 'pending' as const,
  invitation_status_label: 'En attente',
}

const firstNameOrigins = [
  {
    id: 'latine',
    label: 'Latine',
    description: 'Origine latine.',
  },
]

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

describe('SearchDetail', () => {
  it('organise le parcours, les résultats, les participants et les paramètres', async () => {
    authenticatedFetchMock
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))

    const wrapper = mount(SearchDetail, {
      props: {
        search: activeSearch,
        userId: 12,
      },
    })

    expect(wrapper.get('[data-test="workspace-settings"]').classes()).toContain('active')
    expect(wrapper.text()).toContain('Gestion de la recherche')

    await wrapper.get('[data-test="workspace-results"]').trigger('click')
    await flushPromises()

    expect(authenticatedFetchMock).toHaveBeenNthCalledWith(1, '/api/searches/41/matches/')
    expect(wrapper.text()).toContain('Les matchs de « Notre futur prénom »')

    await wrapper.get('[data-test="show-liked-results"]').trigger('click')
    await flushPromises()

    expect(authenticatedFetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/searches/41/liked-first-names/',
    )
    expect(wrapper.text()).toContain('Mes prénoms aimés dans « Notre futur prénom »')

    await wrapper.get('[data-test="workspace-participants"]').trigger('click')

    expect(wrapper.text()).toContain('Participants')
    expect(wrapper.text()).not.toContain('Gestion de la recherche')
  })

  it('permet au propriétaire de modifier les informations et les filtres', async () => {
    const updatedSearch: NameSearch = {
      ...activeSearch,
      title: 'Notre nouvelle recherche',
      genders: ['female'],
      origins: ['latine'],
      min_length: 4,
      max_length: 8,
      first_letters: ['A'],
      updated_at: '2026-08-04T10:00:00Z',
    }

    authenticatedFetchMock
      .mockResolvedValueOnce(jsonResponse(firstNameOrigins))
      .mockResolvedValueOnce(jsonResponse(updatedSearch))

    const wrapper = mount(SearchDetail, {
      props: {
        search: activeSearch,
        userId: 12,
      },
    })

    await wrapper.get('[data-test="edit-search-button"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-test="edit-search-title"]').setValue('  Notre nouvelle recherche  ')
    await wrapper.get('[data-test="edit-search-gender-male"]').trigger('change')
    await wrapper.get('[data-test="edit-search-gender-mixed"]').trigger('change')
    await wrapper.get('[data-test="edit-search-origin-latine"]').trigger('change')
    await wrapper.get('[data-test="edit-search-min-length"]').setValue('4')
    await wrapper.get('[data-test="edit-search-max-length"]').setValue('8')
    await wrapper.get('[data-test="edit-search-first-letter-A"]').trigger('change')
    await wrapper.get('[data-test="edit-search-form"]').trigger('submit')
    await flushPromises()

    expect(authenticatedFetchMock).toHaveBeenCalledTimes(2)
    expect(authenticatedFetchMock).toHaveBeenCalledWith('/api/searches/41/', {
      method: 'PATCH',
      body: JSON.stringify({
        title: 'Notre nouvelle recherche',
        genders: ['female'],
        origins: ['latine'],
        min_length: 4,
        max_length: 8,
        first_letters: ['A'],
      }),
    })
    expect(wrapper.text()).toContain('Notre nouvelle recherche')
    expect(wrapper.text()).toContain('Les informations de la recherche ont bien été enregistrées.')
    expect(wrapper.find('[data-test="edit-search-form"]').exists()).toBe(false)
    expect(wrapper.emitted('searchUpdated')?.[0]).toEqual([updatedSearch])
  })

  it('refuse localement une modification sans genre', async () => {
    authenticatedFetchMock.mockResolvedValueOnce(jsonResponse(firstNameOrigins))

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

    expect(authenticatedFetchMock).toHaveBeenCalledTimes(1)
    expect(authenticatedFetchMock).toHaveBeenCalledWith('/api/first-name-origins/')
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

  it('permet au propriétaire de retirer un participant accepté', async () => {
    const searchWithMember: NameSearch = {
      ...activeSearch,
      participants: [...activeSearch.participants, acceptedMember],
    }
    authenticatedFetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    const wrapper = mount(SearchDetail, {
      props: {
        search: searchWithMember,
        userId: 12,
      },
    })

    await wrapper.get('[data-test="workspace-participants"]').trigger('click')
    await wrapper.get('[data-test="remove-participant-92"]').trigger('click')
    expect(wrapper.get('[data-test="participant-confirmation"]').text()).toContain(
      'Retirer ce participant ?',
    )
    expect(wrapper.get('[data-test="participant-confirmation"]').text()).toContain(
      'Camille n’aura plus accès à cette recherche et ses décisions seront supprimées.',
    )

    await wrapper.get('[data-test="confirm-participant-action"]').trigger('click')
    await flushPromises()

    expect(authenticatedFetchMock).toHaveBeenCalledWith('/api/searches/41/participants/92/', {
      method: 'DELETE',
    })
    expect(wrapper.text()).toContain('Le participant a bien été retiré de la recherche.')
    expect(wrapper.text()).not.toContain('Camille')
    expect(wrapper.emitted('searchUpdated')?.[0]).toEqual([
      {
        ...searchWithMember,
        participants: activeSearch.participants,
      },
    ])
  })

  it('permet au propriétaire d’annuler une invitation en attente', async () => {
    const searchWithInvitation: NameSearch = {
      ...activeSearch,
      participants: [...activeSearch.participants, pendingMember],
    }
    authenticatedFetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    const wrapper = mount(SearchDetail, {
      props: {
        search: searchWithInvitation,
        userId: 12,
      },
    })

    await wrapper.get('[data-test="workspace-participants"]').trigger('click')
    await wrapper.get('[data-test="cancel-invitation-93"]').trigger('click')
    expect(wrapper.get('[data-test="participant-confirmation"]').text()).toContain(
      'Annuler cette invitation ?',
    )

    await wrapper.get('[data-test="confirm-participant-action"]').trigger('click')
    await flushPromises()

    expect(authenticatedFetchMock).toHaveBeenCalledWith('/api/searches/41/participants/93/', {
      method: 'DELETE',
    })
    expect(wrapper.text()).toContain('L’invitation a bien été annulée.')
    expect(wrapper.find('[data-test="search-invitation-form"]').exists()).toBe(true)
  })

  it('permet à un participant accepté de quitter la recherche', async () => {
    const memberSearch: NameSearch = {
      ...activeSearch,
      creator: {
        id: 12,
        username: 'utilisateur',
        display_name: 'Victor',
      },
      participants: [...activeSearch.participants, acceptedMember],
    }
    authenticatedFetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    const wrapper = mount(SearchDetail, {
      props: {
        search: memberSearch,
        userId: 25,
      },
    })

    await wrapper.get('[data-test="workspace-participants"]').trigger('click')
    await wrapper.get('[data-test="leave-search"]').trigger('click')
    expect(wrapper.get('[data-test="participant-confirmation"]').text()).toContain(
      'Quitter cette recherche ?',
    )

    await wrapper.get('[data-test="confirm-participant-action"]').trigger('click')
    await flushPromises()

    expect(authenticatedFetchMock).toHaveBeenCalledWith('/api/searches/41/participants/me/', {
      method: 'DELETE',
    })
    expect(wrapper.emitted('back')).toHaveLength(1)
  })

  it('ne supprime rien lorsque la confirmation est refusée', async () => {
    const searchWithMember: NameSearch = {
      ...activeSearch,
      participants: [...activeSearch.participants, acceptedMember],
    }
    const wrapper = mount(SearchDetail, {
      props: {
        search: searchWithMember,
        userId: 12,
      },
    })

    await wrapper.get('[data-test="workspace-participants"]').trigger('click')
    await wrapper.get('[data-test="remove-participant-92"]').trigger('click')
    await wrapper.get('[data-test="cancel-participant-action"]').trigger('click')
    await flushPromises()

    expect(authenticatedFetchMock).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="participant-confirmation"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Camille')
  })
})
