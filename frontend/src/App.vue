<script setup lang="ts">
import { onMounted, ref } from 'vue'

import keycloak from './auth/keycloak'

interface ApiUser {
  id: string
  username: string
  email: string | null
  roles: string[]
}

const user = ref<ApiUser | null>(null)
const isLoading = ref(true)
const errorMessage = ref('')

async function loadUser() {
  try {
    await keycloak.updateToken(30)

    if (!keycloak.token) {
      throw new Error('Aucun jeton Keycloak disponible.')
    }

    const response = await fetch(
      `${import.meta.env.VITE_API_URL}/api/me/`,
      {
        headers: {
          Authorization: `Bearer ${keycloak.token}`,
        },
      },
    )

    if (!response.ok) {
      throw new Error(`Réponse Django : ${response.status}`)
    }

    user.value = await response.json() as ApiUser
  } catch (error) {
    console.error(
      "Échec de la récupération de l'utilisateur :",
      error,
    )
    errorMessage.value =
      "Impossible de vérifier votre identité auprès de Django."
  } finally {
    isLoading.value = false
  }
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
  <main>
    <h1>Le Bon Prénom</h1>

    <section>
      <p v-if="isLoading">
        Vérification de votre identité...
      </p>

      <p v-else-if="errorMessage" role="alert">
        {{ errorMessage }}
      </p>

      <template v-else-if="user">
        <h2>Bienvenue {{ user.username }}</h2>
        <p v-if="user.email">Adresse e-mail : {{ user.email }}</p>
        <p>Votre identité a été validée par Django.</p>
        <p>Rôles : {{ user.roles.join(', ') || 'aucun' }}</p>
      </template>

      <button type="button" @click="logout">
        Se déconnecter
      </button>
    </section>
  </main>
</template>

<style scoped>
main {
  max-width: 700px;
  margin: 80px auto;
  padding: 24px;
  font-family: Arial, sans-serif;
}

section {
  padding: 24px;
  border: 1px solid #d6d6d6;
  border-radius: 8px;
}

button {
  margin-top: 16px;
  padding: 10px 16px;
  cursor: pointer;
}
</style>
