<script setup lang="ts">
import keycloak from './auth/keycloak'

const username = keycloak.tokenParsed?.preferred_username ?? 'Utilisateur'
const email = keycloak.tokenParsed?.email

async function logout() {
  await keycloak.logout({
    redirectUri: window.location.origin,
  })
}
</script>

<template>
  <main>
    <h1>Le Bon Prénom</h1>

    <section>
      <h2>Bienvenue {{ username }}</h2>
      <p v-if="email">Adresse e-mail : {{ email }}</p>
      <p>Vous êtes connecté avec Keycloak.</p>

      <button type="button" @click="logout">Se déconnecter</button>
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
