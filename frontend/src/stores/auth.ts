import { defineStore } from 'pinia'

import { apiRequest } from '../api/client'
import keycloak from '../auth/keycloak'
import type { AuthUser } from '../types/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as AuthUser | null,
  }),

  getters: {
    isAdmin: (state) => state.user?.role === 'admin',
    homePath: (state) => (state.user?.role === 'admin' ? '/admin' : '/learner'),
    displayName: (state) => state.user?.display_name || state.user?.username || 'Utilisateur',
  },

  actions: {
    async loadUser() {
      this.user = await apiRequest<AuthUser>('/api/me/')
    },

    async logout() {
      await keycloak.logout({
        redirectUri: window.location.origin,
      })
    },
  },
})
