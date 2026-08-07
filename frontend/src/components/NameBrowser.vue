<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { authenticatedFetch, getErrorMessage } from '../api/client'
import type { FirstName, NameDecisionChoice, NameSearch } from '../types/api'
import SearchFiltersPanel from './SearchFiltersPanel.vue'

const props = defineProps<{
  search: NameSearch
  canEditFilters: boolean
}>()

const emit = defineEmits<{
  back: []
  details: []
  searchUpdated: [search: NameSearch]
}>()

const firstName = ref<FirstName | null>(null)
const isLoading = ref(true)
const isSubmitting = ref(false)
const isFinished = ref(false)
const errorMessage = ref('')
const lastAction = ref<NameDecisionChoice | null>(null)
const isEditingFilters = ref(false)
const matchNotification = ref<FirstName | null>(null)

let matchNotificationTimeout: number | null = null

const activeFilterCount = computed(() => {
  let count = 0

  if (props.search.genders.length < 3) {
    count += 1
  }

  if (props.search.origins.length > 0) {
    count += 1
  }

  if (props.search.min_length !== null || props.search.max_length !== null) {
    count += 1
  }

  if (props.search.first_letters.length > 0) {
    count += 1
  }

  return count
})

const lastActionMessage = computed(() => {
  if (lastAction.value === 'liked') {
    return 'Prénom ajouté à tes favoris.'
  }

  if (lastAction.value === 'rejected') {
    return 'Prénom refusé.'
  }

  return ''
})

async function loadNextFirstName() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await authenticatedFetch(`/api/searches/${props.search.id}/next-first-name/`)

    if (response.status === 204) {
      firstName.value = null
      isFinished.value = true
      return
    }

    if (!response.ok) {
      errorMessage.value = await getErrorMessage(
        response,
        'Impossible de récupérer le prochain prénom.',
      )
      return
    }

    firstName.value = (await response.json()) as FirstName
    isFinished.value = false
  } catch (error) {
    console.error('Échec du chargement du prochain prénom :', error)
    errorMessage.value = 'Impossible de contacter Django pour charger un prénom.'
  } finally {
    isLoading.value = false
  }
}

async function choose(choice: NameDecisionChoice) {
  if (!firstName.value || isSubmitting.value) {
    return
  }

  const decidedFirstName = firstName.value

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    const response = await authenticatedFetch(`/api/searches/${props.search.id}/decisions/`, {
      method: 'POST',
      body: JSON.stringify({
        first_name_id: decidedFirstName.id,
        choice,
      }),
    })

    if (!response.ok) {
      errorMessage.value = await getErrorMessage(response, 'Impossible d’enregistrer ton choix.')
      return
    }

    const decision = (await response.json()) as { match_created?: boolean }

    lastAction.value = choice

    if (decision.match_created) {
      showMatchNotification(decidedFirstName)
    }

    await loadNextFirstName()
  } catch (error) {
    console.error('Échec de l’enregistrement de la décision :', error)
    errorMessage.value = 'Impossible de contacter Django pour enregistrer ton choix.'
  } finally {
    isSubmitting.value = false
  }
}

function showMatchNotification(matchedFirstName: FirstName) {
  if (matchNotificationTimeout !== null) {
    window.clearTimeout(matchNotificationTimeout)
  }

  matchNotification.value = matchedFirstName
  matchNotificationTimeout = window.setTimeout(() => {
    matchNotification.value = null
    matchNotificationTimeout = null
  }, 4000)
}

function openFilters() {
  isEditingFilters.value = true
}

function closeFilters() {
  isEditingFilters.value = false
}

async function handleFiltersSaved(updatedSearch: NameSearch) {
  emit('searchUpdated', updatedSearch)
  isEditingFilters.value = false
  firstName.value = null
  isFinished.value = false
  lastAction.value = null
  await loadNextFirstName()
}

onMounted(() => {
  void loadNextFirstName()
})

onBeforeUnmount(() => {
  if (matchNotificationTimeout !== null) {
    window.clearTimeout(matchNotificationTimeout)
  }
})
</script>

<template>
  <section class="browser-shell">
    <header class="browser-header">
      <div class="navigation-actions">
        <button
          type="button"
          class="back-button"
          data-test="back-to-searches"
          @click="emit('back')"
        >
          <span>←</span>
          Retour aux recherches
        </button>

        <button
          type="button"
          class="details-button"
          data-test="open-current-search-details"
          @click="emit('details')"
        >
          Détails
        </button>
      </div>

      <button
        v-if="canEditFilters"
        type="button"
        class="filters-button"
        data-test="open-quick-filters"
        @click="openFilters"
      >
        <span aria-hidden="true">☰</span>
        Filtres
        <strong v-if="activeFilterCount > 0">{{ activeFilterCount }}</strong>
      </button>
    </header>

    <div class="title-block">
      <span class="section-kicker">{{ search.title }}</span>
      <h2>Parcourir les prénoms</h2>
      <p>Découvre une proposition à la fois et indique simplement ce que tu en penses.</p>
    </div>

    <Transition name="match-toast">
      <aside
        v-if="matchNotification"
        class="match-notification"
        data-test="match-notification"
        role="status"
        aria-live="polite"
      >
        <span class="match-notification-icon" aria-hidden="true">♥</span>

        <span>
          <strong>C’est un match !</strong>
          <small>Vous aimez tous les deux {{ matchNotification.name }}.</small>
        </span>
      </aside>
    </Transition>

    <p v-if="lastActionMessage && !errorMessage" class="feedback success-feedback" role="status">
      {{ lastActionMessage }}
    </p>

    <p v-if="errorMessage" class="feedback error-feedback" role="alert">
      {{ errorMessage }}
    </p>

    <div v-if="isLoading" class="state-card" aria-live="polite">
      <span class="loader"></span>

      <div>
        <strong>Recherche du prochain prénom…</strong>
        <p>Nous préparons une proposition compatible avec ta recherche.</p>
      </div>
    </div>

    <div v-else-if="errorMessage && !firstName" class="state-card error-state">
      <span class="state-symbol">!</span>

      <div>
        <strong>Le prénom n’a pas pu être chargé</strong>
        <p>Tu peux réessayer sans perdre les choix déjà enregistrés.</p>

        <button type="button" class="retry-button" @click="loadNextFirstName">Réessayer</button>
      </div>
    </div>

    <div v-else-if="isFinished" class="finished-card">
      <span class="finished-icon">✓</span>
      <h3>Tu as parcouru tous les prénoms disponibles</h3>

      <p>
        Tes choix sont bien enregistrés. Tu pourras bientôt retrouver tes prénoms aimés et les
        matchs obtenus avec l’autre participant.
      </p>

      <button
        type="button"
        class="finish-button"
        data-test="back-to-searches"
        @click="emit('back')"
      >
        Revenir aux recherches
      </button>
    </div>

    <article v-else-if="firstName" class="name-card">
      <div class="name-decoration" aria-hidden="true">♡</div>

      <div class="name-content">
        <span class="gender-badge">{{ firstName.gender_label }}</span>
        <h3>{{ firstName.name }}</h3>

        <dl>
          <div>
            <dt>Origine</dt>
            <dd>{{ firstName.origin_label || 'Non renseignée' }}</dd>
          </div>

          <div>
            <dt>Signification</dt>
            <dd>{{ firstName.meaning || 'Non renseignée' }}</dd>
          </div>
        </dl>
      </div>

      <div class="decision-actions" aria-label="Choisir une décision">
        <button
          type="button"
          class="reject-button"
          :disabled="isSubmitting"
          @click="choose('rejected')"
        >
          <span>×</span>
          Je n’aime pas
        </button>

        <button type="button" class="like-button" :disabled="isSubmitting" @click="choose('liked')">
          <span>♥</span>
          J’aime
        </button>
      </div>

      <p v-if="isSubmitting" class="saving-message" role="status">Enregistrement de ton choix…</p>
    </article>

    <div v-if="isEditingFilters" class="filters-overlay" @click.self="closeFilters">
      <SearchFiltersPanel :search="search" @close="closeFilters" @saved="handleFiltersSaved" />
    </div>
  </section>
</template>

<style scoped>
.browser-shell {
  display: grid;
  gap: 20px;
}

.browser-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.navigation-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 16px;
}

.back-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  color: #7d6552;
  border: 0;
  background: transparent;
  cursor: pointer;
  font-weight: 800;
}

.back-button span {
  font-size: 1.15rem;
}

.details-button {
  min-height: 36px;
  padding: 0 12px;
  color: #6f5540;
  border: 1px solid #e6d3bf;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.88);
  cursor: pointer;
  font-weight: 850;
}

.filters-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  gap: 7px;
  padding: 0 13px;
  border: 1px solid #e6d3bf;
  border-radius: 12px;
  color: #6f5540;
  background: rgba(255, 255, 255, 0.9);
  cursor: pointer;
  font-weight: 850;
  box-shadow: 0 8px 20px rgba(91, 59, 29, 0.07);
}

.filters-button > span {
  color: #e68822;
  font-size: 0.95rem;
}

.filters-button strong {
  display: grid;
  min-width: 21px;
  height: 21px;
  place-items: center;
  padding: 0 5px;
  border-radius: 999px;
  color: #ffffff;
  background: #f49224;
  font-size: 0.69rem;
}

.filters-overlay {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(64, 43, 25, 0.35);
  backdrop-filter: blur(4px);
}

.title-block {
  text-align: center;
}

.section-kicker {
  color: #eb8a20;
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.title-block h2 {
  margin: 6px 0 8px;
  color: #45301f;
  font-size: clamp(2rem, 5vw, 3rem);
  letter-spacing: -0.04em;
}

.title-block p {
  margin: 0;
  color: #887361;
}

.match-notification {
  position: fixed;
  z-index: 120;
  right: 24px;
  bottom: 24px;
  display: flex;
  width: min(360px, calc(100vw - 32px));
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 18px;
  background: linear-gradient(135deg, #f49224, #e76f91);
  box-shadow: 0 18px 45px rgba(137, 69, 43, 0.28);
  pointer-events: none;
}

.match-notification-icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.2);
  font-size: 1.35rem;
}

.match-notification > span:last-child {
  display: grid;
  gap: 3px;
}

.match-notification strong {
  font-size: 1rem;
}

.match-notification small {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.82rem;
}

.match-toast-enter-active,
.match-toast-leave-active {
  transition:
    opacity 220ms ease,
    transform 220ms ease;
}

.match-toast-enter-from,
.match-toast-leave-to {
  opacity: 0;
  transform: translateY(16px) scale(0.96);
}

.feedback {
  margin: 0 auto;
  padding: 11px 15px;
  border-radius: 13px;
  font-size: 0.86rem;
  font-weight: 750;
}

.success-feedback {
  color: #287144;
  background: #e7f7ec;
}

.error-feedback {
  color: #a13e30;
  background: #fff0ed;
}

.state-card,
.finished-card,
.name-card {
  width: min(680px, 100%);
  margin: 0 auto;
  border: 1px solid rgba(126, 83, 35, 0.12);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 24px 65px rgba(105, 70, 31, 0.11);
}

.state-card {
  display: flex;
  min-height: 280px;
  align-items: center;
  justify-content: center;
  gap: 17px;
  padding: 35px;
}

.state-card strong {
  color: #4a3421;
  font-size: 1.05rem;
}

.state-card p {
  margin: 6px 0 0;
  color: #8b7765;
}

.loader {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border: 4px solid #fee6c2;
  border-top-color: #f49224;
  border-radius: 50%;
  animation: spin 750ms linear infinite;
}

.state-symbol {
  display: grid;
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  place-items: center;
  color: #a84444;
  border-radius: 50%;
  background: #fff0ec;
  font-size: 1.2rem;
  font-weight: 900;
}

.retry-button,
.finish-button {
  margin-top: 16px;
  padding: 10px 15px;
  color: #ffffff;
  border: 0;
  border-radius: 11px;
  background: #f49224;
  cursor: pointer;
  font-weight: 850;
}

.finished-card {
  display: grid;
  min-height: 370px;
  padding: 48px;
  place-items: center;
  align-content: center;
  text-align: center;
}

.finished-icon {
  display: grid;
  width: 68px;
  height: 68px;
  place-items: center;
  color: #2d7752;
  border-radius: 22px;
  background: #e3f7eb;
  font-size: 2rem;
  font-weight: 950;
}

.finished-card h3 {
  margin: 20px 0 10px;
  color: #483321;
  font-size: 1.45rem;
}

.finished-card p {
  max-width: 500px;
  margin: 0;
  color: #897462;
  line-height: 1.6;
}

.name-card {
  position: relative;
  overflow: hidden;
  padding: 42px;
  background:
    radial-gradient(circle at 95% 7%, rgba(163, 223, 241, 0.5), transparent 15rem),
    radial-gradient(circle at 4% 97%, rgba(255, 192, 101, 0.28), transparent 14rem),
    rgba(255, 255, 255, 0.96);
}

.name-decoration {
  position: absolute;
  top: 23px;
  right: 28px;
  color: rgba(237, 139, 33, 0.22);
  font-size: 4rem;
  font-weight: 900;
}

.name-content {
  position: relative;
  text-align: center;
}

.gender-badge {
  display: inline-flex;
  padding: 7px 12px;
  color: #276f84;
  border-radius: 999px;
  background: #e0f5fb;
  font-size: 0.76rem;
  font-weight: 850;
}

.name-content h3 {
  margin: 15px 0 28px;
  color: #44301f;
  font-size: clamp(3rem, 9vw, 5.4rem);
  letter-spacing: -0.055em;
  line-height: 1;
}

dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
  text-align: left;
}

dl div {
  min-width: 0;
  padding: 16px;
  border: 1px solid #f0e3d5;
  border-radius: 16px;
  background: rgba(255, 252, 247, 0.78);
}

dt {
  color: #d67a18;
  font-size: 0.69rem;
  font-weight: 900;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

dd {
  margin: 7px 0 0;
  color: #654c37;
  line-height: 1.5;
}

.decision-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 11px;
  margin-top: 28px;
}

.decision-actions button {
  display: grid;
  min-height: 70px;
  gap: 4px;
  place-items: center;
  padding: 10px;
  border-radius: 15px;
  cursor: pointer;
  font-size: 0.83rem;
  font-weight: 850;
  transition:
    transform 150ms ease,
    box-shadow 150ms ease,
    opacity 150ms ease;
}

.decision-actions button:not(:disabled):hover {
  transform: translateY(-2px);
}

.decision-actions button:disabled {
  cursor: wait;
  opacity: 0.58;
}

.decision-actions button span {
  font-size: 1.45rem;
  line-height: 1;
}

.reject-button {
  color: #a54b45;
  border: 1px solid #f0c4bf;
  background: #fff2ef;
}

.like-button {
  color: #ffffff;
  border: 1px solid #ee8b21;
  background: linear-gradient(135deg, #ffa43a, #f28b24);
  box-shadow: 0 11px 24px rgba(242, 139, 36, 0.22);
}

.saving-message {
  margin: 14px 0 0;
  color: #8b7765;
  font-size: 0.78rem;
  font-weight: 750;
  text-align: center;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 600px) {
  .match-notification {
    right: 16px;
    bottom: 16px;
  }

  .filters-overlay {
    align-items: end;
    padding: 6px 0 0;
  }

  .name-card,
  .finished-card {
    padding: 28px 20px;
  }

  dl,
  .decision-actions {
    grid-template-columns: 1fr;
  }

  .decision-actions button {
    min-height: 55px;
    grid-template-columns: auto auto;
    justify-content: center;
  }
}

@media (prefers-reduced-motion: reduce) {
  .match-toast-enter-active,
  .match-toast-leave-active {
    transition: none;
  }
}
</style>
