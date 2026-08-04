<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { authenticatedFetch, getErrorMessage } from '../api/client'
import type { FirstName, NameDecisionChoice } from '../types/api'

const props = defineProps<{
  searchId: number
  searchTitle: string
}>()

const emit = defineEmits<{
  back: []
}>()

const firstName = ref<FirstName | null>(null)
const isLoading = ref(true)
const isSubmitting = ref(false)
const isFinished = ref(false)
const errorMessage = ref('')
const handledCount = ref(0)
const lastAction = ref<NameDecisionChoice | null>(null)

const lastActionMessage = computed(() => {
  if (lastAction.value === 'liked') {
    return 'Prénom ajouté à tes favoris.'
  }

  if (lastAction.value === 'rejected') {
    return 'Prénom refusé.'
  }

  if (lastAction.value === 'skipped') {
    return 'Prénom passé.'
  }

  return ''
})

async function loadNextFirstName() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await authenticatedFetch(
      `/api/searches/${props.searchId}/next-first-name/`,
    )

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
    errorMessage.value =
      'Impossible de contacter Django pour charger un prénom.'
  } finally {
    isLoading.value = false
  }
}

async function choose(choice: NameDecisionChoice) {
  if (!firstName.value || isSubmitting.value) {
    return
  }

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    const response = await authenticatedFetch(
      `/api/searches/${props.searchId}/decisions/`,
      {
        method: 'POST',
        body: JSON.stringify({
          first_name_id: firstName.value.id,
          choice,
        }),
      },
    )

    if (!response.ok) {
      errorMessage.value = await getErrorMessage(
        response,
        'Impossible d’enregistrer ton choix.',
      )
      return
    }

    handledCount.value += 1
    lastAction.value = choice
    await loadNextFirstName()
  } catch (error) {
    console.error('Échec de l’enregistrement de la décision :', error)
    errorMessage.value =
      'Impossible de contacter Django pour enregistrer ton choix.'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  void loadNextFirstName()
})
</script>

<template>
  <section class="browser-shell">
    <header class="browser-header">
      <button type="button" class="back-button" @click="emit('back')">
        <span>←</span>
        Retour au détail
      </button>

      <div class="progress-badge">
        <span>{{ handledCount }}</span>
        prénom{{ handledCount > 1 ? 's' : '' }}
        parcouru{{ handledCount > 1 ? 's' : '' }}
      </div>
    </header>

    <div class="title-block">
      <span class="section-kicker">{{ searchTitle }}</span>
      <h2>Parcourir les prénoms</h2>
      <p>
        Découvre une proposition à la fois et indique simplement ce que tu en
        penses.
      </p>
    </div>

    <p
      v-if="lastActionMessage && !errorMessage"
      class="feedback success-feedback"
      role="status"
    >
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

    <div
      v-else-if="errorMessage && !firstName"
      class="state-card error-state"
    >
      <span class="state-symbol">!</span>

      <div>
        <strong>Le prénom n’a pas pu être chargé</strong>
        <p>Tu peux réessayer sans perdre les choix déjà enregistrés.</p>

        <button
          type="button"
          class="retry-button"
          @click="loadNextFirstName"
        >
          Réessayer
        </button>
      </div>
    </div>

    <div v-else-if="isFinished" class="finished-card">
      <span class="finished-icon">✓</span>
      <h3>Tu as parcouru tous les prénoms disponibles</h3>

      <p>
        Tes choix sont bien enregistrés. Tu pourras bientôt retrouver tes
        prénoms aimés et les matchs obtenus avec l’autre participant.
      </p>

      <button type="button" class="finish-button" @click="emit('back')">
        Revenir à la recherche
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
            <dd>{{ firstName.origin || 'Non renseignée' }}</dd>
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

        <button
          type="button"
          class="skip-button"
          :disabled="isSubmitting"
          @click="choose('skipped')"
        >
          <span>→</span>
          Passer
        </button>

        <button
          type="button"
          class="like-button"
          :disabled="isSubmitting"
          @click="choose('liked')"
        >
          <span>♥</span>
          J’aime
        </button>
      </div>

      <p v-if="isSubmitting" class="saving-message" role="status">
        Enregistrement de ton choix…
      </p>
    </article>
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
  gap: 16px;
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

.progress-badge {
  padding: 9px 12px;
  color: #7b5b3b;
  border-radius: 999px;
  background: #fff0d8;
  font-size: 0.78rem;
  font-weight: 800;
}

.progress-badge span {
  color: #d8750d;
  font-weight: 950;
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
    radial-gradient(
      circle at 95% 7%,
      rgba(163, 223, 241, 0.5),
      transparent 15rem
    ),
    radial-gradient(
      circle at 4% 97%,
      rgba(255, 192, 101, 0.28),
      transparent 14rem
    ),
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
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

.skip-button {
  color: #756555;
  border: 1px solid #dfd4c9;
  background: #f8f4ef;
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
  .browser-header {
    align-items: flex-start;
  }

  .progress-badge {
    text-align: center;
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
</style>