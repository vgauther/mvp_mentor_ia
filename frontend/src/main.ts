import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import './assets/main.css'
import keycloak from './auth/keycloak'
import { createAppRouter } from './router'
import { useAuthStore } from './stores/auth'

async function bootstrap() {
  try {
    await keycloak.init({
      onLoad: 'login-required',
      pkceMethod: 'S256',
      checkLoginIframe: false,
    })

    const pinia = createPinia()
    const auth = useAuthStore(pinia)
    await auth.loadUser()

    const router = createAppRouter(pinia)
    const app = createApp(App)

    app.use(pinia)
    app.use(router)
    await router.isReady()
    app.mount('#app')
  } catch (error) {
    console.error("Échec de l'initialisation de Mentor IA :", error)

    const root = document.querySelector<HTMLDivElement>('#app')
    if (root) {
      root.innerHTML = `
        <main class="startup-error">
          <p class="eyebrow">Mentor IA</p>
          <h1>Impossible d'ouvrir votre espace</h1>
          <p>Vérifiez que Keycloak et l'API Django sont disponibles, puis rechargez la page.</p>
          <button type="button" onclick="window.location.reload()">Réessayer</button>
        </main>
      `
    }
  }
}

void bootstrap()
