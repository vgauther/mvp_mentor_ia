<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { apiRequest } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { ManagedUser } from '../types/api'

const auth = useAuthStore()
const users = ref<ManagedUser[]>([])
const isLoading = ref(true)

const adminCount = computed(() => users.value.filter((user) => user.role === 'admin').length)
const learnerCount = computed(() => users.value.filter((user) => user.role === 'learner').length)

onMounted(async () => {
  try {
    users.value = await apiRequest<ManagedUser[]>('/api/admin/users/')
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <section class="admin-home">
    <div class="page-heading">
      <div>
        <p class="eyebrow">Administration</p>
        <h1>Bonjour {{ auth.displayName }}</h1>
        <p class="page-heading__intro">
          Pilotez les accès de votre plateforme et préparez les futurs parcours de formation.
        </p>
      </div>
      <span class="role-pill">Administrateur</span>
    </div>

    <div class="admin-hero">
      <div class="admin-hero__content">
        <span class="admin-hero__label">Votre espace est prêt</span>
        <h2>Construisons une expérience d'apprentissage plus humaine.</h2>
        <p>
          La gestion des comptes est disponible. Les formations et le Mentor IA viendront enrichir
          cet espace lors des prochaines étapes.
        </p>
        <RouterLink to="/admin/users" class="button button--primary">
          Gérer les utilisateurs
          <span aria-hidden="true">→</span>
        </RouterLink>
      </div>
      <div class="admin-hero__visual" aria-hidden="true">
        <div class="orbit orbit--one"></div>
        <div class="orbit orbit--two"></div>
        <div class="mentor-symbol">
          <span>M</span>
        </div>
        <div class="floating-card floating-card--top">
          <strong>{{ isLoading ? '—' : users.length }}</strong>
          <span>utilisateurs</span>
        </div>
        <div class="floating-card floating-card--bottom">
          <i></i>
          <span>Plateforme active</span>
        </div>
      </div>
    </div>

    <div class="stats-grid" aria-label="Statistiques utilisateurs">
      <article class="stat-card">
        <span class="stat-card__icon stat-card__icon--blue">A</span>
        <div>
          <strong>{{ isLoading ? '—' : adminCount }}</strong>
          <span>Administrateurs</span>
        </div>
      </article>
      <article class="stat-card">
        <span class="stat-card__icon">U</span>
        <div>
          <strong>{{ isLoading ? '—' : learnerCount }}</strong>
          <span>Apprenants</span>
        </div>
      </article>
      <article class="stat-card stat-card--muted">
        <span class="stat-card__icon">F</span>
        <div>
          <strong>0</strong>
          <span>Formations publiées</span>
        </div>
        <small>Bientôt disponible</small>
      </article>
    </div>
  </section>
</template>
