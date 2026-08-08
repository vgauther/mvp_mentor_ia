<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { authenticatedFetch, getErrorMessage } from '../api/client'
import type { InvitationStatus, SearchInvitation } from '../types/api'
import FeatherIcon from './FeatherIcon.vue'

const invitations = ref<SearchInvitation[]>([])
const isLoading = ref(true)
const loadError = ref('')
const actionError = ref('')
const actionSuccess = ref('')
const invitationBeingUpdated = ref<number | null>(null)

const invitationCount = computed(() => invitations.value.length)

async function loadInvitations() {
  isLoading.value = true
  loadError.value = ''
  actionError.value = ''

  try {
    const response = await authenticatedFetch('/api/invitations/')

    if (!response.ok) {
      loadError.value = await getErrorMessage(
        response,
        'Impossible de charger tes invitations.',
      )
      return
    }

    invitations.value = (await response.json()) as SearchInvitation[]
  } catch (error) {
    console.error('Échec du chargement des invitations :', error)
    loadError.value = 'Impossible de contacter Django pour charger tes invitations.'
  } finally {
    isLoading.value = false
  }
}

async function respondToInvitation(
  invitation: SearchInvitation,
  invitationStatus: Extract<InvitationStatus, 'accepted' | 'declined'>,
) {
  invitationBeingUpdated.value = invitation.id
  actionError.value = ''
  actionSuccess.value = ''

  try {
    const response = await authenticatedFetch(`/api/invitations/${invitation.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({
        invitation_status: invitationStatus,
      }),
    })

    if (!response.ok) {
      actionError.value = await getErrorMessage(
        response,
        "Impossible de répondre à cette invitation.",
      )
      return
    }

    invitations.value = invitations.value.filter((item) => item.id !== invitation.id)
    actionSuccess.value =
      invitationStatus === 'accepted'
        ? `Tu as rejoint la recherche « ${invitation.search.title} ». Elle est maintenant disponible dans Mes recherches.`
        : `Tu as refusé l’invitation à la recherche « ${invitation.search.title} ».`
  } catch (error) {
    console.error("Échec de la réponse à l'invitation :", error)
    actionError.value = "Impossible de contacter Django pour répondre à cette invitation."
  } finally {
    invitationBeingUpdated.value = null
  }
}

function creatorName(invitation: SearchInvitation) {
  return invitation.search.creator.display_name || invitation.search.creator.username
}

function creatorInitials(invitation: SearchInvitation) {
  const name = creatorName(invitation).trim()

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

onMounted(() => {
  void loadInvitations()
})
</script>

<template>
  <div class="invitations-content">
    <section class="invitations-panel">
      <div class="invitations-toolbar">
        <p>
          <strong>{{ invitationCount }}</strong>
          invitation{{ invitationCount > 1 ? 's' : '' }} en attente
        </p>

        <button
          type="button"
          class="refresh-button"
          :disabled="isLoading || invitationBeingUpdated !== null"
          @click="loadInvitations"
        >
          <FeatherIcon name="refresh-cw" :size="15" />
          Actualiser
        </button>
      </div>

      <p v-if="actionSuccess" class="feedback success-feedback" role="status">
        {{ actionSuccess }}
      </p>

      <p v-if="actionError" class="feedback error-feedback" role="alert">
        {{ actionError }}
      </p>

      <div v-if="isLoading" class="panel-state" aria-live="polite">
        <span class="loader"></span>

        <div>
          <strong>Chargement de tes invitations…</strong>
          <p>Django vérifie les recherches partagées avec toi.</p>
        </div>
      </div>

      <div v-else-if="loadError" class="panel-state error-state">
        <span class="state-symbol"><FeatherIcon name="alert-circle" :size="21" /></span>

        <div>
          <strong>Chargement impossible</strong>
          <p role="alert">{{ loadError }}</p>
          <button type="button" class="retry-button" @click="loadInvitations">
            <FeatherIcon name="rotate-ccw" :size="15" />
            Réessayer
          </button>
        </div>
      </div>

      <div v-else-if="invitations.length === 0" class="empty-state">
        <span class="empty-icon"><FeatherIcon name="inbox" :size="27" /></span>
        <h3>Aucune invitation en attente</h3>
        <p>Les nouvelles invitations apparaîtront automatiquement dans cette rubrique.</p>
      </div>

      <div v-else class="invitation-list">
        <article
          v-for="invitation in invitations"
          :key="invitation.id"
          class="invitation-card"
        >
          <div class="invitation-main">
            <span class="creator-avatar">{{ creatorInitials(invitation) }}</span>

            <div class="invitation-copy">
              <span class="invitation-label">Invitation reçue</span>
              <h3>{{ invitation.search.title }}</h3>
              <p>
                <strong>{{ creatorName(invitation) }}</strong>
                t’invite à chercher le bon prénom ensemble.
              </p>

              <div class="invitation-meta">
                <span>{{ invitation.role_label }}</span>
                <span>Reçue le {{ formatDate(invitation.created_at) }}</span>
              </div>
            </div>
          </div>

          <div class="invitation-actions">
            <button
              type="button"
              class="decline-button"
              :disabled="invitationBeingUpdated !== null"
              @click="respondToInvitation(invitation, 'declined')"
            >
              <FeatherIcon name="x" :size="15" />
              {{ invitationBeingUpdated === invitation.id ? 'En cours…' : 'Refuser' }}
            </button>

            <button
              type="button"
              class="accept-button"
              :disabled="invitationBeingUpdated !== null"
              @click="respondToInvitation(invitation, 'accepted')"
            >
              <FeatherIcon name="check" :size="15" />
              {{ invitationBeingUpdated === invitation.id ? 'En cours…' : 'Accepter' }}
            </button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.invitations-content {
  display: grid;
  gap: 16px;
}

.invitations-panel {
  padding: 0;
}

.invitations-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.invitation-label {
  color: #da7b14;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.invitations-toolbar p {
  margin: 0;
  color: #806e5e;
  font-size: 13px;
}

.invitations-toolbar p strong {
  color: #4a3421;
  font-size: 16px;
}

.refresh-button,
.retry-button,
.accept-button,
.decline-button {
  border-radius: 11px;
  cursor: pointer;
  font-weight: 850;
  transition:
    transform 150ms ease,
    box-shadow 150ms ease,
    opacity 150ms ease;
}

.refresh-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 10px 13px;
  color: #8a520f;
  border: 1px solid #f0d7b4;
  background: #fff9ef;
  font-size: 11px;
}

button:disabled {
  cursor: wait;
  opacity: 0.58;
}

button:not(:disabled):hover {
  transform: translateY(-1px);
}

.feedback {
  margin: 20px 0 0;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 750;
}

.success-feedback {
  color: #2f704e;
  border: 1px solid #cfe9da;
  background: #edf9f2;
}

.error-feedback {
  color: #9d3e3e;
  border: 1px solid #f0ceca;
  background: #fff1ee;
}

.panel-state,
.empty-state {
  min-height: 250px;
  margin-top: 23px;
  border: 1px dashed #ead7c2;
  border-radius: 18px;
  background: #fffcf7;
}

.panel-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 28px;
}

.panel-state strong {
  color: #4c3828;
  font-size: 15px;
}

.panel-state p {
  margin: 5px 0 0;
  color: #917d6e;
  font-size: 12px;
}

.loader {
  width: 40px;
  height: 40px;
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
  font-size: 20px;
  font-weight: 900;
}

.retry-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 13px;
  padding: 9px 13px;
  color: #fff;
  border: 0;
  background: #f49224;
  font-size: 11px;
}

.empty-state {
  display: grid;
  place-content: center;
  padding: 35px;
  text-align: center;
}

.empty-icon {
  display: grid;
  width: 56px;
  height: 56px;
  place-items: center;
  margin: 0 auto 14px;
  color: #bd7021;
  border-radius: 18px;
  background: #ffebca;
  font-size: 27px;
}

.empty-state h3 {
  margin: 0;
  color: #4b3626;
  font-size: 18px;
}

.empty-state p {
  max-width: 430px;
  margin: 8px 0 0;
  color: #917d6e;
  font-size: 12px;
  line-height: 1.6;
}

.invitation-list {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.invitation-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px;
  border: 1px solid #eadbc9;
  border-radius: 16px;
  background: #ffffff;
}

.invitation-main {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 15px;
}

.creator-avatar {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  color: #74430c;
  border-radius: 15px;
  background: linear-gradient(145deg, #fee4b8, #ffc065);
  font-size: 13px;
  font-weight: 900;
}

.invitation-copy {
  min-width: 0;
}

.invitation-copy h3 {
  margin: 4px 0 5px;
  overflow: hidden;
  color: #453123;
  font-size: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.invitation-copy p {
  margin: 0;
  color: #806c5e;
  font-size: 12px;
  line-height: 1.55;
}

.invitation-copy p strong {
  color: #5a4030;
}

.invitation-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 11px;
}

.invitation-meta span {
  padding: 5px 8px;
  color: #8a6b4e;
  border-radius: 8px;
  background: #fff3df;
  font-size: 9px;
  font-weight: 800;
}

.invitation-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
}

.accept-button,
.decline-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-width: 88px;
  padding: 10px 13px;
  font-size: 11px;
}

.accept-button {
  color: #fff;
  border: 1px solid #eb8e24;
  background: linear-gradient(145deg, #f7a23c, #ed8518);
  box-shadow: 0 8px 18px rgba(237, 133, 24, 0.2);
}

.decline-button {
  color: #836e5c;
  border: 1px solid #e5d8ca;
  background: #fff;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .invitations-toolbar,
  .invitation-card {
    align-items: flex-start;
    flex-direction: column;
  }

  .refresh-button {
    align-self: flex-start;
  }

  .invitation-actions {
    width: 100%;
  }

  .accept-button,
  .decline-button {
    flex: 1;
  }
}

@media (max-width: 480px) {
  .invitation-card {
    padding: 16px;
  }

  .invitation-main {
    align-items: flex-start;
  }

  .invitation-actions {
    flex-direction: column-reverse;
  }
}
</style>
