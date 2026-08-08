<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { authenticatedFetch, getErrorMessage } from '../api/client'
import type { FirstNameOrigin, NameSearch, SearchGender, SearchStatus } from '../types/api'

const props = defineProps<{
  userId: number
}>()

const emit = defineEmits<{
  openSearch: [search: NameSearch]
  openSearchDetails: [search: NameSearch]
}>()

const searches = ref<NameSearch[]>([])
const isLoading = ref(true)
const loadError = ref('')

const isCreateOpen = ref(false)
const isCreating = ref(false)
const createError = ref('')
const createSuccess = ref('')
const newTitle = ref('')
const newGenders = ref<SearchGender[]>(['female', 'male', 'mixed'])
const originOptions = ref<FirstNameOrigin[]>([])
const originLoadError = ref('')
const newOrigins = ref<string[]>([])
const newMinLength = ref('')
const newMaxLength = ref('')
const newFirstLetters = ref<string[]>([])

const selectedStatus = ref<SearchStatus | 'all'>('all')

const genderOptions: { value: SearchGender; label: string; symbol: string }[] = [
  { value: 'female', label: 'Féminin', symbol: 'F' },
  { value: 'male', label: 'Masculin', symbol: 'M' },
  { value: 'mixed', label: 'Mixte', symbol: 'FM' },
]

const statusOptions: { value: SearchStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Toutes' },
  { value: 'active', label: 'Actives' },
  { value: 'completed', label: 'Terminées' },
  { value: 'archived', label: 'Archivées' },
]

const firstLetterOptions = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

const filteredSearches = computed(() => {
  if (selectedStatus.value === 'all') {
    return searches.value
  }

  return searches.value.filter((search) => search.status === selectedStatus.value)
})

function statusCount(status: SearchStatus | 'all') {
  if (status === 'all') {
    return searches.value.length
  }

  return searches.value.filter((search) => search.status === status).length
}

async function loadSearches() {
  isLoading.value = true
  loadError.value = ''

  try {
    const response = await authenticatedFetch('/api/searches/')

    if (!response.ok) {
      loadError.value = await getErrorMessage(
        response,
        'Impossible de charger vos recherches de prénoms.',
      )
      return
    }

    searches.value = (await response.json()) as NameSearch[]
  } catch (error) {
    console.error('Échec du chargement des recherches :', error)
    loadError.value = 'Impossible de contacter Django pour charger vos recherches.'
  } finally {
    isLoading.value = false
  }
}

async function loadOriginOptions() {
  originLoadError.value = ''

  try {
    const response = await authenticatedFetch('/api/first-name-origins/')

    if (!response.ok) {
      originLoadError.value = await getErrorMessage(response, 'Impossible de charger les origines.')
      return
    }

    originOptions.value = (await response.json()) as FirstNameOrigin[]
  } catch (error) {
    console.error('Échec du chargement des origines :', error)
    originLoadError.value = 'Impossible de contacter Django pour charger les origines.'
  }
}

function openCreateForm() {
  createError.value = ''
  createSuccess.value = ''
  isCreateOpen.value = true

  if (originOptions.value.length === 0) {
    void loadOriginOptions()
  }
}

function closeCreateForm() {
  if (isCreating.value) {
    return
  }

  isCreateOpen.value = false
  createError.value = ''
}

function toggleGender(gender: SearchGender) {
  if (newGenders.value.includes(gender)) {
    newGenders.value = newGenders.value.filter((value) => value !== gender)
  } else {
    newGenders.value = [...newGenders.value, gender]
  }
}

function toggleOrigin(origin: string) {
  if (newOrigins.value.includes(origin)) {
    newOrigins.value = newOrigins.value.filter((value) => value !== origin)
  } else {
    newOrigins.value = [...newOrigins.value, origin]
  }
}

function toggleFirstLetter(firstLetter: string) {
  if (newFirstLetters.value.includes(firstLetter)) {
    newFirstLetters.value = newFirstLetters.value.filter((value) => value !== firstLetter)
  } else {
    newFirstLetters.value = [...newFirstLetters.value, firstLetter]
  }
}

function parseOptionalLength(value: string) {
  return value === '' ? null : Number(value)
}

async function createSearch() {
  const title = newTitle.value.trim()
  const minLength = parseOptionalLength(newMinLength.value)
  const maxLength = parseOptionalLength(newMaxLength.value)

  createError.value = ''
  createSuccess.value = ''

  if (!title) {
    createError.value = 'Donne un nom à cette recherche.'
    return
  }

  if (newGenders.value.length === 0) {
    createError.value = 'Choisis au moins un type de prénom.'
    return
  }

  if (
    (minLength !== null && (!Number.isInteger(minLength) || minLength < 1 || minLength > 100)) ||
    (maxLength !== null && (!Number.isInteger(maxLength) || maxLength < 1 || maxLength > 100))
  ) {
    createError.value = 'La longueur doit être un nombre entier compris entre 1 et 100.'
    return
  }

  if (minLength !== null && maxLength !== null && minLength > maxLength) {
    createError.value = 'La longueur minimale ne peut pas dépasser la longueur maximale.'
    return
  }

  isCreating.value = true

  try {
    const response = await authenticatedFetch('/api/searches/', {
      method: 'POST',
      body: JSON.stringify({
        title,
        genders: newGenders.value,
        origins: newOrigins.value,
        min_length: minLength,
        max_length: maxLength,
        first_letters: newFirstLetters.value,
      }),
    })

    if (!response.ok) {
      createError.value = await getErrorMessage(response, 'Impossible de créer cette recherche.')
      return
    }

    const createdSearch = (await response.json()) as NameSearch

    searches.value = [createdSearch, ...searches.value]
    selectedStatus.value = 'all'
    newTitle.value = ''
    newGenders.value = ['female', 'male', 'mixed']
    newOrigins.value = []
    newMinLength.value = ''
    newMaxLength.value = ''
    newFirstLetters.value = []
    isCreateOpen.value = false
    createSuccess.value = `La recherche « ${createdSearch.title} » a bien été créée.`
  } catch (error) {
    console.error('Échec de la création de la recherche :', error)
    createError.value = 'Impossible de contacter Django pour créer cette recherche.'
  } finally {
    isCreating.value = false
  }
}

function genderLabel(gender: SearchGender) {
  return genderOptions.find((option) => option.value === gender)?.label || gender
}

function acceptedParticipants(search: NameSearch) {
  return search.participants.filter((participant) => participant.invitation_status === 'accepted')
}

function currentRole(search: NameSearch) {
  return search.participants.find((participant) => participant.profile.id === props.userId)?.role
}

function formatShortDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Date inconnue'
  }

  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

onMounted(() => {
  void loadSearches()
})
</script>

<template>
  <div class="dashboard-content">
    <section class="searches-panel">
      <div class="searches-toolbar">
        <div class="status-filters" aria-label="Filtrer les recherches">
          <button
            v-for="option in statusOptions"
            :key="option.value"
            type="button"
            :class="{ selected: selectedStatus === option.value }"
            @click="selectedStatus = option.value"
          >
            {{ option.label }}
            <span>{{ statusCount(option.value) }}</span>
          </button>
        </div>

        <button
          type="button"
          class="create-button"
          data-test="create-search-button"
          @click="openCreateForm"
        >
          <span>+</span>
          Nouvelle recherche
        </button>
      </div>

      <p v-if="createSuccess" class="feedback success-feedback" role="status">
        {{ createSuccess }}
      </p>

      <div v-if="isLoading" class="panel-state" aria-live="polite">
        <span class="loader"></span>
        <div>
          <strong>Chargement de tes recherches…</strong>
          <p>Django prépare ton espace.</p>
        </div>
      </div>

      <div v-else-if="loadError" class="panel-state error-state">
        <span class="state-symbol">!</span>
        <div>
          <strong>Impossible de charger les recherches</strong>
          <p role="alert">{{ loadError }}</p>
          <button type="button" class="retry-button" @click="loadSearches">Réessayer</button>
        </div>
      </div>

      <div v-else-if="filteredSearches.length === 0" class="empty-state">
        <span class="empty-heart">♡</span>

        <h3>
          {{
            searches.length === 0
              ? 'Ta première recherche commence ici'
              : 'Aucune recherche dans cette catégorie'
          }}
        </h3>

        <p v-if="searches.length === 0">
          Crée un espace pour découvrir des prénoms seul ou à deux et retrouver vos choix communs.
        </p>

        <p v-else>Choisis un autre filtre pour afficher le reste de tes recherches.</p>

        <button
          v-if="searches.length === 0"
          type="button"
          class="empty-button"
          @click="openCreateForm"
        >
          Créer ma première recherche
        </button>
      </div>

      <div v-else class="search-grid">
        <article
          v-for="search in filteredSearches"
          :key="search.id"
          class="search-card"
          data-test="search-card"
        >
          <div class="search-card-main">
            <div class="card-topline">
              <span :class="['status-badge', `status-${search.status}`]">
                <span></span>
                {{ search.status_label }}
              </span>

              <span class="role-badge">
                {{ currentRole(search) === 'owner' ? 'Ma recherche' : 'Partagée avec moi' }}
              </span>
            </div>

            <h3>{{ search.title }}</h3>

            <div class="search-meta">
              <span>{{ search.genders.map(genderLabel).join(' · ') }}</span>
              <span>
                {{
                  acceptedParticipants(search).length === 1
                    ? 'Individuelle'
                    : `${acceptedParticipants(search).length} participants`
                }}
              </span>
              <span>Créée le {{ formatShortDate(search.created_at) }}</span>
            </div>
          </div>

          <footer>
            <div class="search-actions">
              <button
                type="button"
                class="details-button"
                data-test="open-search-details-button"
                @click="emit('openSearchDetails', search)"
              >
                {{ search.status === 'active' ? 'Gérer' : 'Consulter' }}
              </button>

              <button
                v-if="search.status === 'active'"
                type="button"
                data-test="open-search-button"
                @click="emit('openSearch', search)"
              >
                Continuer
                <span>→</span>
              </button>
            </div>
          </footer>
        </article>
      </div>
    </section>

    <div v-if="isCreateOpen" class="modal-backdrop" @click.self="closeCreateForm">
      <section class="create-modal" role="dialog" aria-modal="true" aria-labelledby="create-title">
        <button type="button" class="close-button" aria-label="Fermer" @click="closeCreateForm">
          ×
        </button>

        <h2 id="create-title">Nouvelle recherche</h2>
        <p>Donne-lui un nom et choisis les types de prénoms à parcourir.</p>

        <form data-test="create-search-form" @submit.prevent="createSearch">
          <label for="search-title">Nom de la recherche</label>

          <input
            id="search-title"
            v-model="newTitle"
            data-test="search-title-input"
            type="text"
            maxlength="150"
            placeholder="Par exemple : Notre futur prénom"
            autofocus
          />

          <fieldset>
            <legend>Types de prénoms</legend>

            <div class="gender-options">
              <button
                v-for="option in genderOptions"
                :key="option.value"
                type="button"
                :class="{ selected: newGenders.includes(option.value) }"
                @click="toggleGender(option.value)"
              >
                <span>{{ option.symbol }}</span>
                {{ option.label }}
              </button>
            </div>
          </fieldset>

          <details class="advanced-filters">
            <summary>
              <span>Filtres facultatifs</span>
              <small>Origine, longueur et première lettre</small>
            </summary>

            <div class="advanced-filters-content">
              <fieldset>
                <legend>Origines</legend>
                <p class="filter-help">Sans sélection, toutes les origines sont proposées.</p>

                <p v-if="originLoadError" class="filter-load-error" role="alert">
                  {{ originLoadError }}
                </p>

                <div v-else class="origin-options">
                  <button
                    v-for="origin in originOptions"
                    :key="origin.id"
                    type="button"
                    :class="{ selected: newOrigins.includes(origin.id) }"
                    :title="origin.description"
                    :data-test="`create-search-origin-${origin.id}`"
                    @click="toggleOrigin(origin.id)"
                  >
                    {{ origin.label }}
                  </button>
                </div>
              </fieldset>

              <fieldset>
                <legend>Longueur du prénom</legend>
                <div class="length-options">
                  <label>
                    Minimum
                    <input
                      v-model="newMinLength"
                      data-test="create-search-min-length"
                      type="number"
                      min="1"
                      max="100"
                      inputmode="numeric"
                      placeholder="Sans minimum"
                    />
                  </label>

                  <label>
                    Maximum
                    <input
                      v-model="newMaxLength"
                      data-test="create-search-max-length"
                      type="number"
                      min="1"
                      max="100"
                      inputmode="numeric"
                      placeholder="Sans maximum"
                    />
                  </label>
                </div>
              </fieldset>

              <fieldset>
                <legend>Première lettre</legend>
                <div class="first-letter-options">
                  <button
                    v-for="firstLetter in firstLetterOptions"
                    :key="firstLetter"
                    type="button"
                    :class="{ selected: newFirstLetters.includes(firstLetter) }"
                    :data-test="`create-search-first-letter-${firstLetter}`"
                    @click="toggleFirstLetter(firstLetter)"
                  >
                    {{ firstLetter }}
                  </button>
                </div>
              </fieldset>
            </div>
          </details>

          <p v-if="createError" class="feedback error-feedback" role="alert">
            {{ createError }}
          </p>

          <div class="modal-actions">
            <button
              type="button"
              class="cancel-button"
              :disabled="isCreating"
              @click="closeCreateForm"
            >
              Annuler
            </button>

            <button type="submit" class="confirm-button" :disabled="isCreating">
              {{ isCreating ? 'Création…' : 'Créer la recherche' }}
            </button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard-content {
  display: grid;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  border: 1px solid rgba(112, 77, 39, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 14px 34px rgba(124, 80, 32, 0.06);
}

.summary-icon {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 15px;
  font-size: 20px;
  font-weight: 900;
}

.active-summary .summary-icon {
  color: #c76700;
  background: #fee4b8;
}

.completed-summary .summary-icon {
  color: #28778c;
  background: #d9f3fb;
}

.archived-summary .summary-icon {
  color: #7f7063;
  background: #eee8e1;
}

.summary-card strong,
.summary-card span {
  display: block;
}

.summary-card strong {
  color: #412f20;
  font-size: 27px;
  line-height: 1;
}

.summary-card div > span {
  margin-top: 5px;
  color: #887567;
  font-size: 13px;
  font-weight: 700;
}

.searches-panel {
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.searches-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}

.section-kicker {
  display: block;
  margin-bottom: 7px;
  color: #bd6c17;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.panel-heading h2,
.create-modal h2 {
  margin: 0;
  color: #3f2e20;
  font-size: 24px;
}

.panel-heading p,
.create-modal > p {
  margin: 7px 0 0;
  color: #806e5e;
  font-size: 14px;
  line-height: 1.55;
}

.create-button,
.empty-button,
.confirm-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 12px 17px;
  color: #fff;
  border: 0;
  border-radius: 13px;
  background: #f49224;
  box-shadow: 0 10px 22px rgba(244, 146, 36, 0.23);
  cursor: pointer;
  font-weight: 850;
}

.create-button span {
  font-size: 20px;
  line-height: 0;
}

.status-filters {
  display: flex;
  gap: 7px;
  margin: 0;
  padding: 0;
  overflow-x: auto;
  border: 0;
}

.status-filters button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  color: #876f5d;
  border: 0;
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
}

.status-filters button span {
  display: grid;
  min-width: 20px;
  height: 20px;
  place-items: center;
  padding: 0 5px;
  border-radius: 999px;
  color: #8f7864;
  background: #f0ebe5;
  font-size: 10px;
}

.status-filters button.selected {
  color: #814b0f;
  background: #fee4b8;
}

.status-filters button.selected span {
  color: #ffffff;
  background: #e98a22;
}

.panel-state,
.empty-state {
  display: flex;
  min-height: 250px;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.panel-state {
  gap: 16px;
}

.panel-state > div {
  text-align: left;
}

.panel-state strong {
  color: #473426;
}

.panel-state p {
  margin: 5px 0 0;
  color: #8a7869;
}

.loader {
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  border: 4px solid #fee8c7;
  border-top-color: #f49224;
  border-radius: 50%;
  animation: spin 750ms linear infinite;
}

.state-symbol {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  color: #a94141;
  border-radius: 50%;
  background: #fff0ec;
  font-weight: 900;
}

.retry-button {
  margin-top: 12px;
  padding: 9px 13px;
  color: #8b4d0d;
  border: 1px solid #efc28d;
  border-radius: 10px;
  background: #fff8ef;
  cursor: pointer;
  font-weight: 800;
}

.empty-state {
  flex-direction: column;
  padding: 30px;
}

.empty-heart {
  display: grid;
  width: 64px;
  height: 64px;
  place-items: center;
  color: #ef8b20;
  border-radius: 20px;
  background: #fff0d8;
  font-size: 35px;
}

.empty-state h3 {
  margin: 17px 0 0;
  color: #473426;
  font-size: 20px;
}

.empty-state p {
  max-width: 530px;
  margin: 9px 0 20px;
  color: #887668;
  line-height: 1.55;
}

.search-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.search-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 20px;
  min-width: 0;
  padding: 17px 18px;
  border: 1px solid #eee0d2;
  border-radius: 16px;
  background: #ffffff;
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    border-color 160ms ease;
}

.search-card:hover {
  transform: translateY(-1px);
  border-color: #efc796;
  box-shadow: 0 15px 30px rgba(128, 80, 27, 0.1);
}

.card-topline,
.search-card footer,
.participant-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-topline {
  justify-content: flex-start;
}

.status-badge,
.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 9px;
  border-radius: 9px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.status-badge > span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.status-active {
  color: #9b570d;
  background: #fff0d8;
}

.status-completed {
  color: #28778c;
  background: #e0f5fb;
}

.status-archived {
  color: #75675b;
  background: #eee9e4;
}

.role-badge {
  color: #7a6b5f;
  background: #f4f0eb;
}

.search-card h3 {
  margin: 10px 0 7px;
  color: #3e2d20;
  font-size: 18px;
}

.search-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  color: #89786a;
  font-size: 11px;
  font-weight: 700;
}

.search-meta span + span {
  position: relative;
}

.search-meta span + span::before {
  position: absolute;
  left: -8px;
  content: "·";
}

.gender-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.gender-list span {
  padding: 6px 9px;
  color: #68513d;
  border: 1px solid #edd9c2;
  border-radius: 8px;
  background: #fff7eb;
  font-size: 11px;
  font-weight: 750;
}

.participant-row {
  justify-content: flex-start;
  margin: 20px 0;
}

.avatar-stack {
  display: flex;
  padding-left: 7px;
}

.avatar-stack span {
  display: grid;
  width: 30px;
  height: 30px;
  margin-left: -7px;
  place-items: center;
  color: #5a3e1c;
  border: 2px solid #fffdf9;
  border-radius: 50%;
  background: #fee4b8;
  font-size: 11px;
  font-weight: 900;
}

.avatar-stack span:nth-child(2) {
  color: #245c6b;
  background: #a3dff1;
}

.participant-row p {
  margin: 0;
  color: #817064;
  font-size: 12px;
  font-weight: 700;
}

.search-card footer {
  padding: 0;
  border: 0;
}

.search-card footer > span {
  color: #9b8878;
  font-size: 11px;
}

.search-card footer button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 39px;
  padding: 8px 13px;
  color: #9a570d;
  border: 0;
  border-radius: 9px;
  background: #fff0d8;
  cursor: pointer;
  font-size: 12px;
  font-weight: 850;
}

.search-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
}

.search-card footer .details-button {
  color: #705d4d;
  border: 1px solid #e4d5c5;
  background: #fff;
}

.search-card footer button:disabled {
  color: #7a6e64;
  background: #eeeae6;
  cursor: default;
}

.feedback {
  margin: 18px 0 0;
  padding: 11px 13px;
  border-radius: 11px;
  font-size: 13px;
  font-weight: 750;
}

.success-feedback {
  color: #2f7352;
  background: #e9f8ef;
}

.error-feedback {
  color: #9d3e3e;
  background: #fff0ec;
}

.modal-backdrop {
  position: fixed;
  z-index: 20;
  inset: 0;
  display: grid;
  padding: 22px;
  place-items: center;
  overflow-y: auto;
  background: rgba(57, 39, 23, 0.44);
  backdrop-filter: blur(5px);
}

.create-modal {
  position: relative;
  width: min(720px, 100%);
  max-height: calc(100vh - 44px);
  padding: 29px;
  overflow-y: auto;
  border-radius: 25px;
  background: #fffdf9;
  box-shadow: 0 30px 80px rgba(61, 38, 17, 0.25);
}

.close-button {
  position: absolute;
  top: 17px;
  right: 17px;
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  color: #7b6756;
  border: 0;
  border-radius: 10px;
  background: #f3ede6;
  cursor: pointer;
  font-size: 22px;
}

.modal-icon {
  display: grid;
  width: 51px;
  height: 51px;
  margin-bottom: 18px;
  place-items: center;
  color: #f08b1d;
  border-radius: 16px;
  background: #fee4b8;
  font-size: 29px;
}

.create-modal form {
  margin-top: 20px;
}

.create-modal label,
.create-modal legend {
  display: block;
  margin-bottom: 8px;
  color: #806343;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.create-modal input {
  width: 100%;
  padding: 13px 14px;
  color: #3f2e20;
  border: 1px solid #e5d3bf;
  border-radius: 12px;
  outline: none;
  background: #fff;
}

.create-modal input:focus {
  border-color: #ffa43a;
  box-shadow: 0 0 0 4px rgba(255, 164, 58, 0.16);
}

fieldset {
  margin: 20px 0 0;
  padding: 0;
  border: 0;
}

.advanced-filters {
  margin-top: 20px;
  border: 1px solid #eadccd;
  border-radius: 14px;
  background: #fffaf4;
}

.advanced-filters summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 15px;
  color: #684d36;
  cursor: pointer;
  font-weight: 850;
  list-style-position: inside;
}

.advanced-filters summary small {
  color: #968272;
  font-size: 11px;
  font-weight: 650;
}

.advanced-filters-content {
  padding: 0 15px 16px;
  border-top: 1px solid #eadccd;
}

.gender-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 9px;
}

.gender-options button {
  display: grid;
  gap: 6px;
  padding: 12px 8px;
  color: #806d5e;
  border: 1px solid #eadccd;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.gender-options button span {
  font-size: 10px;
  font-weight: 950;
}

.gender-options button.selected {
  color: #874b08;
  border-color: #f0bb79;
  background: #fff0d8;
  box-shadow: inset 0 0 0 1px #f0bb79;
}

.filter-help {
  margin: -2px 0 10px;
  color: #8b7766;
  font-size: 12px;
  line-height: 1.45;
}

.filter-load-error {
  margin: 0;
  color: #9d3e3e;
  font-size: 12px;
  font-weight: 750;
}

.origin-options {
  display: flex;
  max-height: 180px;
  flex-wrap: wrap;
  gap: 7px;
  padding: 10px;
  overflow-y: auto;
  border: 1px solid #eadccd;
  border-radius: 12px;
  background: #fff;
}

.origin-options button,
.first-letter-options button {
  color: #705d4d;
  border: 1px solid #e7d7c6;
  background: #fffaf4;
  cursor: pointer;
  font-weight: 800;
}

.origin-options button {
  padding: 7px 9px;
  border-radius: 9px;
  font-size: 11px;
}

.origin-options button.selected,
.first-letter-options button.selected {
  color: #874b08;
  border-color: #f0bb79;
  background: #fff0d8;
  box-shadow: inset 0 0 0 1px #f0bb79;
}

.length-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.length-options label {
  margin: 0;
}

.length-options input {
  margin-top: 7px;
}

.first-letter-options {
  display: grid;
  grid-template-columns: repeat(13, minmax(0, 1fr));
  gap: 6px;
}

.first-letter-options button {
  aspect-ratio: 1;
  padding: 0;
  border-radius: 8px;
  font-size: 12px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.cancel-button {
  padding: 11px 16px;
  color: #765f4d;
  border: 1px solid #e4d5c5;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  font-weight: 800;
}

button:disabled {
  opacity: 0.62;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .summary-grid,
  .search-grid {
    grid-template-columns: 1fr;
  }

  .panel-heading,
  .searches-toolbar {
    display: grid;
  }

  .create-button {
    width: 100%;
  }

  .search-card {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .search-card footer,
  .search-actions {
    width: 100%;
  }

  .search-actions button {
    flex: 1;
    justify-content: center;
  }

  .first-letter-options {
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }
}

@media (max-width: 480px) {
  .gender-options {
    grid-template-columns: 1fr;
  }

  .length-options {
    grid-template-columns: 1fr;
  }

  .create-modal {
    padding: 27px 20px 20px;
  }

  .advanced-filters summary {
    align-items: flex-start;
    flex-direction: column;
    gap: 3px;
  }

  .modal-actions {
    display: grid;
  }
}
</style>
