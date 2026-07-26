import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import App from '../App.vue'

describe('App', () => {
  it('affiche la page de l’utilisateur connecté', () => {
    const wrapper = mount(App)

    expect(wrapper.text()).toContain('Le Bon Prénom')
    expect(wrapper.text()).toContain('Bienvenue Utilisateur')
    expect(wrapper.text()).toContain('Vous êtes connecté avec Keycloak.')
    expect(wrapper.get('button').text()).toBe('Se déconnecter')
  })
})
