import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import keycloak from './auth/keycloak'

async function bootstrap() {
  try {
    await keycloak.init({
      onLoad: 'login-required',
      pkceMethod: 'S256',
    })

    const { default: router } = await import('./router')

    const app = createApp(App)

    app.use(createPinia())
    app.use(router)

    app.mount('#app')
  } catch (error) {
    console.error("Échec de l'initialisation de Keycloak :", error)
  }
}

void bootstrap()
