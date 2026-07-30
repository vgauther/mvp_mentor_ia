import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App.vue'

const { logoutMock, updateTokenMock } = vi.hoisted(() => ({
  logoutMock: vi.fn<(options: { redirectUri: string }) => Promise<void>>(),
  updateTokenMock: vi.fn<(minValidity: number) => Promise<boolean>>(),
}))

logoutMock.mockResolvedValue(undefined)
updateTokenMock.mockResolvedValue(false)

vi.mock('../auth/keycloak', () => ({
  default: {
    token: 'jeton-test',
    updateToken: updateTokenMock,
    logout: logoutMock,
  },
}))

const profile = {
  id: 12,
  username: 'utilisateur',
  email: 'utilisateur@example.com',
  display_name: 'Victor',
  roles: ['parent', 'user'],
  created_at: '2026-07-30T08:30:00Z',
  updated_at: '2026-07-30T08:30:00Z',
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
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  vi.clearAllMocks()

  logoutMock.mockResolvedValue(undefined)
  updateTokenMock.mockResolvedValue(false)
})

describe('App', () => {
  it('envoie le jeton Keycloak et affiche le profil Django', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(profile))

    vi.stubEnv('VITE_API_URL', 'http://127.0.0.1:8000')
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(App)

    expect(wrapper.text()).toContain('Vérification de votre identité')

    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)

    const firstCall = fetchMock.mock.calls[0]

    if (!firstCall) {
      throw new Error("L'appel initial vers Django n'a pas été effectué.")
    }

    const [url, options] = firstCall
    const headers = new Headers(options?.headers)

    expect(url).toBe('http://127.0.0.1:8000/api/me/')
    expect(headers.get('Authorization')).toBe('Bearer jeton-test')

    expect(wrapper.text()).toContain('Bonjour Victor')
    expect(wrapper.text()).toContain('Votre identité a été validée par Django.')
    expect(wrapper.text()).toContain('utilisateur@example.com')
    expect(wrapper.text()).toContain('parent')
    expect(wrapper.text()).toContain('user')
  })

  it('modifie le nom d’affichage avec PATCH', async () => {
    const updatedProfile = {
      ...profile,
      display_name: 'Nouveau nom',
    }

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse(updatedProfile))

    vi.stubEnv('VITE_API_URL', 'http://127.0.0.1:8000')
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(App)

    await flushPromises()

    await wrapper.get('[data-test="display-name-input"]').setValue('Nouveau nom')

    await wrapper.get('[data-test="profile-form"]').trigger('submit')

    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(2)

    const patchCall = fetchMock.mock.calls[1]

    if (!patchCall) {
      throw new Error("L'appel PATCH vers Django n'a pas été effectué.")
    }

    const [url, options] = patchCall
    const headers = new Headers(options?.headers)

    expect(url).toBe('http://127.0.0.1:8000/api/me/')
    expect(options?.method).toBe('PATCH')
    expect(options?.body).toBe(
      JSON.stringify({
        display_name: 'Nouveau nom',
      }),
    )
    expect(headers.get('Authorization')).toBe('Bearer jeton-test')
    expect(headers.get('Content-Type')).toBe('application/json')

    expect(wrapper.text()).toContain('Votre nom d’affichage a bien été enregistré.')
    expect(wrapper.text()).toContain('Bonjour Nouveau nom')
  })

  it('recherche un utilisateur avec son e-mail exact', async () => {
    const foundProfile = {
      id: 25,
      username: 'autre-utilisateur',
      email: 'autre@example.com',
      display_name: 'Autre personne',
    }

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse(foundProfile))

    vi.stubEnv('VITE_API_URL', 'http://127.0.0.1:8000')
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(App)

    await flushPromises()

    await wrapper.get('[data-test="lookup-email-input"]').setValue('autre@example.com')

    await wrapper.get('[data-test="lookup-form"]').trigger('submit')

    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(2)

    const lookupCall = fetchMock.mock.calls[1]

    if (!lookupCall) {
      throw new Error("L'appel de recherche vers Django n'a pas été effectué.")
    }

    const [url, options] = lookupCall
    const headers = new Headers(options?.headers)

    expect(url).toBe('http://127.0.0.1:8000/api/profiles/lookup/' + '?email=autre%40example.com')
    expect(headers.get('Authorization')).toBe('Bearer jeton-test')

    const result = wrapper.get('[data-test="lookup-result"]')

    expect(result.text()).toContain('Utilisateur trouvé')
    expect(result.text()).toContain('Autre personne')
    expect(result.text()).toContain('autre@example.com')
    expect(result.text()).toContain('@autre-utilisateur')
  })

  it('affiche une erreur lorsque Django refuse la connexion', async () => {
    vi.stubEnv('VITE_API_URL', 'http://127.0.0.1:8000')
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 401 })),
    )

    const wrapper = mount(App)

    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe(
      'Impossible de vérifier votre identité auprès de Django.',
    )
  })
})
