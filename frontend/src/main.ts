import { createApp, type Component } from 'vue'
import { createPinia } from 'pinia'

import keycloak from './auth/keycloak'

async function bootstrap() {
  try {
    const isAuthenticated = await keycloak.init({
      onLoad: 'check-sso',
      pkceMethod: 'S256',
      checkLoginIframe: false,
    })

    const { default: router } = await import('./router')

    const rootComponent: Component = isAuthenticated
      ? (await import('./App.vue')).default
      : (await import('./PublicHome.vue')).default

    const app = createApp(rootComponent)

    app.use(createPinia())
    app.use(router)

    app.mount('#app')
  } catch (error) {
    console.error("Échec de l'initialisation de Keycloak :", error)
  }
}

void bootstrap()
