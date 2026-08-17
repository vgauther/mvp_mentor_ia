<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import { useAuthStore } from './stores/auth'

const auth = useAuthStore()

const initials = computed(() => {
  const source = auth.displayName.trim()
  const parts = source.split(/\s+/).filter(Boolean)

  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink :to="auth.homePath" class="brand" aria-label="Accueil Mentor IA">
        <span class="brand__mark" aria-hidden="true">
          <span></span>
          <span></span>
        </span>
        <span>
          <strong>Mentor IA</strong>
          <small>Learning platform</small>
        </span>
      </RouterLink>

      <nav class="main-nav" aria-label="Navigation principale">
        <template v-if="auth.isAdmin">
          <RouterLink to="/admin">Vue d'ensemble</RouterLink>
          <RouterLink to="/admin/trainings">Formations</RouterLink>
          <RouterLink to="/admin/users">Utilisateurs</RouterLink>
        </template>
        <RouterLink v-else to="/learner">Mon espace</RouterLink>
      </nav>

      <div class="account">
        <div class="account__avatar" aria-hidden="true">{{ initials }}</div>
        <div class="account__identity">
          <strong>{{ auth.displayName }}</strong>
          <span>{{ auth.user?.role_label }}</span>
        </div>
        <button type="button" class="button button--quiet" @click="auth.logout">
          Se déconnecter
        </button>
      </div>
    </header>

    <main class="page-shell">
      <RouterView />
    </main>
  </div>
</template>
