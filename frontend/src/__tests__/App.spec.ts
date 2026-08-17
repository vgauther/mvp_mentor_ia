import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App.vue'
import { useAuthStore } from '../stores/auth'
import type { AuthUser } from '../types/api'

vi.mock('../auth/keycloak', () => ({
  default: {
    logout: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
    updateToken: vi.fn<() => Promise<boolean>>().mockResolvedValue(false),
    token: 'jeton-test',
  },
}))

function mountApp(role: AuthUser['role']) {
  const pinia = createPinia()
  setActivePinia(pinia)

  const auth = useAuthStore()
  auth.user = {
    id: 1,
    keycloak_id: 'keycloak-user-1',
    username: 'victor',
    email: 'victor@example.com',
    display_name: 'Victor',
    role,
    role_label: role === 'admin' ? 'Administrateur' : 'Apprenant',
    roles: [role],
  }

  return mount(App, {
    global: {
      plugins: [pinia],
      stubs: {
        RouterLink: {
          template: '<a><slot /></a>',
        },
        RouterView: true,
      },
    },
  })
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('App', () => {
  it("affiche la navigation d'administration pour un administrateur", () => {
    const wrapper = mountApp('admin')

    expect(wrapper.text()).toContain('Mentor IA')
    expect(wrapper.text()).toContain("Vue d'ensemble")
    expect(wrapper.text()).toContain('Utilisateurs')
    expect(wrapper.text()).toContain('Administrateur')
  })

  it("limite la navigation d'un apprenant à son espace", () => {
    const wrapper = mountApp('learner')

    expect(wrapper.text()).toContain('Mon espace')
    expect(wrapper.text()).toContain('Apprenant')
    expect(wrapper.text()).not.toContain('Utilisateurs')
  })
})
