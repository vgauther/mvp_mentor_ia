<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { authenticatedFetch, getErrorMessage } from '../api/client'
import type { NameSearch, NameSearchParticipant, SearchGender, SearchStatus } from '../types/api'
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

const genderLabels: Record<SearchGender, string> = {
  female: 'Féminin',
  male: 'Masculin',
  mixed: 'Mixte',
}

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
    currentSearch.value = search

    if (search.status !== 'active') {
      isBrowsingFirstNames.value = false
    }
  },
)

function openNameBrowser() {
  if (currentSearch.value.status !== 'active') {
    return
  }

  isBrowsingFirstNames.value = true
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function closeNameBrowser() {
  isBrowsingFirstNames.value = false
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
        </div>
      </section>

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
                <p>L’invitation d’un proche sera ajoutée lors de la prochaine étape.</p>
              </div>
            </div>
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
            <button type="button" disabled>Bientôt</button>
          </article>

          <article>
            <span class="feature-icon yellow">♥</span>
            <div>
              <h4>Résultats et matchs</h4>
              <p>Découvre les prénoms appréciés par tous les participants.</p>
            </div>
            <button type="button" disabled>Bientôt</button>
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
.features-section {
  border: 1px solid rgba(126, 83, 35, 0.1);
  border-radius: 25px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 45px rgba(119, 82, 38, 0.07);
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
  font-weight: 800;
}

@media (max-width: 950px) {
  .detail-grid,
  .feature-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .hero-card {
    display: grid;
    padding: 22px;
  }

  .hero-meta {
    min-width: 0;
  }

  .panel,
  .features-section {
    padding: 20px;
  }

  .participant-list article {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .participant-role {
    grid-column: 2;
    width: fit-content;
  }
}
</style>
