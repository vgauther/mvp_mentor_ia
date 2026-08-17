<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiRequest } from '../api/client'
import type { TrainingDetail, TrainingSummary } from '../types/api'

const router = useRouter()
const trainings = ref<TrainingSummary[]>([])
const isLoading = ref(true)
const isCreating = ref(false)
const showCreation = ref(false)
const errorMessage = ref('')
const title = ref('')
const description = ref('')

const totalSources = computed(() =>
  trainings.value.reduce((total, training) => total + training.raw_material_count, 0),
)
const totalObjectives = computed(() =>
  trainings.value.reduce((total, training) => total + training.objective_count, 0),
)

async function loadTrainings() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    trainings.value = await apiRequest<TrainingSummary[]>('/api/admin/trainings/')
  } catch (error) {
    console.error('Échec du chargement des formations :', error)
    errorMessage.value = 'Impossible de charger les formations.'
  } finally {
    isLoading.value = false
  }
}

async function createTraining() {
  if (!title.value.trim()) return

  isCreating.value = true
  errorMessage.value = ''
  try {
    const training = await apiRequest<TrainingDetail>('/api/admin/trainings/', {
      method: 'POST',
      body: JSON.stringify({
        title: title.value.trim(),
        description: description.value.trim(),
      }),
    })
    await router.push(`/admin/trainings/${training.id}`)
  } catch (error) {
    console.error('Échec de la création de la formation :', error)
    errorMessage.value = 'La formation n’a pas pu être créée.'
  } finally {
    isCreating.value = false
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}

onMounted(() => void loadTrainings())
</script>

<template>
  <section>
    <div class="page-heading page-heading--compact">
      <div>
        <p class="eyebrow">Conception pédagogique</p>
        <h1>Formations</h1>
        <p class="page-heading__intro">
          Rassemblez les sources, fixez les objectifs et préparez la structure de chaque parcours.
        </p>
      </div>
      <button type="button" class="button button--primary" @click="showCreation = !showCreation">
        <span aria-hidden="true">＋</span>
        Nouvelle formation
      </button>
    </div>

    <form v-if="showCreation" class="creation-panel" @submit.prevent="createTraining">
      <div class="creation-panel__heading">
        <div>
          <span class="section-kicker">Nouveau brouillon</span>
          <h2>Créer une formation</h2>
        </div>
        <button type="button" class="icon-button" aria-label="Fermer" @click="showCreation = false">
          ×
        </button>
      </div>
      <div class="form-grid form-grid--training">
        <label class="form-field">
          <span>Nom de travail *</span>
          <input v-model="title" required maxlength="255" placeholder="Ex. Réussir sa prise de parole" />
        </label>
        <label class="form-field">
          <span>Contexte ou description</span>
          <textarea
            v-model="description"
            rows="3"
            placeholder="Public visé, contexte, contraintes connues…"
          ></textarea>
        </label>
      </div>
      <div class="creation-panel__actions">
        <span>Les titres définitifs et métadonnées pourront être générés plus tard.</span>
        <button class="button button--primary" :disabled="isCreating || !title.trim()">
          {{ isCreating ? 'Création…' : 'Créer et préparer' }}
        </button>
      </div>
    </form>

    <p v-if="errorMessage" class="feedback feedback--error" role="alert">{{ errorMessage }}</p>

    <div class="training-overview-stats">
      <div><strong>{{ trainings.length }}</strong><span>formations</span></div>
      <div><strong>{{ totalObjectives }}</strong><span>objectifs pédagogiques</span></div>
      <div><strong>{{ totalSources }}</strong><span>sources brutes</span></div>
    </div>

    <div v-if="isLoading" class="empty-state">Chargement des formations…</div>
    <div v-else-if="trainings.length === 0" class="empty-state empty-state--illustrated">
      <span class="empty-state__icon" aria-hidden="true">M</span>
      <h2>Votre premier parcours commence ici</h2>
      <p>Créez une formation, puis ajoutez ses objectifs et ses premières sources.</p>
      <button type="button" class="button button--primary" @click="showCreation = true">
        Créer une formation
      </button>
    </div>
    <div v-else class="training-grid">
      <RouterLink
        v-for="training in trainings"
        :key="training.id"
        :to="`/admin/trainings/${training.id}`"
        class="training-card"
      >
        <div class="training-card__topline">
          <span class="status-badge">{{ training.status_label }}</span>
          <span>Mis à jour le {{ formatDate(training.updated_at) }}</span>
        </div>
        <h2>{{ training.title }}</h2>
        <p>{{ training.description || 'Aucun contexte renseigné pour le moment.' }}</p>
        <div class="training-card__metrics">
          <span><strong>{{ training.objective_count }}</strong> objectifs</span>
          <span><strong>{{ training.unit_count }}</strong> éléments</span>
          <span><strong>{{ training.raw_material_count }}</strong> sources</span>
        </div>
        <span class="training-card__link">Préparer la formation <b>→</b></span>
      </RouterLink>
    </div>
  </section>
</template>
