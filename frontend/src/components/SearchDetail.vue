<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { authenticatedFetch, getErrorMessage } from '../api/client'
import type {
  FirstName,
  NameSearch,
  NameSearchParticipant,
  ProfileLookup,
  SearchInvitation,
  SearchGender,
  SearchStatus,
} from '../types/api'
import NameBrowser from './NameBrowser.vue'

const props = defineProps<{
  search: NameSearch
  userId: number
}>()

const emit = defineEmits<{
  back: []
  searchUpdated: [search: NameSearch]
}>()

const currentSearch = ref<NameSearch>(props.search)
const isUpdatingStatus = ref(false)
const statusError = ref('')
const statusSuccess = ref('')
const isBrowsingFirstNames = ref(false)
const isViewingLikedFirstNames = ref(false)
const likedFirstNames = ref<FirstName[]>([])
const isLoadingLikedFirstNames = ref(false)
const likedFirstNamesError = ref('')
const isViewingMatches = ref(false)
const matches = ref<FirstName[]>([])
const isLoadingMatches = ref(false)
const matchesError = ref('')
const invitationEmail = ref('')
const foundProfile = ref<ProfileLookup | null>(null)
const isSearchingProfile = ref(false)
const isSendingInvitation = ref(false)
const invitationError = ref('')
const invitationSuccess = ref('')
const isEditingSearch = ref(false)
const editTitle = ref('')
const editGenders = ref<SearchGender[]>([])
const isSavingSearch = ref(false)
const editError = ref('')
const editSuccess = ref('')

const genderLabels: Record<SearchGender, string> = {
  female: 'Féminin',
  male: 'Masculin',
  mixed: 'Mixte',
}

const genderOptions: SearchGender[] = ['female', 'male', 'mixed']

const currentParticipant = computed(() =>
  currentSearch.value.participants.find(
    (participant) =>
      participant.profile.id === props.userId && participant.invitation_status === 'accepted',
  ),
)

const isOwner = computed(() => currentParticipant.value?.role === 'owner')

const acceptedParticipants = computed(() =>
  currentSearch.value.participants.filter(
    (participant) => participant.invitation_status === 'accepted',
  ),
)

const pendingParticipants = computed(() =>
  currentSearch.value.participants.filter(
    (participant) => participant.invitation_status === 'pending',
  ),
)

const canInviteParticipant = computed(
  () =>
    isOwner.value &&
    currentSearch.value.status === 'active' &&
    acceptedParticipants.value.length === 1 &&
    pendingParticipants.value.length === 0,
)

const statusDescription = computed(() => {
  if (currentSearch.value.status === 'active') {
    return 'La recherche est ouverte : les participants peuvent encore parcourir et choisir des prénoms.'
  }

  if (currentSearch.value.status === 'completed') {
    return 'La recherche est terminée. Les choix restent consultables et le propriétaire peut la réactiver ou l’archiver.'
  }

  return 'La recherche est archivée. Elle reste consultable et peut être restaurée comme recherche terminée.'
})

watch(
  () => props.search,
  (search) => {
    const searchChanged = currentSearch.value.id !== search.id
    currentSearch.value = search

    if (searchChanged) {
      isEditingSearch.value = false
      editError.value = ''
      editSuccess.value = ''
      isViewingLikedFirstNames.value = false
      likedFirstNames.value = []
      likedFirstNamesError.value = ''
      isViewingMatches.value = false
      matches.value = []
      matchesError.value = ''
      resetInvitationForm()
    }

    if (search.status !== 'active') {
      isBrowsingFirstNames.value = false
    }
  },
)

function openNameBrowser() {
  if (currentSearch.value.status !== 'active') {
    return
  }

  isViewingLikedFirstNames.value = false
  isViewingMatches.value = false
  isBrowsingFirstNames.value = true
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function closeNameBrowser() {
  isBrowsingFirstNames.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function loadLikedFirstNames() {
  isLoadingLikedFirstNames.value = true
  likedFirstNamesError.value = ''

  try {
    const response = await authenticatedFetch(
      `/api/searches/${currentSearch.value.id}/liked-first-names/`,
    )

    if (!response.ok) {
      likedFirstNamesError.value = await getErrorMessage(
        response,
        'Impossible de charger tes prénoms aimés.',
      )
      return
    }

    likedFirstNames.value = (await response.json()) as FirstName[]
  } catch (error) {
    console.error('Échec du chargement des prénoms aimés :', error)
    likedFirstNamesError.value = 'Impossible de contacter Django pour charger tes prénoms aimés.'
  } finally {
    isLoadingLikedFirstNames.value = false
  }
}

async function openLikedFirstNames() {
  isBrowsingFirstNames.value = false
  isViewingMatches.value = false
  isViewingLikedFirstNames.value = true
  window.scrollTo({ top: 0, behavior: 'smooth' })
  await loadLikedFirstNames()
}

function closeLikedFirstNames() {
  isViewingLikedFirstNames.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function loadMatches() {
  isLoadingMatches.value = true
  matchesError.value = ''

  try {
    const response = await authenticatedFetch(`/api/searches/${currentSearch.value.id}/matches/`)

    if (!response.ok) {
      matchesError.value = await getErrorMessage(
        response,
        'Impossible de charger les matchs de cette recherche.',
      )
      return
    }

    matches.value = (await response.json()) as FirstName[]
  } catch (error) {
    console.error('Échec du chargement des matchs :', error)
    matchesError.value = 'Impossible de contacter Django pour charger les matchs.'
  } finally {
    isLoadingMatches.value = false
  }
}

async function openMatches() {
  isBrowsingFirstNames.value = false
  isViewingLikedFirstNames.value = false
  isViewingMatches.value = true
  window.scrollTo({ top: 0, behavior: 'smooth' })
  await loadMatches()
}

function closeMatches() {
  isViewingMatches.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function participantName(participant: NameSearchParticipant) {
  return participant.profile.display_name || participant.profile.username
}

function initials(participant: NameSearchParticipant) {
  const name = participantName(participant).trim()

  if (!name) {
    return '?'
  }

  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('')
}

function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Date inconnue'
  }

  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

function resetInvitationForm() {
  invitationEmail.value = ''
  foundProfile.value = null
  invitationError.value = ''
  invitationSuccess.value = ''
}

function openSearchEditor() {
  if (!isOwner.value) {
    return
  }

  editTitle.value = currentSearch.value.title
  editGenders.value = [...currentSearch.value.genders]
  editError.value = ''
  editSuccess.value = ''
  isEditingSearch.value = true
}

function closeSearchEditor() {
  if (isSavingSearch.value) {
    return
  }

  isEditingSearch.value = false
  editError.value = ''
}

function toggleEditGender(gender: SearchGender) {
  editError.value = ''

  if (editGenders.value.includes(gender)) {
    editGenders.value = editGenders.value.filter((selectedGender) => selectedGender !== gender)
    return
  }

  editGenders.value = [...editGenders.value, gender]
}

async function saveSearchDetails() {
  const title = editTitle.value.trim()

  editError.value = ''
  editSuccess.value = ''

  if (!title) {
    editError.value = 'Donne un titre à cette recherche.'
    return
  }

  if (editGenders.value.length === 0) {
    editError.value = 'Sélectionne au moins un type de prénom.'
    return
  }

  isSavingSearch.value = true

  try {
    const response = await authenticatedFetch(`/api/searches/${currentSearch.value.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({
        title,
        genders: editGenders.value,
      }),
    })

    if (!response.ok) {
      editError.value = await getErrorMessage(
        response,
        'Impossible de modifier les informations de cette recherche.',
      )
      return
    }

    const updatedSearch = (await response.json()) as NameSearch

    currentSearch.value = updatedSearch
    isEditingSearch.value = false
    editSuccess.value = 'Les informations de la recherche ont bien été enregistrées.'
    emit('searchUpdated', updatedSearch)
  } catch (error) {
    console.error('Échec de la modification de la recherche :', error)
    editError.value = 'Impossible de contacter Django pour modifier cette recherche.'
  } finally {
    isSavingSearch.value = false
  }
}

function updateInvitationEmail() {
  foundProfile.value = null
  invitationError.value = ''
  invitationSuccess.value = ''
}

async function searchProfileToInvite() {
  const email = invitationEmail.value.trim()

  foundProfile.value = null
  invitationError.value = ''
  invitationSuccess.value = ''

  if (!email) {
    invitationError.value = 'Saisis l’adresse e-mail de la personne à inviter.'
    return
  }

  isSearchingProfile.value = true

  try {
    const query = new URLSearchParams({ email })
    const response = await authenticatedFetch(`/api/profiles/lookup/?${query.toString()}`)

    if (!response.ok) {
      invitationError.value = await getErrorMessage(
        response,
        'Aucun utilisateur ne correspond à cette adresse e-mail.',
      )
      return
    }

    const profile = (await response.json()) as ProfileLookup

    if (profile.id === props.userId) {
      invitationError.value = 'Tu ne peux pas t’inviter dans ta propre recherche.'
      return
    }

    foundProfile.value = profile
  } catch (error) {
    console.error('Échec de la recherche du profil à inviter :', error)
    invitationError.value = 'Impossible de contacter Django pour rechercher cet utilisateur.'
  } finally {
    isSearchingProfile.value = false
  }
}

async function sendInvitation() {
  if (!foundProfile.value || !canInviteParticipant.value) {
    return
  }

  isSendingInvitation.value = true
  invitationError.value = ''
  invitationSuccess.value = ''

  try {
    const response = await authenticatedFetch(
      `/api/searches/${currentSearch.value.id}/invitations/`,
      {
        method: 'POST',
        body: JSON.stringify({ profile_id: foundProfile.value.id }),
      },
    )

    if (!response.ok) {
      invitationError.value = await getErrorMessage(
        response,
        'Impossible d’envoyer cette invitation.',
      )
      return
    }

    const invitation = (await response.json()) as SearchInvitation
    const participant: NameSearchParticipant = {
      id: invitation.id,
      profile: invitation.profile,
      role: invitation.role,
      role_label: invitation.role_label,
      invitation_status: invitation.invitation_status,
      invitation_status_label: invitation.invitation_status_label,
      created_at: invitation.created_at,
      updated_at: invitation.updated_at,
    }
    const existingParticipantIndex = currentSearch.value.participants.findIndex(
      (currentParticipant) => currentParticipant.id === participant.id,
    )
    const participants = [...currentSearch.value.participants]

    if (existingParticipantIndex >= 0) {
      participants.splice(existingParticipantIndex, 1, participant)
    } else {
      participants.push(participant)
    }

    const updatedSearch: NameSearch = {
      ...currentSearch.value,
      participants,
    }

    currentSearch.value = updatedSearch
    invitationEmail.value = ''
    foundProfile.value = null
    invitationSuccess.value = 'L’invitation a bien été envoyée.'
    emit('searchUpdated', updatedSearch)
  } catch (error) {
    console.error('Échec de l’envoi de l’invitation :', error)
    invitationError.value = 'Impossible de contacter Django pour envoyer cette invitation.'
  } finally {
    isSendingInvitation.value = false
  }
}

async function updateStatus(newStatus: SearchStatus) {
  isUpdatingStatus.value = true
  statusError.value = ''
  statusSuccess.value = ''

  try {
    const response = await authenticatedFetch(`/api/searches/${currentSearch.value.id}/status/`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    })

    if (!response.ok) {
      statusError.value = await getErrorMessage(
        response,
        'Impossible de modifier le statut de cette recherche.',
      )
      return
    }

    const updatedSearch = (await response.json()) as NameSearch

    currentSearch.value = updatedSearch
    statusSuccess.value = `La recherche est maintenant ${updatedSearch.status_label.toLowerCase()}.`
    emit('searchUpdated', updatedSearch)
  } catch (error) {
    console.error('Échec de la modification du statut :', error)
    statusError.value = 'Impossible de contacter Django pour modifier cette recherche.'
  } finally {
    isUpdatingStatus.value = false
  }
}
</script>

<template>
  <div class="detail-content">
    <NameBrowser
      v-if="isBrowsingFirstNames"
      :search-id="currentSearch.id"
      :search-title="currentSearch.title"
      @back="closeNameBrowser"
    />

    <section v-else-if="isViewingLikedFirstNames" class="matches-view">
      <button
        type="button"
        class="back-button"
        data-test="back-to-search-detail"
        @click="closeLikedFirstNames"
      >
        <span>←</span>
        Retour à la recherche
      </button>

      <section class="matches-hero">
        <div>
          <p class="eyebrow">Ma sélection</p>
          <h2>Mes prénoms aimés dans « {{ currentSearch.title }} »</h2>
          <p>
            Retrouve ici tous les prénoms que tu as aimés pendant ton parcours dans cette recherche.
          </p>
        </div>

        <div class="match-total" aria-live="polite">
          <strong>{{ isLoadingLikedFirstNames ? '…' : likedFirstNames.length }}</strong>
          <span>
            {{ likedFirstNames.length > 1 ? 'prénoms aimés' : 'prénom aimé' }}
          </span>
        </div>
      </section>

      <div class="matches-toolbar">
        <div>
          <span class="section-kicker">Sélection personnelle</span>
          <h3>Les prénoms que tu as conservés</h3>
        </div>
        <button
          type="button"
          class="refresh-button"
          :disabled="isLoadingLikedFirstNames"
          data-test="refresh-liked-first-names"
          @click="loadLikedFirstNames"
        >
          {{ isLoadingLikedFirstNames ? 'Actualisation…' : 'Actualiser' }}
        </button>
      </div>

      <div v-if="isLoadingLikedFirstNames" class="matches-state" role="status">
        <span class="loading-heart">♥</span>
        <div>
          <strong>Chargement de tes prénoms aimés…</strong>
          <p>Nous récupérons les prénoms que tu as conservés pour cette recherche.</p>
        </div>
      </div>

      <div v-else-if="likedFirstNamesError" class="matches-state error-state" role="alert">
        <span>!</span>
        <div>
          <strong>Les prénoms aimés n’ont pas pu être chargés</strong>
          <p>{{ likedFirstNamesError }}</p>
          <button type="button" @click="loadLikedFirstNames">Réessayer</button>
        </div>
      </div>

      <div v-else-if="likedFirstNames.length === 0" class="matches-state empty-state">
        <span>♡</span>
        <div>
          <strong>Tu n’as encore aimé aucun prénom</strong>
          <p v-if="currentSearch.status === 'active'">
            Parcours les propositions et utilise le bouton « J’aime » : tes choix apparaîtront
            ensuite ici.
          </p>
          <p v-else>Aucun prénom aimé n’a été enregistré dans cette recherche.</p>
        </div>
      </div>

      <div v-else class="matches-grid" data-test="liked-first-names-list">
        <article
          v-for="(firstName, index) in likedFirstNames"
          :key="firstName.id"
          class="match-card"
        >
          <div class="match-card-heading">
            <span class="match-number">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="match-heart">♥</span>
          </div>

          <h3>{{ firstName.name }}</h3>

          <div class="match-tags">
            <span>{{ genderLabels[firstName.gender] }}</span>
            <span>{{ firstName.origin || 'Origine non renseignée' }}</span>
          </div>

          <div class="meaning-block">
            <span>Signification</span>
            <p>
              {{ firstName.meaning || 'Aucune signification renseignée pour ce prénom.' }}
            </p>
          </div>
        </article>
      </div>
    </section>

    <section v-else-if="isViewingMatches" class="matches-view">
      <button
        type="button"
        class="back-button"
        data-test="back-to-search-detail"
        @click="closeMatches"
      >
        <span>←</span>
        Retour à la recherche
      </button>

      <section class="matches-hero">
        <div>
          <p class="eyebrow">Résultats communs</p>
          <h2>Les matchs de « {{ currentSearch.title }} »</h2>
          <p>
            Retrouve ici les prénoms aimés par les deux participants. La liste évolue au fur et à
            mesure de vos décisions.
          </p>
        </div>

        <div class="match-total" aria-live="polite">
          <strong>{{ isLoadingMatches ? '…' : matches.length }}</strong>
          <span>{{ matches.length > 1 ? 'matchs trouvés' : 'match trouvé' }}</span>
        </div>
      </section>

      <div class="matches-toolbar">
        <div>
          <span class="section-kicker">Sélection commune</span>
          <h3>Prénoms appréciés ensemble</h3>
        </div>
        <button
          type="button"
          class="refresh-button"
          :disabled="isLoadingMatches"
          data-test="refresh-search-matches"
          @click="loadMatches"
        >
          {{ isLoadingMatches ? 'Actualisation…' : 'Actualiser' }}
        </button>
      </div>

      <div v-if="isLoadingMatches" class="matches-state" role="status">
        <span class="loading-heart">♥</span>
        <div>
          <strong>Recherche des matchs…</strong>
          <p>Nous comparons les prénoms aimés par les deux participants.</p>
        </div>
      </div>

      <div v-else-if="matchesError" class="matches-state error-state" role="alert">
        <span>!</span>
        <div>
          <strong>Les matchs n’ont pas pu être chargés</strong>
          <p>{{ matchesError }}</p>
          <button type="button" @click="loadMatches">Réessayer</button>
        </div>
      </div>

      <div v-else-if="matches.length === 0" class="matches-state empty-state">
        <span>♡</span>
        <div v-if="acceptedParticipants.length < 2">
          <strong>Le second participant n’a pas encore rejoint la recherche</strong>
          <p>
            Les matchs apparaîtront ici dès que son invitation sera acceptée et que vous aurez
            commencé à choisir des prénoms.
          </p>
        </div>
        <div v-else>
          <strong>Aucun match pour le moment</strong>
          <p>
            Continuez à parcourir les prénoms. Dès que vous aimerez tous les deux le même prénom, il
            apparaîtra ici.
          </p>
        </div>
      </div>

      <div v-else class="matches-grid" data-test="search-matches-list">
        <article v-for="(firstName, index) in matches" :key="firstName.id" class="match-card">
          <div class="match-card-heading">
            <span class="match-number">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="match-heart">♥</span>
          </div>

          <h3>{{ firstName.name }}</h3>

          <div class="match-tags">
            <span>{{ genderLabels[firstName.gender] }}</span>
            <span>{{ firstName.origin || 'Origine non renseignée' }}</span>
          </div>

          <div class="meaning-block">
            <span>Signification</span>
            <p>
              {{ firstName.meaning || 'Aucune signification renseignée pour ce prénom.' }}
            </p>
          </div>
        </article>
      </div>
    </section>

    <template v-else>
      <button type="button" class="back-button" data-test="back-to-searches" @click="emit('back')">
        <span>←</span>
        Retour aux recherches
      </button>

      <section class="hero-card">
        <div class="hero-copy">
          <div class="badge-row">
            <span :class="['status-badge', `status-${currentSearch.status}`]">
              <span></span>
              {{ currentSearch.status_label }}
            </span>
            <span class="role-badge">{{ isOwner ? 'Ma recherche' : 'Partagée avec moi' }}</span>
          </div>

          <p class="eyebrow">Recherche de prénoms</p>
          <h2>{{ currentSearch.title }}</h2>
          <p>{{ statusDescription }}</p>

          <div class="gender-list" aria-label="Types de prénoms recherchés">
            <span v-for="gender in currentSearch.genders" :key="gender">
              {{ genderLabels[gender] }}
            </span>
          </div>
        </div>

        <div class="hero-meta">
          <span>Créée le</span>
          <strong>{{ formatDate(currentSearch.created_at) }}</strong>
          <span>Dernière modification</span>
          <strong>{{ formatDate(currentSearch.updated_at) }}</strong>
          <button
            v-if="isOwner"
            type="button"
            class="edit-search-button"
            data-test="edit-search-button"
            @click="openSearchEditor"
          >
            Modifier la recherche
          </button>
        </div>
      </section>

      <section v-if="isEditingSearch" class="panel edit-search-panel">
        <div class="panel-heading">
          <div>
            <span class="section-kicker">Informations</span>
            <h3>Modifier la recherche</h3>
          </div>
        </div>

        <form data-test="edit-search-form" @submit.prevent="saveSearchDetails">
          <label for="edit-search-title">Titre de la recherche</label>
          <input
            id="edit-search-title"
            v-model="editTitle"
            data-test="edit-search-title"
            type="text"
            maxlength="150"
            autocomplete="off"
            :disabled="isSavingSearch"
          />

          <fieldset>
            <legend>Types de prénoms recherchés</legend>
            <div class="edit-gender-grid">
              <label v-for="gender in genderOptions" :key="gender">
                <input
                  type="checkbox"
                  :value="gender"
                  :checked="editGenders.includes(gender)"
                  :disabled="isSavingSearch"
                  :data-test="`edit-search-gender-${gender}`"
                  @change="toggleEditGender(gender)"
                />
                <span>{{ genderLabels[gender] }}</span>
              </label>
            </div>
          </fieldset>

          <p v-if="editError" class="edit-search-error" role="alert">
            {{ editError }}
          </p>

          <div class="edit-search-actions">
            <button
              type="button"
              class="secondary-action"
              :disabled="isSavingSearch"
              data-test="cancel-edit-search"
              @click="closeSearchEditor"
            >
              Annuler
            </button>
            <button
              type="submit"
              class="primary-action"
              :disabled="isSavingSearch"
              data-test="save-search-details"
            >
              {{ isSavingSearch ? 'Enregistrement…' : 'Enregistrer les modifications' }}
            </button>
          </div>
        </form>
      </section>

      <p v-if="editSuccess" class="feedback success-feedback" role="status">
        {{ editSuccess }}
      </p>

      <p v-if="statusSuccess" class="feedback success-feedback" role="status">
        {{ statusSuccess }}
      </p>
      <p v-if="statusError" class="feedback error-feedback" role="alert">
        {{ statusError }}
      </p>

      <div class="detail-grid">
        <section class="panel participant-panel">
          <div class="panel-heading">
            <div>
              <span class="section-kicker">Équipe</span>
              <h3>Participants</h3>
            </div>
            <span class="count-badge">{{ acceptedParticipants.length }}/2</span>
          </div>

          <div class="participant-list">
            <article v-for="participant in acceptedParticipants" :key="participant.id">
              <span class="avatar">{{ initials(participant) }}</span>
              <div>
                <strong>{{ participantName(participant) }}</strong>
                <span>@{{ participant.profile.username }}</span>
              </div>
              <span class="participant-role">{{ participant.role_label }}</span>
            </article>

            <article
              v-for="participant in pendingParticipants"
              :key="participant.id"
              class="pending"
            >
              <span class="avatar">{{ initials(participant) }}</span>
              <div>
                <strong>{{ participantName(participant) }}</strong>
                <span>Invitation en attente</span>
              </div>
              <span class="participant-role">En attente</span>
            </article>

            <div
              v-if="acceptedParticipants.length === 1 && pendingParticipants.length === 0"
              class="empty-slot"
            >
              <span>+</span>
              <div>
                <strong>Aucun second participant</strong>
                <p v-if="isOwner && currentSearch.status === 'active'">
                  Recherche un utilisateur ci-dessous pour l’inviter.
                </p>
                <p v-else-if="currentSearch.status !== 'active'">
                  Réactive la recherche avant d’inviter une personne.
                </p>
                <p v-else>Seul le propriétaire peut envoyer une invitation.</p>
              </div>
            </div>
          </div>

          <div v-if="canInviteParticipant || invitationSuccess" class="invitation-area">
            <div class="invitation-heading">
              <span>Inviter un proche</span>
              <p>Utilise l’adresse e-mail exacte de son compte.</p>
            </div>

            <form
              v-if="canInviteParticipant"
              class="invitation-form"
              data-test="search-invitation-form"
              @submit.prevent="searchProfileToInvite"
            >
              <label for="invitation-email">Adresse e-mail</label>
              <div>
                <input
                  id="invitation-email"
                  v-model="invitationEmail"
                  data-test="search-invitation-email"
                  type="email"
                  placeholder="utilisateur@exemple.fr"
                  autocomplete="off"
                  :disabled="isSearchingProfile || isSendingInvitation"
                  @input="updateInvitationEmail"
                />
                <button
                  type="submit"
                  class="lookup-button"
                  :disabled="isSearchingProfile || isSendingInvitation"
                >
                  {{ isSearchingProfile ? 'Recherche…' : 'Rechercher' }}
                </button>
              </div>
            </form>

            <p v-if="invitationError" class="invitation-message error-message" role="alert">
              {{ invitationError }}
            </p>
            <p v-if="invitationSuccess" class="invitation-message success-message" role="status">
              {{ invitationSuccess }}
            </p>

            <article
              v-if="foundProfile && canInviteParticipant"
              class="invitation-result"
              data-test="search-invitation-profile"
            >
              <span class="avatar">
                {{ (foundProfile.display_name || foundProfile.username).charAt(0).toUpperCase() }}
              </span>
              <div>
                <small>Utilisateur trouvé</small>
                <strong>{{ foundProfile.display_name || foundProfile.username }}</strong>
                <p>{{ foundProfile.email }} · @{{ foundProfile.username }}</p>
              </div>
              <button
                type="button"
                class="send-invitation-button"
                data-test="send-search-invitation"
                :disabled="isSendingInvitation"
                @click="sendInvitation"
              >
                {{ isSendingInvitation ? 'Envoi…' : 'Envoyer l’invitation' }}
              </button>
            </article>
          </div>
        </section>

        <section class="panel management-panel">
          <div class="panel-heading">
            <div>
              <span class="section-kicker">Cycle de vie</span>
              <h3>Gestion de la recherche</h3>
            </div>
          </div>

          <template v-if="isOwner">
            <p>Tu es propriétaire de cette recherche. Choisis son état selon son avancement.</p>

            <div v-if="currentSearch.status === 'active'" class="action-stack">
              <button
                type="button"
                class="primary-action"
                data-test="complete-search"
                :disabled="isUpdatingStatus"
                @click="updateStatus('completed')"
              >
                {{ isUpdatingStatus ? 'Modification…' : 'Terminer la recherche' }}
              </button>
              <small
                >Les nouvelles décisions seront bloquées, mais les résultats resteront
                visibles.</small
              >
            </div>

            <div v-else-if="currentSearch.status === 'completed'" class="action-stack">
              <button
                type="button"
                class="primary-action"
                data-test="reopen-search"
                :disabled="isUpdatingStatus"
                @click="updateStatus('active')"
              >
                Réactiver la recherche
              </button>
              <button
                type="button"
                class="secondary-action"
                data-test="archive-search"
                :disabled="isUpdatingStatus"
                @click="updateStatus('archived')"
              >
                Archiver la recherche
              </button>
            </div>

            <div v-else class="action-stack">
              <button
                type="button"
                class="primary-action"
                data-test="restore-search"
                :disabled="isUpdatingStatus"
                @click="updateStatus('completed')"
              >
                Restaurer la recherche
              </button>
              <small>La recherche repassera d’abord dans l’état « Terminée ».</small>
            </div>
          </template>

          <div v-else class="member-note">
            <span>i</span>
            <p>Seul le propriétaire peut terminer, réactiver ou archiver cette recherche.</p>
          </div>
        </section>
      </div>

      <section class="features-section">
        <div class="section-heading">
          <span class="section-kicker">Fonctionnalités</span>
          <h3>Que veux-tu faire ?</h3>
        </div>

        <div class="feature-grid">
          <article :class="{ unavailable: currentSearch.status !== 'active' }">
            <span class="feature-icon orange">♡</span>
            <div>
              <h4>Parcourir les prénoms</h4>
              <p>Aime ou refuse les propositions correspondant à cette recherche.</p>
            </div>
            <button
              type="button"
              :disabled="currentSearch.status !== 'active'"
              data-test="browse-first-names"
              @click="openNameBrowser"
            >
              {{ currentSearch.status === 'active' ? 'Commencer →' : 'Recherche inactive' }}
            </button>
          </article>

          <article>
            <span class="feature-icon blue">✓</span>
            <div>
              <h4>Prénoms aimés</h4>
              <p>Retrouve les prénoms que tu as conservés pendant ton parcours.</p>
            </div>
            <button type="button" data-test="view-liked-first-names" @click="openLikedFirstNames">
              Voir mes prénoms →
            </button>
          </article>

          <article>
            <span class="feature-icon yellow">♥</span>
            <div>
              <h4>Résultats et matchs</h4>
              <p>Découvre les prénoms appréciés par tous les participants.</p>
            </div>
            <button type="button" data-test="view-search-matches" @click="openMatches">
              Voir les matchs →
            </button>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.detail-content {
  display: grid;
  gap: 20px;
}

.matches-view {
  display: grid;
  gap: 20px;
}

.back-button {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: 0;
  color: #7d6552;
  background: transparent;
  cursor: pointer;
  font-weight: 800;
}

.back-button span {
  font-size: 1.15rem;
}

.hero-card,
.panel,
.features-section,
.matches-hero,
.matches-state,
.match-card {
  border: 1px solid rgba(126, 83, 35, 0.1);
  border-radius: 25px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 45px rgba(119, 82, 38, 0.07);
}

.matches-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 30px;
  padding: 31px;
  background:
    radial-gradient(circle at 94% 12%, rgba(255, 218, 123, 0.45), transparent 14rem),
    linear-gradient(135deg, rgba(255, 255, 255, 0.97), rgba(255, 249, 239, 0.97));
}

.matches-hero h2 {
  margin: 4px 0 12px;
  color: #4a3421;
  font-size: clamp(1.75rem, 4vw, 2.55rem);
  line-height: 1.1;
}

.matches-hero > div:first-child > p:last-child {
  max-width: 690px;
  margin: 0;
  color: #7d6552;
  line-height: 1.65;
}

.match-total {
  display: grid;
  min-width: 155px;
  place-items: center;
  padding: 23px 20px;
  border: 1px solid rgba(185, 126, 33, 0.13);
  border-radius: 20px;
  color: #87591c;
  background: rgba(255, 255, 255, 0.75);
}

.match-total strong {
  font-size: 2.4rem;
  line-height: 1;
}

.match-total span {
  margin-top: 7px;
  font-size: 0.76rem;
  font-weight: 850;
}

.matches-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.matches-toolbar h3 {
  margin: 4px 0 0;
  color: #4a3421;
  font-size: 1.25rem;
}

.refresh-button,
.matches-state button {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid #e1cdb9;
  border-radius: 11px;
  color: #6f5742;
  background: #fffaf3;
  cursor: pointer;
  font-weight: 850;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.6;
}

.matches-state {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 27px;
}

.matches-state > span {
  display: grid;
  width: 54px;
  height: 54px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 17px;
  color: #9b6724;
  background: #fff0c9;
  font-size: 1.5rem;
  font-weight: 900;
}

.matches-state strong {
  color: #4e3825;
  font-size: 1.05rem;
}

.matches-state p {
  margin: 5px 0 0;
  color: #8a7461;
  line-height: 1.55;
}

.matches-state button {
  margin-top: 13px;
}

.loading-heart {
  animation: heart-pulse 1.1s ease-in-out infinite;
}

.error-state > span {
  color: #a13e30;
  background: #fff0ed;
}

.matches-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.match-card {
  display: grid;
  gap: 16px;
  padding: 23px;
  background:
    radial-gradient(circle at 100% 0, rgba(255, 229, 166, 0.32), transparent 10rem),
    rgba(255, 255, 255, 0.92);
}

.match-card-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.match-number {
  color: #a18c78;
  font-size: 0.75rem;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.match-heart {
  display: grid;
  width: 37px;
  height: 37px;
  place-items: center;
  border-radius: 12px;
  color: #a65d13;
  background: #fee4b8;
}

.match-card h3 {
  margin: 0;
  color: #4a3421;
  font-size: 1.65rem;
}

.match-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.match-tags span {
  padding: 6px 10px;
  border-radius: 999px;
  color: #76512e;
  background: #fff0d8;
  font-size: 0.75rem;
  font-weight: 850;
}

.meaning-block {
  padding-top: 15px;
  border-top: 1px solid #f0e5d8;
}

.meaning-block span {
  color: #a18c78;
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.meaning-block p {
  margin: 6px 0 0;
  color: #725e4c;
  line-height: 1.55;
}

@keyframes heart-pulse {
  0%,
  100% {
    transform: scale(1);
  }

  50% {
    transform: scale(1.12);
  }
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 30px;
  overflow: hidden;
  padding: 31px;
  background:
    radial-gradient(circle at 95% 5%, rgba(163, 223, 241, 0.45), transparent 15rem),
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(255, 249, 239, 0.96));
}

.hero-copy {
  max-width: 710px;
}

.badge-row,
.gender-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-badge,
.role-badge,
.gender-list span,
.count-badge,
.participant-role {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 850;
}

.status-badge,
.role-badge {
  gap: 7px;
  padding: 6px 10px;
}

.status-badge > span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.status-active {
  color: #99631f;
  background: #fff0d2;
}

.status-completed {
  color: #22728b;
  background: #dff5fb;
}

.status-archived {
  color: #6c6259;
  background: #eeeae5;
}

.role-badge {
  color: #87511c;
  background: #fff7e8;
}

.eyebrow,
.section-kicker {
  color: #eb8a20;
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.eyebrow {
  margin: 24px 0 4px;
}

.hero-copy h2 {
  margin: 0;
  color: #4a3421;
  font-size: clamp(1.8rem, 4vw, 2.7rem);
  line-height: 1.08;
}

.hero-copy > p:not(.eyebrow) {
  max-width: 660px;
  margin: 13px 0 20px;
  color: #7d6552;
  line-height: 1.65;
}

.gender-list span {
  padding: 7px 11px;
  color: #76512e;
  background: #fff0d8;
}

.hero-meta {
  display: grid;
  min-width: 210px;
  align-content: center;
  gap: 4px;
  padding: 21px;
  border: 1px solid rgba(63, 125, 144, 0.12);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.65);
}

.hero-meta span {
  margin-top: 9px;
  color: #8b7765;
  font-size: 0.75rem;
  font-weight: 700;
}

.hero-meta strong {
  color: #4d3a29;
  font-size: 0.92rem;
}

.edit-search-button {
  min-height: 40px;
  margin-top: 15px;
  padding: 0 14px;
  border: 1px solid #d9c2aa;
  border-radius: 11px;
  color: #6f5742;
  background: #fffaf3;
  cursor: pointer;
  font-weight: 850;
}

.edit-search-panel form {
  display: grid;
  gap: 16px;
  margin-top: 20px;
}

.edit-search-panel form > label,
.edit-search-panel legend {
  color: #5d4937;
  font-size: 0.84rem;
  font-weight: 850;
}

.edit-search-panel form > input {
  width: 100%;
  min-height: 46px;
  box-sizing: border-box;
  padding: 0 14px;
  border: 1px solid #dfcdbb;
  border-radius: 12px;
  color: #4d3a29;
  background: #fffdf9;
  font: inherit;
}

.edit-search-panel form > input:focus {
  border-color: #efa04d;
  outline: 3px solid rgba(239, 160, 77, 0.16);
}

.edit-search-panel fieldset {
  padding: 0;
  border: 0;
}

.edit-search-panel legend {
  margin-bottom: 10px;
}

.edit-gender-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.edit-gender-grid label {
  cursor: pointer;
}

.edit-gender-grid input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.edit-gender-grid span {
  display: grid;
  min-height: 43px;
  place-items: center;
  border: 1px solid #e5d6c7;
  border-radius: 12px;
  color: #765f4a;
  background: #fffaf4;
  font-size: 0.86rem;
  font-weight: 800;
}

.edit-gender-grid input:checked + span {
  border-color: #eda14f;
  color: #85511e;
  background: #fff0d8;
}

.edit-gender-grid input:focus-visible + span {
  outline: 3px solid rgba(239, 160, 77, 0.22);
}

.edit-search-error {
  margin: 0;
  color: #a13e30;
  font-weight: 750;
}

.edit-search-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.edit-search-actions button {
  min-height: 44px;
  padding: 0 17px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 850;
}

.edit-search-actions button:disabled {
  cursor: wait;
  opacity: 0.62;
}

.feedback {
  margin: 0;
  padding: 13px 16px;
  border-radius: 14px;
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

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(310px, 0.8fr);
  gap: 20px;
}

.panel,
.features-section {
  padding: 25px;
}

.panel-heading,
.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-heading h3,
.section-heading h3 {
  margin: 3px 0 0;
  color: #4a3421;
  font-size: 1.22rem;
}

.count-badge {
  padding: 7px 11px;
  color: #24758d;
  background: #e4f6fb;
}

.participant-list {
  display: grid;
  gap: 10px;
  margin-top: 20px;
}

.participant-list article,
.empty-slot {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid #f0e5d8;
  border-radius: 16px;
  background: #fffcf7;
}

.invitation-area {
  display: grid;
  gap: 14px;
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid #f0e5d8;
}

.invitation-heading > span,
.invitation-form label,
.invitation-result small {
  color: #9a7042;
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.invitation-heading p {
  margin: 5px 0 0;
  color: #846f5c;
  font-size: 0.84rem;
}

.invitation-form {
  display: grid;
  gap: 7px;
}

.invitation-form > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 9px;
}

.invitation-form input {
  min-width: 0;
  padding: 12px 13px;
  color: #4a3421;
  border: 1px solid #e5d3bf;
  border-radius: 11px;
  outline: none;
  background: #fff;
}

.invitation-form input:focus {
  border-color: #f1a34a;
  box-shadow: 0 0 0 3px rgba(241, 163, 74, 0.13);
}

.lookup-button,
.send-invitation-button {
  min-height: 42px;
  border: 0;
  border-radius: 11px;
  cursor: pointer;
  font-weight: 850;
}

.lookup-button {
  padding: 0 15px;
  color: #75502c;
  background: #fff0d8;
}

.lookup-button:disabled,
.send-invitation-button:disabled {
  cursor: wait;
  opacity: 0.62;
}

.invitation-message {
  margin: 0;
  padding: 11px 13px;
  border-radius: 11px;
  font-size: 0.84rem;
  font-weight: 750;
}

.invitation-message.error-message {
  color: #a13e30;
  background: #fff0ed;
}

.invitation-message.success-message {
  color: #287144;
  background: #e7f7ec;
}

.invitation-result {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid #f0ddc4;
  border-radius: 15px;
  background: #fffaf2;
}

.invitation-result strong {
  display: block;
  margin-top: 2px;
  color: #4e3825;
}

.invitation-result p {
  overflow: hidden;
  margin: 3px 0 0;
  color: #8a7461;
  font-size: 0.78rem;
  text-overflow: ellipsis;
}

.send-invitation-button {
  grid-column: 1 / -1;
  color: #fff;
  background: linear-gradient(135deg, #ffa43a, #f28b24);
}

.participant-list article.pending {
  border-style: dashed;
  opacity: 0.78;
}

.avatar,
.empty-slot > span {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 13px;
  color: #76501f;
  background: #fee4b8;
  font-weight: 900;
}

.participant-list strong,
.participant-list span {
  display: block;
}

.participant-list article div > span,
.empty-slot p {
  margin: 3px 0 0;
  color: #917c69;
  font-size: 0.78rem;
}

.participant-role {
  padding: 6px 9px;
  color: #76512e;
  background: #fff0d8;
}

.empty-slot {
  grid-template-columns: auto minmax(0, 1fr);
  border-style: dashed;
  background: transparent;
}

.management-panel > p {
  margin: 19px 0;
  color: #7c6856;
  line-height: 1.55;
}

.action-stack {
  display: grid;
  gap: 10px;
}

.action-stack button {
  min-height: 45px;
  border-radius: 13px;
  cursor: pointer;
  font-weight: 850;
}

.action-stack button:disabled {
  cursor: wait;
  opacity: 0.62;
}

.primary-action {
  border: 0;
  color: #fff;
  background: linear-gradient(135deg, #ffa43a, #f28b24);
  box-shadow: 0 10px 22px rgba(242, 139, 36, 0.2);
}

.secondary-action {
  border: 1px solid #e1cdb9;
  color: #6f5742;
  background: #fffaf3;
}

.action-stack small {
  color: #917c69;
  line-height: 1.45;
}

.member-note {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 19px;
  padding: 14px;
  border-radius: 15px;
  color: #316f81;
  background: #e9f7fb;
}

.member-note span {
  display: grid;
  width: 24px;
  height: 24px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: #c9edf6;
  font-weight: 900;
}

.member-note p {
  margin: 2px 0 0;
  line-height: 1.5;
}

.features-section {
  display: grid;
  gap: 18px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 13px;
}

.feature-grid article {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  padding: 17px;
  border: 1px solid #f0e5d8;
  border-radius: 17px;
  background: #fffcf8;
}

.feature-grid article.unavailable {
  opacity: 0.66;
}

.feature-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 13px;
  font-weight: 900;
}

.feature-icon.orange {
  color: #a65d13;
  background: #fee4b8;
}

.feature-icon.blue {
  color: #24758d;
  background: #dff4fa;
}

.feature-icon.yellow {
  color: #9b6724;
  background: #fff0c9;
}

.feature-grid h4 {
  margin: 2px 0 5px;
  color: #4e3825;
}

.feature-grid p {
  margin: 0;
  color: #8a7461;
  font-size: 0.82rem;
  line-height: 1.45;
}

.feature-grid button {
  grid-column: 1 / -1;
  min-height: 36px;
  border: 0;
  border-radius: 10px;
  color: #907861;
  background: #f4eee7;
  cursor: pointer;
  font-weight: 800;
}

.feature-grid button:disabled {
  cursor: not-allowed;
}

@media (max-width: 950px) {
  .detail-grid,
  .feature-grid,
  .matches-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .hero-card {
    display: grid;
    padding: 22px;
  }

  .matches-hero {
    display: grid;
    padding: 22px;
  }

  .match-total {
    min-width: 0;
  }

  .matches-toolbar {
    align-items: flex-start;
  }

  .hero-meta {
    min-width: 0;
  }

  .edit-gender-grid {
    grid-template-columns: 1fr;
  }

  .edit-search-actions {
    display: grid;
  }

  .panel,
  .features-section {
    padding: 20px;
  }

  .participant-list article {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .invitation-form > div {
    grid-template-columns: 1fr;
  }

  .participant-role {
    grid-column: 2;
    width: fit-content;
  }
}

@media (max-width: 520px) {
  .matches-toolbar,
  .matches-state {
    display: grid;
  }

  .refresh-button {
    width: 100%;
  }
}
</style>
