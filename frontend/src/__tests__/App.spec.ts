import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App.vue'

vi.mock('../auth/keycloak', () => ({
  default: {
    token: 'jeton-test',
    updateToken: vi
      .fn<(minValidity: number) => Promise<boolean>>()
      .mockResolvedValue(false),
    logout: vi
      .fn<(options: { redirectUri: string }) => Promise<void>>()
      .mockResolvedValue(undefined),
  },
}))

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  vi.clearAllMocks()
})

describe('App', () => {
  it('envoie le jeton Keycloak à Django et affiche l’utilisateur', async () => {
    const response = new Response(
      JSON.stringify({
        id: 'identifiant-test',
        username: 'Utilisateur',
        email: 'utilisateur@example.com',
        roles: ['user'],
      }),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      },
    )

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(response)

    vi.stubEnv('VITE_API_URL', 'http://127.0.0.1:8000')
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(App)

    expect(wrapper.text()).toContain(
      'Vérification de votre identité...',
    )

    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/me/',
      {
        headers: {
          Authorization: 'Bearer jeton-test',
        },
      },
    )

    expect(wrapper.text()).toContain('Le Bon Prénom')
    expect(wrapper.text()).toContain('Bienvenue Utilisateur')
    expect(wrapper.text()).toContain(
      'Votre identité a été validée par Django.',
    )
    expect(wrapper.text()).toContain('Rôles : user')
    expect(wrapper.get('button').text()).toBe('Se déconnecter')
  })

  it('affiche une erreur lorsque Django refuse la requête', async () => {
    vi.stubEnv('VITE_API_URL', 'http://127.0.0.1:8000')
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response(null, { status: 401 })),
    )

    const wrapper = mount(App)

    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe(
      "Impossible de vérifier votre identité auprès de Django.",
    )
  })
})
