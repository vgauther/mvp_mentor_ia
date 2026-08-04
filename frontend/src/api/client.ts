import keycloak from '../auth/keycloak'

export async function authenticatedFetch(path: string, options: RequestInit = {}) {
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

export async function getErrorMessage(response: Response, fallbackMessage: string) {
  try {
    const data = (await response.json()) as Record<string, unknown>

    if (typeof data.detail === 'string') {
      return data.detail
    }

    for (const value of Object.values(data)) {
      if (typeof value === 'string') {
        return value
      }

      if (Array.isArray(value) && typeof value[0] === 'string') {
        return value[0]
      }
    }

    return fallbackMessage
  } catch {
    return fallbackMessage
  }
}
