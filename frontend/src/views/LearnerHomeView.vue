<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { apiRequest } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { LearnerTraining } from '../types/api'

const auth = useAuthStore()
const trainings = ref<LearnerTraining[]>([])
const isLoading = ref(true)
const errorMessage = ref('')

async function loadTrainings() {
  try {
    trainings.value = await apiRequest<LearnerTraining[]>('/api/learner/trainings/')
  } catch (error) {
    console.error('Échec du chargement des formations attribuées :', error)
    errorMessage.value = 'Impossible de charger vos formations.'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => void loadTrainings())
</script>

<template>
  <section class="learner-space">
    <div class="learner-home">
      <div class="learner-home__copy">
      <p class="eyebrow">Espace apprenant</p>
      <h1>Hello {{ auth.displayName }} <span aria-hidden="true">👋</span></h1>
      <p>
        Retrouvez ici les formations qui vous ont été attribuées.
      </p>
      <span class="role-pill">Apprenant</span>
      </div>

      <div class="learner-home__card" aria-hidden="true">
        <div class="learner-home__glow"></div>
        <div class="mentor-symbol mentor-symbol--large"><span>M</span></div>
        <span class="learner-home__caption">Votre Mentor IA vous attend</span>
      </div>
    </div>

    <div class="learner-trainings">
      <div class="learner-trainings__heading">
        <div>
          <p class="section-kicker">Mon parcours</p>
          <h2>Mes formations</h2>
        </div>
        <span>{{ trainings.length }} attribuée{{ trainings.length > 1 ? 's' : '' }}</span>
      </div>
      <p v-if="errorMessage" class="feedback feedback--error" role="alert">{{ errorMessage }}</p>
      <div v-if="isLoading" class="learner-trainings__empty">Chargement de vos formations…</div>
      <div v-else-if="trainings.length === 0" class="learner-trainings__empty">
        Aucune formation ne vous a encore été attribuée.
      </div>
      <div v-else class="learner-training-grid">
        <article v-for="training in trainings" :key="training.id" class="learner-training-card">
          <span class="status-badge">{{ training.status_label }}</span>
          <h3>{{ training.title }}</h3>
          <p>{{ training.description || 'Aucune description renseignée.' }}</p>
        </article>
      </div>
    </div>
  </section>
</template>
