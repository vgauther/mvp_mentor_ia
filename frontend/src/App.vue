<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { authenticatedFetch } from "./api/client";
import logoIconUrl from "./assets/brand/logo-icon.png";
import keycloak from "./auth/keycloak";
import FeatherIcon from "./components/FeatherIcon.vue";
import InvitationsDashboard from "./components/InvitationsDashboard.vue";
import ProfileSettings from "./components/ProfileSettings.vue";
import SearchDashboard from "./components/SearchDashboard.vue";
import SearchDetail from "./components/SearchDetail.vue";
import type { CurrentProfile, NameSearch } from "./types/api";

type AppSection = "searches" | "invitations" | "profile";
type SearchView = "browser" | "detail";

const user = ref<CurrentProfile | null>(null);
const isLoading = ref(true);
const loadError = ref("");
const activeSection = ref<AppSection>("searches");
const selectedSearch = ref<NameSearch | null>(null);
const selectedSearchView = ref<SearchView>("detail");

const visibleName = computed(() => {
  if (!user.value) {
    return "";
  }

  return user.value.display_name || user.value.username;
});

const initials = computed(() => {
  const name = visibleName.value.trim();

  if (!name) {
    return "?";
  }

  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
});

const pageTitle = computed(() => {
  if (activeSection.value === "profile") {
    return "Ton profil";
  }

  if (activeSection.value === "invitations") {
    return "Tes invitations";
  }

  return "Tes recherches de prénoms";
});

const pageDescription = computed(() => {
  if (activeSection.value === "profile") {
    return "Consulte tes informations et personnalise ton compte.";
  }

  if (activeSection.value === "invitations") {
    return "Retrouve les recherches auxquelles un autre utilisateur t’invite à participer.";
  }

  return "Retrouve tes recherches ou commence-en une nouvelle.";
});

async function loadUser() {
  isLoading.value = true;
  loadError.value = "";

  try {
    const response = await authenticatedFetch("/api/me/");

    if (!response.ok) {
      throw new Error(`Réponse Django : ${response.status}`);
    }

    user.value = (await response.json()) as CurrentProfile;
  } catch (error) {
    console.error("Échec de la récupération de l'utilisateur :", error);
    loadError.value = "Impossible de vérifier votre identité auprès de Django.";
  } finally {
    isLoading.value = false;
  }
}

function showSearches() {
  activeSection.value = "searches";
  selectedSearch.value = null;
}

function showProfile() {
  activeSection.value = "profile";
  selectedSearch.value = null;
}

function showInvitations() {
  activeSection.value = "invitations";
  selectedSearch.value = null;
}

function openSearch(search: NameSearch) {
  activeSection.value = "searches";
  selectedSearch.value = search;
  selectedSearchView.value = "browser";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function openSearchDetails(search: NameSearch) {
  activeSection.value = "searches";
  selectedSearch.value = search;
  selectedSearchView.value = "detail";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function closeSearch() {
  selectedSearch.value = null;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateSelectedSearch(search: NameSearch) {
  selectedSearch.value = search;
}

function updateProfile(profile: CurrentProfile) {
  user.value = profile;
}

async function logout() {
  await keycloak.logout({
    redirectUri: window.location.origin,
  });
}

onMounted(() => {
  void loadUser();
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="/" aria-label="Accueil Le Bon Prénom">
        <img :src="logoIconUrl" alt="" />

        <span>
          <strong>Le Bon Prénom</strong>
          <small>Trouvez-le ensemble</small>
        </span>
      </a>

      <nav aria-label="Navigation principale">
        <button
          type="button"
          :class="{ active: activeSection === 'searches' }"
          data-test="searches-navigation"
          @click="showSearches"
        >
          <span class="nav-icon"><FeatherIcon name="heart" :size="19" /></span>
          <span>Recherches</span>
        </button>

        <button
          type="button"
          :class="{ active: activeSection === 'invitations' }"
          data-test="invitations-navigation"
          @click="showInvitations"
        >
          <span class="nav-icon"><FeatherIcon name="mail" :size="19" /></span>
          <span>Invitations</span>
        </button>

        <button
          type="button"
          :class="{ active: activeSection === 'profile' }"
          data-test="profile-navigation"
          @click="showProfile"
        >
          <span class="nav-icon"><FeatherIcon name="user" :size="19" /></span>
          <span>Profil</span>
        </button>
      </nav>

      <div v-if="user" class="sidebar-profile">
        <span class="avatar">{{ initials }}</span>

        <span>
          <strong>{{ visibleName }}</strong>
          <small>{{ user.email || `@${user.username}` }}</small>
        </span>
      </div>

      <button type="button" class="logout-button" @click="logout">
        <FeatherIcon name="log-out" :size="16" />
        Se déconnecter
      </button>
    </aside>

    <main class="main-content">
      <header class="mobile-header">
        <a class="mobile-brand" href="/" aria-label="Accueil Le Bon Prénom">
          <img :src="logoIconUrl" alt="" />
          <strong>Le Bon Prénom</strong>
        </a>

        <div class="mobile-actions">
          <button
            type="button"
            class="mobile-navigation"
            aria-label="Afficher mes recherches"
            :class="{ active: activeSection === 'searches' }"
            @click="showSearches"
          >
            <FeatherIcon name="heart" :size="19" />
          </button>

          <button
            type="button"
            class="mobile-navigation"
            aria-label="Afficher mes invitations"
            :class="{ active: activeSection === 'invitations' }"
            @click="showInvitations"
          >
            <FeatherIcon name="mail" :size="19" />
          </button>

          <button
            type="button"
            class="mobile-navigation"
            aria-label="Afficher mon profil"
            :class="{ active: activeSection === 'profile' }"
            @click="showProfile"
          >
            <FeatherIcon name="user" :size="19" />
          </button>

          <button
            type="button"
            class="mobile-logout"
            aria-label="Se déconnecter"
            @click="logout"
          >
            <FeatherIcon name="log-out" :size="19" />
          </button>
        </div>
      </header>

      <section v-if="isLoading" class="app-state" aria-live="polite">
        <span class="loader"></span>

        <div>
          <h1>Vérification de votre identité</h1>
          <p>Keycloak transmet votre accès sécurisé à Django…</p>
        </div>
      </section>

      <section v-else-if="loadError" class="app-state error-state">
        <span class="state-symbol"><FeatherIcon name="alert-circle" :size="23" /></span>

        <div>
          <h1>Connexion impossible</h1>
          <p role="alert">{{ loadError }}</p>
          <button type="button" class="retry-button" @click="loadUser">
            <FeatherIcon name="rotate-ccw" :size="16" />
            Réessayer
          </button>
        </div>
      </section>

      <template v-else-if="user">
        <header v-if="!selectedSearch" class="page-heading">
          <div>
            <p>
              Bonjour {{ visibleName }}
              <FeatherIcon name="sun" :size="15" />
            </p>

            <h1>{{ pageTitle }}</h1>
            <span>{{ pageDescription }}</span>
          </div>

        </header>

        <SearchDetail
          v-if="activeSection === 'searches' && selectedSearch"
          :search="selectedSearch"
          :user-id="user.id"
          :initial-view="selectedSearchView"
          @back="closeSearch"
          @search-updated="updateSelectedSearch"
        />

        <SearchDashboard
          v-else-if="activeSection === 'searches'"
          :user-id="user.id"
          @open-search="openSearch"
          @open-search-details="openSearchDetails"
        />

        <InvitationsDashboard v-else-if="activeSection === 'invitations'" />

        <ProfileSettings v-else :user="user" @profile-updated="updateProfile" />
      </template>

    </main>
  </div>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(html) {
  min-width: 320px;
  background: #fbfaf8;
}

:global(body) {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
  color: #3f2e20;
  background: #fbfaf8;
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

.app-shell {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  display: flex;
  height: 100vh;
  flex-direction: column;
  padding: 22px 14px 16px;
  border-right: 1px solid rgba(126, 83, 35, 0.1);
  background: #ffffff;
}

.brand,
.mobile-brand {
  display: flex;
  align-items: center;
  gap: 11px;
  color: inherit;
  text-decoration: none;
}

.brand img {
  width: 44px;
  height: 44px;
  border-radius: 13px;
  object-fit: cover;
  box-shadow: 0 10px 24px rgba(238, 137, 27, 0.13);
}

.brand strong,
.brand small,
.sidebar-profile strong,
.sidebar-profile small {
  display: block;
}

.brand strong {
  color: #d87208;
  font-size: 16px;
  line-height: 1.1;
}

.brand small {
  margin-top: 3px;
  color: #9a806b;
  font-size: 10px;
  font-weight: 700;
}

nav {
  display: grid;
  gap: 7px;
  margin-top: 30px;
}

nav button {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 11px 12px;
  color: #776353;
  border: 0;
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  text-align: left;
}

nav button.active {
  color: #8d500c;
  background: #fee4b8;
  box-shadow: inset 3px 0 #ffa43a;
}

.nav-icon {
  display: grid;
  width: 25px;
  height: 25px;
  place-items: center;
  font-size: 20px;
  font-weight: 900;
}

.sidebar-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  padding: 15px 9px;
  border-top: 1px solid #f0e4d7;
}

.sidebar-profile > span:last-child {
  min-width: 0;
}

.avatar {
  display: grid;
  width: 39px;
  height: 39px;
  flex: 0 0 auto;
  place-items: center;
  color: #74430c;
  border-radius: 13px;
  background: linear-gradient(145deg, #fee4b8, #ffc065);
  font-size: 12px;
  font-weight: 900;
}

.sidebar-profile strong,
.sidebar-profile small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-profile strong {
  color: #493525;
  font-size: 12px;
}

.sidebar-profile small {
  margin-top: 3px;
  color: #9b8878;
  font-size: 9px;
}

.logout-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px;
  color: #7d6958;
  border: 1px solid #e8dbcf;
  border-radius: 11px;
  background: #fff;
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
}

.main-content {
  width: min(1120px, 100%);
  min-width: 0;
  margin: 0 auto;
  padding: 28px 32px 24px;
}

.mobile-header {
  display: none;
}

.page-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.page-heading p {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 5px;
  color: #a16f3e;
  font-size: 12px;
  font-weight: 800;
}

.page-heading h1 {
  margin: 0;
  color: #3d2c1f;
  font-size: clamp(27px, 3vw, 36px);
  letter-spacing: -0.035em;
}

.page-heading div > span {
  display: block;
  margin-top: 5px;
  color: #897568;
  font-size: 14px;
}

.app-state {
  display: flex;
  min-height: calc(100vh - 100px);
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 30px;
  text-align: left;
}

.app-state h1 {
  margin: 0;
  color: #3e2d20;
  font-size: 25px;
}

.app-state p {
  margin: 8px 0 0;
  color: #887568;
}

.loader {
  width: 46px;
  height: 46px;
  flex: 0 0 auto;
  border: 4px solid #fee6c2;
  border-top-color: #f49224;
  border-radius: 50%;
  animation: spin 750ms linear infinite;
}

.state-symbol {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  color: #a84444;
  border-radius: 50%;
  background: #fff0ec;
  font-size: 22px;
  font-weight: 900;
}

.retry-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 16px;
  padding: 10px 15px;
  color: #fff;
  border: 0;
  border-radius: 11px;
  background: #f49224;
  cursor: pointer;
  font-weight: 850;
}

.mobile-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-navigation,
.mobile-logout {
  display: grid;
  width: 39px;
  height: 39px;
  place-items: center;
  color: #7d6958;
  border: 1px solid #e5d7c9;
  border-radius: 11px;
  background: #fff;
  cursor: pointer;
}

.mobile-navigation {
  color: #7d6958;
}

.mobile-navigation.active {
  color: #8d500c;
  background: #fff5e5;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 920px) {
  .app-shell {
    display: block;
  }

  .sidebar {
    display: none;
  }

  .main-content {
    padding: 0 20px 22px;
  }

  .mobile-header {
    display: flex;
    min-height: 76px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
    border-bottom: 1px solid #eddfd1;
  }

  .mobile-brand img {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    object-fit: cover;
  }

  .mobile-brand strong {
    color: #d87208;
    font-size: 15px;
  }

  .page-heading {
    align-items: flex-start;
  }
}

@media (max-width: 600px) {
  .main-content {
    padding: 0 15px 18px;
  }

  .page-heading h1 {
    font-size: 30px;
  }

  .app-state {
    min-height: calc(100vh - 120px);
    padding: 20px 0;
  }
}
</style>
