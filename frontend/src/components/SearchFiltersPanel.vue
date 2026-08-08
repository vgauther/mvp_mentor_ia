<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { authenticatedFetch, getErrorMessage } from '../api/client'
import type { FirstNameOrigin, NameSearch, SearchGender } from '../types/api'
import FeatherIcon from './FeatherIcon.vue'

const props = defineProps<{
  search: NameSearch
}>()

const emit = defineEmits<{
  close: []
  saved: [search: NameSearch]
}>()

const genderLabels: Record<SearchGender, string> = {
  female: 'Féminin',
  male: 'Masculin',
  mixed: 'Mixte',
}

const genderOptions: SearchGender[] = ['female', 'male', 'mixed']
const firstLetterOptions = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

const selectedGenders = ref<SearchGender[]>([])
const selectedOrigins = ref<string[]>([])
const minLength = ref('')
const maxLength = ref('')
const selectedFirstLetters = ref<string[]>([])
const originOptions = ref<FirstNameOrigin[]>([])
const isLoadingOrigins = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')

function resetFromSearch() {
  selectedGenders.value = [...props.search.genders]
  selectedOrigins.value = [...props.search.origins]
  minLength.value = props.search.min_length?.toString() ?? ''
  maxLength.value = props.search.max_length?.toString() ?? ''
  selectedFirstLetters.value = [...props.search.first_letters]
  errorMessage.value = ''
}

watch(() => props.search, resetFromSearch, { immediate: true })

function toggleGender(gender: SearchGender) {
  errorMessage.value = ''

  if (selectedGenders.value.includes(gender)) {
    selectedGenders.value = selectedGenders.value.filter((value) => value !== gender)
    return
  }

  selectedGenders.value = [...selectedGenders.value, gender]
}

function toggleOrigin(origin: string) {
  errorMessage.value = ''

  if (selectedOrigins.value.includes(origin)) {
    selectedOrigins.value = selectedOrigins.value.filter((value) => value !== origin)
    return
  }

  selectedOrigins.value = [...selectedOrigins.value, origin]
}

function toggleFirstLetter(firstLetter: string) {
  errorMessage.value = ''

  if (selectedFirstLetters.value.includes(firstLetter)) {
    selectedFirstLetters.value = selectedFirstLetters.value.filter((value) => value !== firstLetter)
    return
  }

  selectedFirstLetters.value = [...selectedFirstLetters.value, firstLetter]
}

function resetOptionalFilters() {
  selectedGenders.value = [...genderOptions]
  selectedOrigins.value = []
  minLength.value = ''
  maxLength.value = ''
  selectedFirstLetters.value = []
  errorMessage.value = ''
}

function parseOptionalLength(value: string) {
  return value === '' ? null : Number(value)
}

async function loadOrigins() {
  isLoadingOrigins.value = true
  errorMessage.value = ''

  try {
    const response = await authenticatedFetch('/api/first-name-origins/')

    if (!response.ok) {
      errorMessage.value = await getErrorMessage(response, 'Impossible de charger les origines.')
      return
    }

    originOptions.value = (await response.json()) as FirstNameOrigin[]
  } catch (error) {
    console.error('Échec du chargement des origines :', error)
    errorMessage.value = 'Impossible de contacter Django pour charger les origines.'
  } finally {
    isLoadingOrigins.value = false
  }
}

async function saveFilters() {
  const parsedMinLength = parseOptionalLength(minLength.value)
  const parsedMaxLength = parseOptionalLength(maxLength.value)

  errorMessage.value = ''

  if (selectedGenders.value.length === 0) {
    errorMessage.value = 'Sélectionne au moins un type de prénom.'
    return
  }

  if (
    (parsedMinLength !== null &&
      (!Number.isInteger(parsedMinLength) || parsedMinLength < 1 || parsedMinLength > 100)) ||
    (parsedMaxLength !== null &&
      (!Number.isInteger(parsedMaxLength) || parsedMaxLength < 1 || parsedMaxLength > 100))
  ) {
    errorMessage.value = 'La longueur doit être un nombre entier compris entre 1 et 100.'
    return
  }

  if (parsedMinLength !== null && parsedMaxLength !== null && parsedMinLength > parsedMaxLength) {
    errorMessage.value = 'La longueur minimale ne peut pas dépasser la longueur maximale.'
    return
  }

  isSaving.value = true

  try {
    const response = await authenticatedFetch(`/api/searches/${props.search.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({
        genders: selectedGenders.value,
        origins: selectedOrigins.value,
        min_length: parsedMinLength,
        max_length: parsedMaxLength,
        first_letters: selectedFirstLetters.value,
      }),
    })

    if (!response.ok) {
      errorMessage.value = await getErrorMessage(response, 'Impossible d’enregistrer les filtres.')
      return
    }

    emit('saved', (await response.json()) as NameSearch)
  } catch (error) {
    console.error('Échec de la modification des filtres :', error)
    errorMessage.value = 'Impossible de contacter Django pour enregistrer les filtres.'
  } finally {
    isSaving.value = false
  }
}

onMounted(() => {
  void loadOrigins()
})
</script>

<template>
  <section
    class="filters-panel"
    role="dialog"
    aria-modal="true"
    aria-labelledby="quick-filters-title"
    data-test="quick-filters-panel"
  >
    <header class="filters-heading">
      <div>
        <span>Parcours</span>
        <h3 id="quick-filters-title">Modifier les filtres</h3>
        <p>Les prochaines propositions s’adapteront dès l’enregistrement.</p>
      </div>

      <button
        type="button"
        class="close-button"
        aria-label="Fermer les filtres"
        :disabled="isSaving"
        data-test="close-quick-filters"
        @click="emit('close')"
      >
        <FeatherIcon name="x" :size="19" />
      </button>
    </header>

    <form @submit.prevent="saveFilters">
      <fieldset>
        <legend>Types de prénoms</legend>
        <div class="choice-grid gender-grid">
          <label v-for="gender in genderOptions" :key="gender">
            <input
              type="checkbox"
              :checked="selectedGenders.includes(gender)"
              :disabled="isSaving"
              :data-test="`quick-filter-gender-${gender}`"
              @change="toggleGender(gender)"
            />
            <span>{{ genderLabels[gender] }}</span>
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Origines</legend>
        <p class="field-help">Sans sélection, toutes les origines sont proposées.</p>

        <p v-if="isLoadingOrigins" class="loading-message" role="status">
          Chargement des origines…
        </p>

        <div v-else class="choice-grid origin-grid">
          <label v-for="origin in originOptions" :key="origin.id" :title="origin.description">
            <input
              type="checkbox"
              :checked="selectedOrigins.includes(origin.id)"
              :disabled="isSaving"
              :data-test="`quick-filter-origin-${origin.id}`"
              @change="toggleOrigin(origin.id)"
            />
            <span>{{ origin.label }}</span>
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Longueur</legend>
        <div class="length-grid">
          <label>
            Minimum
            <input
              v-model="minLength"
              type="number"
              min="1"
              max="100"
              inputmode="numeric"
              placeholder="Aucun"
              :disabled="isSaving"
              data-test="quick-filter-min-length"
            />
          </label>

          <label>
            Maximum
            <input
              v-model="maxLength"
              type="number"
              min="1"
              max="100"
              inputmode="numeric"
              placeholder="Aucun"
              :disabled="isSaving"
              data-test="quick-filter-max-length"
            />
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Première lettre</legend>
        <p class="field-help">Tu peux choisir plusieurs initiales.</p>

        <div class="letter-grid">
          <label v-for="firstLetter in firstLetterOptions" :key="firstLetter">
            <input
              type="checkbox"
              :checked="selectedFirstLetters.includes(firstLetter)"
              :disabled="isSaving"
              :data-test="`quick-filter-first-letter-${firstLetter}`"
              @change="toggleFirstLetter(firstLetter)"
            />
            <span>{{ firstLetter }}</span>
          </label>
        </div>
      </fieldset>

      <p v-if="errorMessage" class="filter-error" role="alert">{{ errorMessage }}</p>

      <div class="filter-actions">
        <button
          type="button"
          class="reset-button"
          :disabled="isSaving"
          data-test="reset-quick-filters"
          @click="resetOptionalFilters"
        >
          <FeatherIcon name="rotate-ccw" :size="15" />
          Tout réinitialiser
        </button>
        <button
          type="submit"
          class="save-button"
          :disabled="isSaving || isLoadingOrigins"
          data-test="save-quick-filters"
        >
          <FeatherIcon name="check" :size="16" />
          {{ isSaving ? 'Enregistrement…' : 'Appliquer les filtres' }}
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.filters-panel {
  width: min(720px, calc(100% - 24px));
  max-height: min(820px, calc(100vh - 32px));
  overflow-y: auto;
  padding: 26px;
  border: 1px solid rgba(126, 83, 35, 0.15);
  border-radius: 24px;
  background: #fffdf9;
  box-shadow: 0 28px 80px rgba(73, 45, 19, 0.24);
}

.filters-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f1e4d6;
}

.filters-heading > div > span {
  color: #eb8a20;
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.filters-heading h3 {
  margin: 5px 0 7px;
  color: #483321;
  font-size: 1.5rem;
}

.filters-heading p,
.field-help,
.loading-message {
  margin: 0;
  color: #897462;
  line-height: 1.5;
}

.close-button {
  display: grid;
  width: 39px;
  height: 39px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid #ead9c8;
  border-radius: 12px;
  color: #7d6552;
  background: #ffffff;
  cursor: pointer;
}

form {
  display: grid;
  gap: 22px;
  padding-top: 22px;
}

fieldset {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

legend {
  margin-bottom: 10px;
  color: #563c28;
  font-size: 0.85rem;
  font-weight: 900;
}

.field-help {
  margin: -4px 0 10px;
  font-size: 0.78rem;
}

.choice-grid,
.letter-grid {
  display: grid;
  gap: 8px;
}

.gender-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.origin-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.letter-grid {
  grid-template-columns: repeat(9, minmax(0, 1fr));
}

.choice-grid label,
.letter-grid label {
  cursor: pointer;
}

.choice-grid input,
.letter-grid input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.choice-grid span,
.letter-grid span {
  display: grid;
  min-height: 40px;
  place-items: center;
  padding: 7px 9px;
  border: 1px solid #ead9c8;
  border-radius: 11px;
  color: #745b46;
  background: #ffffff;
  font-size: 0.78rem;
  font-weight: 800;
  text-align: center;
  transition: 140ms ease;
}

.choice-grid input:checked + span,
.letter-grid input:checked + span {
  color: #8c5418;
  border-color: #f1aa55;
  background: #fff0d9;
  box-shadow: inset 0 0 0 1px rgba(244, 146, 36, 0.16);
}

.choice-grid input:focus-visible + span,
.letter-grid input:focus-visible + span {
  outline: 3px solid rgba(244, 146, 36, 0.2);
  outline-offset: 2px;
}

.length-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.length-grid label {
  display: grid;
  gap: 7px;
  color: #745b46;
  font-size: 0.78rem;
  font-weight: 800;
}

.length-grid input {
  min-width: 0;
  min-height: 44px;
  padding: 0 12px;
  border: 1px solid #e4d1be;
  border-radius: 11px;
  color: #4f3926;
  background: #ffffff;
  font: inherit;
}

.length-grid input:focus {
  border-color: #ef9a3a;
  outline: 3px solid rgba(239, 154, 58, 0.15);
}

.filter-error {
  margin: 0;
  padding: 11px 13px;
  border-radius: 11px;
  color: #a13e30;
  background: #fff0ed;
  font-size: 0.82rem;
  font-weight: 750;
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 4px;
}

.filter-actions button {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 16px;
  border-radius: 11px;
  cursor: pointer;
  font-weight: 850;
}

.filter-actions button:disabled,
.close-button:disabled {
  cursor: wait;
  opacity: 0.58;
}

.reset-button {
  border: 1px solid #e4d1be;
  color: #725b47;
  background: #ffffff;
}

.save-button {
  border: 1px solid #ef8d22;
  color: #ffffff;
  background: linear-gradient(135deg, #ffa43a, #f28b24);
  box-shadow: 0 10px 22px rgba(242, 139, 36, 0.2);
}

@media (max-width: 680px) {
  .filters-panel {
    width: 100%;
    max-height: calc(100vh - 12px);
    padding: 21px 16px;
    border-radius: 22px 22px 0 0;
  }

  .origin-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .letter-grid {
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }

  .filter-actions {
    display: grid;
    grid-template-columns: 1fr;
  }

  .save-button {
    grid-row: 1;
  }
}
</style>
