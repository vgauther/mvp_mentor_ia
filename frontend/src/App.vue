<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import keycloak from './auth/keycloak'

interface CurrentProfile {
  id: number
  username: string
  email: string
  display_name: string
  roles: string[]
  created_at: string
  updated_at: string
}

interface ProfileLookup {
  id: number
  username: string
  email: string
  display_name: string
}

const user = ref<CurrentProfile | null>(null)
const foundProfile = ref<ProfileLookup | null>(null)

const displayName = ref('')
const lookupEmail = ref('')

const isLoading = ref(true)
const isSaving = ref(false)
const isSearching = ref(false)

const loadError = ref('')
const saveError = ref('')
const saveSuccess = ref('')
const lookupError = ref('')

const visibleName = computed(() => {
  if (!user.value) {
    return ''
  }

  return user.value.display_name || user.value.username
})

const initials = computed(() => {
  const name = visibleName.value.trim()

  if (!name) {
    return '?'
  }

  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('')
})

async function authenticatedFetch(path: string, options: RequestInit = {}) {
  await keycloak.updateToken(30)

  if (!keycloak.token) {
    throw new Error('Aucun jeton Keycloak disponible.')
  }

  const headers = new Headers(options.headers)

  headers.set('Authorization', `Bearer ${keycloak.token}`)

  if (options.body) {
    headers.set('Content-Type', 'application/json')
  }

  return fetch(`${import.meta.env.VITE_API_URL}${path}`, {
    ...options,
    headers,
  })
}

async function getErrorMessage(response: Response, fallbackMessage: string) {
  try {
    const data = (await response.json()) as {
      detail?: string
    }

    return data.detail || fallbackMessage
  } catch {
    return fallbackMessage
  }
}

async function loadUser() {
  isLoading.value = true
  loadError.value = ''

  try {
    const response = await authenticatedFetch('/api/me/')

    if (!response.ok) {
      throw new Error(`Réponse Django : ${response.status}`)
    }

    const profile = (await response.json()) as CurrentProfile

    user.value = profile
    displayName.value = profile.display_name || ''
  } catch (error) {
    console.error("Échec de la récupération de l'utilisateur :", error)

    loadError.value = 'Impossible de vérifier votre identité auprès de Django.'
  } finally {
    isLoading.value = false
  }
}

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

    user.value = (await response.json()) as CurrentProfile
    displayName.value = user.value.display_name || ''
    saveSuccess.value = 'Votre nom d’affichage a bien été enregistré.'
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
    const query = new URLSearchParams({
      email,
    })

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

function formatDate(value: string | undefined) {
  if (!value) {
    return 'Non disponible'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Non disponible'
  }

  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
    timeStyle: 'short',
  }).format(date)
}

async function logout() {
  await keycloak.logout({
    redirectUri: window.location.origin,
  })
}

onMounted(() => {
  void loadUser()
})
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Accueil Le Bon Prénom">
        <span class="brand-mark">LBP</span>

        <span>
          <strong>Le Bon Prénom</strong>
          <small>Espace de démonstration</small>
        </span>
      </a>

      <div class="session-actions">
        <span v-if="user" class="connected-badge">
          <span class="status-dot"></span>
          Connecté
        </span>

        <button type="button" class="logout-button" @click="logout">Se déconnecter</button>
      </div>
    </header>

    <section class="hero">
      <div>
        <p class="eyebrow">Compte utilisateur</p>

        <h1>
          Votre espace personnel,
          <span>simple et sécurisé.</span>
        </h1>

        <p class="hero-description">
          Cette page permet de vérifier visuellement la connexion entre Keycloak, Django et votre
          base PostgreSQL.
        </p>
      </div>

      <div class="architecture">
        <span>Keycloak</span>
        <span class="arrow">→</span>
        <span>Django</span>
        <span class="arrow">→</span>
        <span>PostgreSQL</span>
      </div>
    </section>

    <section v-if="isLoading" class="state-card" aria-live="polite">
      <div class="loader"></div>

      <div>
        <h2>Vérification de votre identité</h2>

        <p>Keycloak transmet votre jeton sécurisé à Django…</p>
      </div>
    </section>

    <section v-else-if="loadError" class="state-card error-state">
      <div class="state-icon">!</div>

      <div>
        <h2>Connexion impossible</h2>

        <p role="alert">
          {{ loadError }}
        </p>

        <button type="button" class="primary-button compact-button" @click="loadUser">
          Réessayer
        </button>
      </div>
    </section>

    <template v-else-if="user">
      <section class="profile-banner">
        <div class="avatar">
          {{ initials }}
        </div>

        <div class="profile-heading">
          <p class="eyebrow">Profil synchronisé</p>

          <h2>Bonjour {{ visibleName }}</h2>

          <p>Votre identité a été validée par Django.</p>
        </div>

        <div class="validation-badge">
          <span>✓</span>
          Identité validée
        </div>
      </section>

      <div class="dashboard-grid">
        <section class="card">
          <div class="card-heading">
            <div>
              <p class="eyebrow">Informations</p>
              <h2>Votre compte</h2>
            </div>

            <span class="card-icon">01</span>
          </div>

          <dl class="profile-data">
            <div>
              <dt>Nom d’utilisateur</dt>
              <dd>{{ user.username }}</dd>
            </div>

            <div>
              <dt>Adresse e-mail</dt>
              <dd>{{ user.email || 'Non renseignée' }}</dd>
            </div>

            <div>
              <dt>Identifiant Django</dt>
              <dd>#{{ user.id }}</dd>
            </div>

            <div>
              <dt>Compte créé le</dt>
              <dd>{{ formatDate(user.created_at) }}</dd>
            </div>
          </dl>

          <div class="roles-block">
            <span class="field-label">Rôles Keycloak</span>

            <div class="role-list">
              <span v-for="role in user.roles" :key="role" class="role-badge">
                {{ role }}
              </span>

              <span v-if="user.roles.length === 0" class="empty-value"> Aucun rôle </span>
            </div>
          </div>
        </section>

        <section class="card">
          <div class="card-heading">
            <div>
              <p class="eyebrow">Personnalisation</p>
              <h2>Nom d’affichage</h2>
            </div>

            <span class="card-icon">02</span>
          </div>

          <p class="card-description">
            Ce nom est stocké dans Django. Votre nom d’utilisateur et votre e-mail restent
            administrés par Keycloak.
          </p>

          <form data-test="profile-form" @submit.prevent="saveDisplayName">
            <label for="display-name"> Nom affiché dans l’application </label>

            <input
              id="display-name"
              v-model="displayName"
              data-test="display-name-input"
              type="text"
              maxlength="150"
              placeholder="Par exemple : Victor"
              autocomplete="name"
            />

            <p v-if="saveError" class="form-message error-message" role="alert">
              {{ saveError }}
            </p>

            <p v-if="saveSuccess" class="form-message success-message" role="status">
              {{ saveSuccess }}
            </p>

            <button type="submit" class="primary-button" :disabled="isSaving">
              {{ isSaving ? 'Enregistrement…' : 'Enregistrer le nom' }}
            </button>
          </form>
        </section>

        <section class="card lookup-card">
          <div class="card-heading">
            <div>
              <p class="eyebrow">Préparation des invitations</p>
              <h2>Rechercher un utilisateur</h2>
            </div>

            <span class="card-icon">03</span>
          </div>

          <p class="card-description">
            La recherche fonctionne uniquement avec une adresse e-mail complète. Elle ne permet pas
            de parcourir l’ensemble des utilisateurs.
          </p>

          <form class="lookup-form" data-test="lookup-form" @submit.prevent="searchProfile">
            <div class="lookup-field">
              <label for="lookup-email"> Adresse e-mail exacte </label>

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
            <div class="result-avatar">
              {{ (foundProfile.display_name || foundProfile.username).charAt(0).toUpperCase() }}
            </div>

            <div>
              <span>Utilisateur trouvé</span>

              <strong>
                {{ foundProfile.display_name || foundProfile.username }}
              </strong>

              <p>
                {{ foundProfile.email }}
                · @{{ foundProfile.username }}
              </p>
            </div>

            <div class="result-check">✓</div>
          </article>
        </section>
      </div>
    </template>

    <footer>Démonstration technique · Keycloak · Django REST · Vue.js</footer>
  </main>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
  color: #202138;
  background:
    radial-gradient(circle at top left, rgba(255, 210, 218, 0.72), transparent 34rem),
    linear-gradient(145deg, #fffaf8 0%, #f7f4ff 100%);
  font-family: Inter, Avenir, Helvetica, Arial, sans-serif;
}

:global(button),
:global(input) {
  font: inherit;
}

button {
  transition:
    transform 150ms ease,
    box-shadow 150ms ease,
    opacity 150ms ease;
}

button:not(:disabled):hover {
  transform: translateY(-1px);
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.app-shell {
  width: min(1180px, calc(100% - 40px));
  min-height: 100vh;
  margin: 0 auto;
  padding-bottom: 28px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 92px;
  border-bottom: 1px solid rgba(75, 63, 116, 0.12);
}

.brand {
  display: flex;
  align-items: center;
  gap: 13px;
  color: inherit;
  text-decoration: none;
}

.brand-mark {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  color: white;
  border-radius: 15px;
  background: #5e51a4;
  box-shadow: 0 10px 25px rgba(94, 81, 164, 0.23);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-size: 17px;
}

.brand small {
  margin-top: 2px;
  color: #77738d;
  font-size: 12px;
}

.session-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.connected-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #38745a;
  font-size: 13px;
  font-weight: 700;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #45b77e;
  box-shadow: 0 0 0 4px rgba(69, 183, 126, 0.14);
}

.logout-button {
  padding: 10px 15px;
  color: #514977;
  border: 1px solid rgba(81, 73, 119, 0.2);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.65);
  cursor: pointer;
  font-weight: 700;
}

.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 40px;
  padding: 70px 0 48px;
}

.eyebrow {
  margin: 0 0 10px;
  color: #7667bd;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.13em;
  text-transform: uppercase;
}

.hero h1 {
  max-width: 680px;
  margin: 0;
  color: #29273d;
  font-size: clamp(39px, 6vw, 68px);
  line-height: 0.99;
  letter-spacing: -0.055em;
}

.hero h1 span {
  color: #7465b7;
}

.hero-description {
  max-width: 600px;
  margin: 24px 0 0;
  color: #716e7e;
  font-size: 17px;
  line-height: 1.65;
}

.architecture {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 14px 17px;
  border: 1px solid rgba(100, 87, 164, 0.13);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.62);
  color: #655d81;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.arrow {
  color: #cf7187;
}

.state-card,
.profile-banner,
.card {
  border: 1px solid rgba(88, 76, 141, 0.12);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 24px 60px rgba(72, 61, 111, 0.09);
  backdrop-filter: blur(18px);
}

.state-card {
  display: flex;
  align-items: center;
  gap: 22px;
  min-height: 180px;
  padding: 36px;
  border-radius: 25px;
}

.state-card h2,
.state-card p {
  margin: 0;
}

.state-card p {
  margin-top: 8px;
  color: #77738a;
}

.error-state {
  border-color: rgba(197, 75, 98, 0.2);
}

.state-icon {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  color: #c54b62;
  border-radius: 50%;
  background: #ffeaee;
  font-size: 22px;
  font-weight: 900;
}

.loader {
  width: 45px;
  height: 45px;
  flex: 0 0 auto;
  border: 4px solid #ebe7fb;
  border-top-color: #7465b7;
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}

.profile-banner {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 22px;
  padding: 25px 28px;
  border-radius: 24px;
}

.avatar {
  display: grid;
  width: 66px;
  height: 66px;
  flex: 0 0 auto;
  place-items: center;
  color: #514388;
  border-radius: 21px;
  background: linear-gradient(145deg, #ffe0e5, #ded7ff);
  font-size: 23px;
  font-weight: 900;
}

.profile-heading {
  flex: 1;
}

.profile-heading .eyebrow {
  margin-bottom: 5px;
}

.profile-heading h2 {
  margin: 0;
  font-size: 25px;
}

.profile-heading > p:last-child {
  margin: 5px 0 0;
  color: #77738a;
}

.validation-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 13px;
  color: #367557;
  border-radius: 12px;
  background: #eaf8f0;
  font-size: 13px;
  font-weight: 800;
}

.validation-badge span {
  display: grid;
  width: 20px;
  height: 20px;
  place-items: center;
  color: white;
  border-radius: 50%;
  background: #46a873;
  font-size: 12px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
}

.card {
  padding: 30px;
  border-radius: 24px;
}

.lookup-card {
  grid-column: 1 / -1;
}

.card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.card-heading .eyebrow {
  margin-bottom: 6px;
}

.card-heading h2 {
  margin: 0;
  font-size: 22px;
}

.card-icon {
  color: #a19ab9;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.card-description {
  max-width: 610px;
  margin: -8px 0 23px;
  color: #77738a;
  font-size: 14px;
  line-height: 1.65;
}

.profile-data {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
  border-top: 1px solid #edeaf3;
}

.profile-data div {
  min-width: 0;
  padding: 17px 12px 17px 0;
  border-bottom: 1px solid #edeaf3;
}

.profile-data dt,
.field-label,
label {
  display: block;
  margin-bottom: 7px;
  color: #8a8599;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.profile-data dd {
  overflow: hidden;
  margin: 0;
  color: #353246;
  font-size: 14px;
  font-weight: 750;
  text-overflow: ellipsis;
}

.roles-block {
  margin-top: 21px;
}

.role-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.role-badge {
  padding: 7px 10px;
  color: #61549c;
  border-radius: 9px;
  background: #f0edfb;
  font-size: 12px;
  font-weight: 700;
}

.empty-value {
  color: #918c9f;
  font-size: 13px;
}

input {
  width: 100%;
  padding: 13px 14px;
  color: #302d40;
  border: 1px solid #dcd7e8;
  border-radius: 11px;
  outline: none;
  background: #fff;
  transition:
    border-color 150ms ease,
    box-shadow 150ms ease;
}

input:focus {
  border-color: #8474c6;
  box-shadow: 0 0 0 4px rgba(132, 116, 198, 0.13);
}

.primary-button,
.secondary-button {
  margin-top: 16px;
  padding: 12px 17px;
  border-radius: 11px;
  cursor: pointer;
  font-weight: 800;
}

.primary-button {
  color: white;
  border: 0;
  background: #6555a6;
  box-shadow: 0 10px 22px rgba(101, 85, 166, 0.2);
}

.secondary-button {
  min-width: 140px;
  color: white;
  border: 0;
  background: #cf7187;
  box-shadow: 0 10px 22px rgba(207, 113, 135, 0.2);
}

.compact-button {
  margin-top: 16px;
}

.form-message {
  margin: 13px 0 0;
  padding: 10px 12px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 650;
}

.error-message {
  color: #a93d52;
  background: #fff0f2;
}

.success-message {
  color: #327152;
  background: #eaf8f0;
}

.lookup-form {
  display: flex;
  align-items: flex-end;
  gap: 13px;
}

.lookup-field {
  flex: 1;
}

.lookup-form .secondary-button {
  margin-top: 0;
}

.search-result {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-top: 21px;
  padding: 17px;
  border: 1px solid #dcecdf;
  border-radius: 15px;
  background: #f6fcf8;
}

.result-avatar {
  display: grid;
  width: 45px;
  height: 45px;
  flex: 0 0 auto;
  place-items: center;
  color: white;
  border-radius: 14px;
  background: #55a67a;
  font-weight: 900;
}

.search-result > div:nth-child(2) {
  min-width: 0;
  flex: 1;
}

.search-result span,
.search-result strong,
.search-result p {
  display: block;
}

.search-result span {
  margin-bottom: 3px;
  color: #5f8e71;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.search-result strong {
  color: #2e4938;
}

.search-result p {
  overflow: hidden;
  margin: 4px 0 0;
  color: #658171;
  font-size: 13px;
  text-overflow: ellipsis;
}

.result-check {
  display: grid;
  width: 31px;
  height: 31px;
  flex: 0 0 auto;
  place-items: center;
  color: #397855;
  border-radius: 50%;
  background: #dff3e6;
  font-weight: 900;
}

footer {
  padding: 35px 0 5px;
  color: #9994a5;
  text-align: center;
  font-size: 12px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 820px) {
  .hero {
    display: block;
    padding-top: 50px;
  }

  .architecture {
    width: fit-content;
    margin-top: 28px;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .lookup-card {
    grid-column: auto;
  }

  .profile-banner {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .validation-badge {
    margin-left: 86px;
  }
}

@media (max-width: 590px) {
  .app-shell {
    width: min(100% - 24px, 1180px);
  }

  .topbar {
    min-height: 76px;
  }

  .brand small,
  .connected-badge {
    display: none;
  }

  .hero {
    padding: 42px 0 35px;
  }

  .hero h1 {
    font-size: 40px;
  }

  .architecture {
    max-width: 100%;
    overflow-x: auto;
  }

  .profile-banner,
  .card,
  .state-card {
    padding: 22px;
    border-radius: 19px;
  }

  .validation-badge {
    width: 100%;
    margin-left: 0;
  }

  .profile-data {
    grid-template-columns: 1fr;
  }

  .lookup-form {
    align-items: stretch;
    flex-direction: column;
  }

  .lookup-form .secondary-button {
    width: 100%;
  }
}
</style>
