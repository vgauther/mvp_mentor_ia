<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { authenticatedFetch, getErrorMessage } from '../api/client'
import type { NameSearch, SearchGender, SearchStatus } from '../types/api'

const props = defineProps<{
  userId: number
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

const activeCount = computed(
  () => searches.value.filter((search) => search.status === 'active').length,
)
const completedCount = computed(
  () => searches.value.filter((search) => search.status === 'completed').length,
)
const archivedCount = computed(
  () => searches.value.filter((search) => search.status === 'archived').length,
)

const filteredSearches = computed(() => {
  if (selectedStatus.value === 'all') {
    return searches.value
  }

  return searches.value.filter((search) => search.status === selectedStatus.value)
})

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

function openCreateForm() {
  createError.value = ''
  createSuccess.value = ''
  isCreateOpen.value = true
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

async function createSearch() {
  const title = newTitle.value.trim()

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

  isCreating.value = true

  try {
    const response = await authenticatedFetch('/api/searches/', {
      method: 'POST',
      body: JSON.stringify({
        title,
        genders: newGenders.value,
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
    <section class="summary-grid" aria-label="Résumé des recherches">
      <article class="summary-card active-summary">
        <span class="summary-icon">♥</span>
        <div>
          <strong>{{ activeCount }}</strong>
          <span
            >Recherche{{ activeCount > 1 ? 's' : '' }} active{{ activeCount > 1 ? 's' : '' }}</span
          >
        </div>
      </article>

      <article class="summary-card completed-summary">
        <span class="summary-icon">✓</span>
        <div>
          <strong>{{ completedCount }}</strong>
          <span>Terminée{{ completedCount > 1 ? 's' : '' }}</span>
        </div>
      </article>

      <article class="summary-card archived-summary">
        <span class="summary-icon">□</span>
        <div>
          <strong>{{ archivedCount }}</strong>
          <span>Archivée{{ archivedCount > 1 ? 's' : '' }}</span>
        </div>
      </article>
    </section>

    <section class="searches-panel">
      <div class="panel-heading">
        <div>
          <span class="section-kicker">Mes projets</span>
          <h2>Mes recherches de prénoms</h2>
          <p>Retrouve ici tes recherches personnelles et celles partagées avec toi.</p>
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

      <div class="status-filters" aria-label="Filtrer les recherches">
        <button
          v-for="option in statusOptions"
          :key="option.value"
          type="button"
          :class="{ selected: selectedStatus === option.value }"
          @click="selectedStatus = option.value"
        >
          {{ option.label }}
        </button>
      </div>

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

          <div class="gender-list" aria-label="Types de prénoms recherchés">
            <span v-for="gender in search.genders" :key="gender">{{ genderLabel(gender) }}</span>
          </div>

          <div class="participant-row">
            <div class="avatar-stack" aria-hidden="true">
              <span
                v-for="participant in acceptedParticipants(search).slice(0, 2)"
                :key="participant.id"
              >
                {{
                  (participant.profile.display_name || participant.profile.username)
                    .charAt(0)
                    .toUpperCase()
                }}
              </span>
            </div>

            <p>
              {{
                acceptedParticipants(search).length === 1
                  ? 'Recherche individuelle'
                  : `${acceptedParticipants(search).length} participants`
              }}
            </p>
          </div>

          <footer>
            <span>Créée le {{ formatShortDate(search.created_at) }}</span>
            <button type="button" disabled>
              {{ search.status === 'active' ? 'Ouvrir bientôt' : 'Consulter bientôt' }}
              <span>→</span>
            </button>
          </footer>
        </article>
      </div>
    </section>

    <div v-if="isCreateOpen" class="modal-backdrop" @click.self="closeCreateForm">
      <section class="create-modal" role="dialog" aria-modal="true" aria-labelledby="create-title">
        <button type="button" class="close-button" aria-label="Fermer" @click="closeCreateForm">
          ×
        </button>

        <span class="modal-icon">♡</span>
        <span class="section-kicker">Nouveau projet</span>
        <h2 id="create-title">Créer une recherche</h2>
        <p>Choisis un nom pour la retrouver facilement, puis indique les prénoms à proposer.</p>

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
  gap: 24px;
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
  padding: 28px;
  border: 1px solid rgba(105, 75, 39, 0.1);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 22px 50px rgba(130, 83, 32, 0.08);
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
  margin: 25px 0 20px;
  padding-bottom: 18px;
  overflow-x: auto;
  border-bottom: 1px solid #f0e5da;
}

.status-filters button {
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

.status-filters button.selected {
  color: #814b0f;
  background: #fee4b8;
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 17px;
}

.search-card {
  min-width: 0;
  padding: 21px;
  border: 1px solid #eee0d2;
  border-radius: 19px;
  background: #fffdf9;
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    border-color 160ms ease;
}

.search-card:hover {
  transform: translateY(-2px);
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
  margin: 19px 0 13px;
  color: #3e2d20;
  font-size: 19px;
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
  padding-top: 16px;
  border-top: 1px solid #f1e6dc;
}

.search-card footer > span {
  color: #9b8878;
  font-size: 11px;
}

.search-card footer button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 10px;
  color: #9a570d;
  border: 0;
  border-radius: 9px;
  background: #fff0d8;
  cursor: pointer;
  font-size: 12px;
  font-weight: 850;
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
  width: min(540px, 100%);
  padding: 32px;
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
  margin-top: 24px;
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

  .panel-heading {
    display: grid;
  }

  .create-button {
    width: 100%;
  }

  .searches-panel {
    padding: 20px;
  }
}

@media (max-width: 480px) {
  .gender-options {
    grid-template-columns: 1fr;
  }

  .create-modal {
    padding: 27px 20px 20px;
  }

  .modal-actions {
    display: grid;
  }
}
</style>
