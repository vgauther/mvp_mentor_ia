import keycloak from '../auth/keycloak'

export function resolveApiUrl(path: string): string {
  return import.meta.env.VITE_API_URL + path
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  await keycloak.updateToken(30)

  if (!keycloak.token) {
    throw new Error('Aucun jeton Keycloak disponible.')
  }

  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${keycloak.token}`)

  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(resolveApiUrl(path), {
    ...options,
    headers,
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null)
    const error = new Error(`Réponse Django : ${response.status}`)
    Object.assign(error, { status: response.status, body: errorBody })
    throw error
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export async function downloadApiFile(path: string, filename: string): Promise<void> {
  await keycloak.updateToken(30)

  if (!keycloak.token) {
    throw new Error('Aucun jeton Keycloak disponible.')
  }

  const response = await fetch(resolveApiUrl(path), {
    headers: { Authorization: `Bearer ${keycloak.token}` },
  })

  if (!response.ok) {
    throw new Error(`Téléchargement impossible : ${response.status}`)
  }

  const blobUrl = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(blobUrl)
}
