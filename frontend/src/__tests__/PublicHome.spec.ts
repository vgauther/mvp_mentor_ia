import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import PublicHome from '../PublicHome.vue'

const { loginMock, registerMock } = vi.hoisted(() => ({
  loginMock: vi.fn<(options: { redirectUri: string; locale: string }) => Promise<void>>(),
  registerMock: vi.fn<(options: { redirectUri: string; locale: string }) => Promise<void>>(),
}))

vi.mock('../auth/keycloak', () => ({
  default: {
    login: loginMock,
    register: registerMock,
  },
}))

afterEach(() => {
  vi.clearAllMocks()
  loginMock.mockResolvedValue(undefined)
  registerMock.mockResolvedValue(undefined)
})

describe('PublicHome', () => {
  it('ouvre la connexion Keycloak depuis l’en-tête', async () => {
    loginMock.mockResolvedValue(undefined)
    const wrapper = mount(PublicHome)

    await wrapper.get('.header-login-button').trigger('click')
    await flushPromises()

    expect(loginMock).toHaveBeenCalledExactlyOnceWith({
      redirectUri: window.location.origin,
      locale: 'fr',
    })
  })

  it('ouvre la création de compte Keycloak depuis l’action principale', async () => {
    registerMock.mockResolvedValue(undefined)
    const wrapper = mount(PublicHome)

    await wrapper.get('.primary-button').trigger('click')
    await flushPromises()

    expect(registerMock).toHaveBeenCalledExactlyOnceWith({
      redirectUri: window.location.origin,
      locale: 'fr',
    })
  })

  it('affiche une erreur lorsque la redirection vers Keycloak échoue', async () => {
    loginMock.mockRejectedValue(new Error('Keycloak indisponible'))
    const wrapper = mount(PublicHome)

    await wrapper.get('.header-login-button').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(
      "Impossible d'ouvrir la page de connexion.",
    )
    expect(wrapper.get('.header-login-button').attributes('disabled')).toBeUndefined()
  })
})
