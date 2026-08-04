<script setup lang="ts">
import { ref, watch } from 'vue'

import { authenticatedFetch, getErrorMessage } from '../api/client'
import type { CurrentProfile, ProfileLookup } from '../types/api'

const props = defineProps<{
  user: CurrentProfile
}>()

const emit = defineEmits<{
  'profile-updated': [profile: CurrentProfile]
}>()

const displayName = ref(props.user.display_name)
const lookupEmail = ref('')
const foundProfile = ref<ProfileLookup | null>(null)

const isSaving = ref(false)
const isSearching = ref(false)

const saveError = ref('')
const saveSuccess = ref('')
const lookupError = ref('')

watch(
  () => props.user.display_name,
  (value) => {
    displayName.value = value
  },
)

async function saveDisplayName() {
  isSaving.value = true
  saveError.value = ''
  saveSuccess.value = ''

  try {
    const response = await authenticatedFetch('/api/me/', {
      method: 'PATCH',
      body: JSON.stringify({
        display_name: displayName.value.trim(),
      }),
    })

    if (!response.ok) {
      saveError.value = await getErrorMessage(
        response,
        "Impossible d'enregistrer le nom d'affichage.",
      )
      return
    }

    const updatedProfile = (await response.json()) as CurrentProfile

    displayName.value = updatedProfile.display_name
    saveSuccess.value = 'Votre nom d’affichage a bien été enregistré.'
    emit('profile-updated', updatedProfile)
  } catch (error) {
    console.error('Échec de la modification du profil :', error)
    saveError.value = 'Impossible de contacter Django pour modifier le profil.'
  } finally {
    isSaving.value = false
  }
}

async function searchProfile() {
  const email = lookupEmail.value.trim()

  lookupError.value = ''
  foundProfile.value = null

  if (!email) {
    lookupError.value = 'Saisissez une adresse e-mail.'
    return
  }

  isSearching.value = true

  try {
    const query = new URLSearchParams({ email })
    const response = await authenticatedFetch(`/api/profiles/lookup/?${query.toString()}`)

    if (!response.ok) {
      lookupError.value = await getErrorMessage(
        response,
        'Aucun utilisateur ne correspond à cette adresse e-mail.',
      )
      return
    }

    foundProfile.value = (await response.json()) as ProfileLookup
  } catch (error) {
    console.error('Échec de la recherche du profil :', error)
    lookupError.value = 'Impossible de contacter Django pour effectuer la recherche.'
  } finally {
    isSearching.value = false
  }
}

function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Non disponible'
  }

  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
  }).format(date)
}
</script>

<template>
  <div class="settings-stack">
    <section class="settings-card account-card">
      <div class="section-heading">
        <div>
          <span class="section-kicker">Mon compte</span>
          <h2>Informations personnelles</h2>
        </div>

        <span class="section-number">01</span>
      </div>

      <dl class="profile-data">
        <div>
          <dt>Nom d’utilisateur</dt>
          <dd>@{{ user.username }}</dd>
        </div>

        <div>
          <dt>Adresse e-mail</dt>
          <dd>{{ user.email || 'Non renseignée' }}</dd>
        </div>

        <div>
          <dt>Identifiant</dt>
          <dd>#{{ user.id }}</dd>
        </div>

        <div>
          <dt>Membre depuis</dt>
          <dd>{{ formatDate(user.created_at) }}</dd>
        </div>
      </dl>

      <div class="roles-block">
        <span>Rôles Keycloak</span>

        <div class="role-list">
          <span v-for="role in user.roles" :key="role" class="role-badge">{{ role }}</span>
          <span v-if="user.roles.length === 0" class="muted-value">Aucun rôle</span>
        </div>
      </div>
    </section>

    <section class="settings-card">
      <div class="section-heading">
        <div>
          <span class="section-kicker">Personnalisation</span>
          <h2>Nom d’affichage</h2>
        </div>

        <span class="section-number">02</span>
      </div>

      <p class="section-description">
        Ce nom est visible dans l’application. Ton identifiant et ton e-mail restent administrés par
        Keycloak.
      </p>

      <form data-test="profile-form" @submit.prevent="saveDisplayName">
        <label for="display-name">Nom affiché dans l’application</label>

        <input
          id="display-name"
          v-model="displayName"
          data-test="display-name-input"
          type="text"
          maxlength="150"
          placeholder="Par exemple : Victor"
          autocomplete="name"
        />

        <p v-if="saveError" class="form-message error-message" role="alert">{{ saveError }}</p>
        <p v-if="saveSuccess" class="form-message success-message" role="status">
          {{ saveSuccess }}
        </p>

        <button type="submit" class="primary-button" :disabled="isSaving">
          {{ isSaving ? 'Enregistrement…' : 'Enregistrer le nom' }}
        </button>
      </form>
    </section>

    <section class="settings-card lookup-card">
      <div class="section-heading">
        <div>
          <span class="section-kicker">Invitations</span>
          <h2>Rechercher un utilisateur</h2>
        </div>

        <span class="section-number">03</span>
      </div>

      <p class="section-description">
        Retrouve une personne avec son adresse e-mail exacte avant de l’inviter dans une recherche.
      </p>

      <form class="lookup-form" data-test="lookup-form" @submit.prevent="searchProfile">
        <div>
          <label for="lookup-email">Adresse e-mail exacte</label>
          <input
            id="lookup-email"
            v-model="lookupEmail"
            data-test="lookup-email-input"
            type="email"
            placeholder="utilisateur@exemple.fr"
            autocomplete="off"
          />
        </div>

        <button type="submit" class="secondary-button" :disabled="isSearching">
          {{ isSearching ? 'Recherche…' : 'Rechercher' }}
        </button>
      </form>

      <p v-if="lookupError" class="form-message error-message" role="alert">
        {{ lookupError }}
      </p>

      <article v-if="foundProfile" class="search-result" data-test="lookup-result">
        <span class="result-avatar">
          {{ (foundProfile.display_name || foundProfile.username).charAt(0).toUpperCase() }}
        </span>

        <div>
          <small>Utilisateur trouvé</small>
          <strong>{{ foundProfile.display_name || foundProfile.username }}</strong>
          <p>{{ foundProfile.email }} · @{{ foundProfile.username }}</p>
        </div>

        <span class="result-check" aria-label="Utilisateur trouvé">✓</span>
      </article>
    </section>
  </div>
</template>

<style scoped>
.settings-stack {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
}

.settings-card {
  padding: 28px;
  border: 1px solid rgba(105, 75, 39, 0.1);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 45px rgba(130, 83, 32, 0.08);
}

.lookup-card {
  grid-column: 1 / -1;
}

.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.section-kicker,
.roles-block > span,
label,
dt {
  display: block;
  margin-bottom: 7px;
  color: #9a7042;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h2 {
  margin: 0;
  color: #3f2e20;
  font-size: 22px;
}

.section-number {
  color: #d4b590;
  font-size: 12px;
  font-weight: 900;
}

.section-description {
  max-width: 660px;
  margin: -5px 0 22px;
  color: #7c6b5c;
  font-size: 14px;
  line-height: 1.6;
}

.profile-data {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
  border-top: 1px solid #f0e5d8;
}

.profile-data div {
  min-width: 0;
  padding: 16px 12px 16px 0;
  border-bottom: 1px solid #f0e5d8;
}

.profile-data dd {
  overflow: hidden;
  margin: 0;
  color: #4c3928;
  font-size: 14px;
  font-weight: 750;
  text-overflow: ellipsis;
}

.roles-block {
  margin-top: 20px;
}

.role-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.role-badge {
  padding: 7px 10px;
  color: #795226;
  border-radius: 9px;
  background: #fff0d9;
  font-size: 12px;
  font-weight: 750;
}

.muted-value {
  color: #9d8c7c;
  font-size: 13px;
}

input {
  width: 100%;
  padding: 13px 14px;
  color: #3f2e20;
  border: 1px solid #e5d3bf;
  border-radius: 12px;
  outline: none;
  background: #fffdf9;
  transition:
    border-color 150ms ease,
    box-shadow 150ms ease;
}

input:focus {
  border-color: #ffa43a;
  box-shadow: 0 0 0 4px rgba(255, 164, 58, 0.16);
}

.primary-button,
.secondary-button {
  padding: 12px 18px;
  border: 0;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 850;
}

.primary-button {
  margin-top: 16px;
  color: #fff;
  background: #f49224;
  box-shadow: 0 10px 22px rgba(244, 146, 36, 0.22);
}

.secondary-button {
  min-width: 140px;
  color: #513716;
  background: #a3dff1;
}

.lookup-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 13px;
}

.form-message {
  margin: 13px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
}

.error-message {
  color: #9d3e3e;
  background: #fff0ec;
}

.success-message {
  color: #2f7352;
  background: #e9f8ef;
}

.search-result {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
  padding: 16px;
  border: 1px solid #cfe9d8;
  border-radius: 16px;
  background: #f5fcf7;
}

.result-avatar {
  display: grid;
  width: 45px;
  height: 45px;
  flex: 0 0 auto;
  place-items: center;
  color: #fff;
  border-radius: 14px;
  background: #55a67a;
  font-weight: 900;
}

.search-result > div {
  min-width: 0;
  flex: 1;
}

.search-result small,
.search-result strong {
  display: block;
}

.search-result small {
  margin-bottom: 3px;
  color: #4d8c69;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.search-result strong {
  color: #325340;
}

.search-result p {
  overflow: hidden;
  margin: 3px 0 0;
  color: #688073;
  font-size: 13px;
  text-overflow: ellipsis;
}

.result-check {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  color: #fff;
  border-radius: 50%;
  background: #55a67a;
  font-weight: 900;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

@media (max-width: 760px) {
  .settings-stack {
    grid-template-columns: 1fr;
  }

  .lookup-card {
    grid-column: auto;
  }

  .profile-data,
  .lookup-form {
    grid-template-columns: 1fr;
  }

  .secondary-button {
    width: 100%;
  }
}
</style>
