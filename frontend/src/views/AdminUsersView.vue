<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { apiRequest } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { ManagedUser, TrainingSummary, UserRole } from '../types/api'

const auth = useAuthStore()
const users = ref<ManagedUser[]>([])
const trainings = ref<TrainingSummary[]>([])
const search = ref('')
const isLoading = ref(true)
const errorMessage = ref('')
const successMessage = ref('')
const updatingUserId = ref<number | null>(null)
const updatingTrainingUserId = ref<number | null>(null)

const filteredUsers = computed(() => {
  const query = search.value.trim().toLocaleLowerCase('fr')
  if (!query) return users.value

  return users.value.filter((user) =>
    [user.display_name, user.username, user.email]
      .filter(Boolean)
      .some((value) => value?.toLocaleLowerCase('fr').includes(query)),
  )
})

const adminCount = computed(() => users.value.filter((user) => user.role === 'admin').length)

async function loadUsers() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const [loadedUsers, loadedTrainings] = await Promise.all([
      apiRequest<ManagedUser[]>('/api/admin/users/'),
      apiRequest<TrainingSummary[]>('/api/admin/trainings/'),
    ])
    users.value = loadedUsers
    trainings.value = loadedTrainings
  } catch (error) {
    console.error('Échec du chargement des utilisateurs :', error)
    errorMessage.value = 'Impossible de charger les utilisateurs.'
  } finally {
    isLoading.value = false
  }
}

function hasTraining(user: ManagedUser, trainingId: number) {
  return user.assigned_trainings.some((training) => training.id === trainingId)
}

function assignmentLabel(user: ManagedUser) {
  if (user.assigned_trainings.length === 0) return 'Aucune formation'
  if (user.assigned_trainings.length === 1) return user.assigned_trainings[0]?.title
  return `${user.assigned_trainings.length} formations`
}

async function updateTrainingAssignment(
  user: ManagedUser,
  trainingId: number,
  isAssigned: boolean,
) {
  const currentIds = user.assigned_trainings.map((training) => training.id)
  const trainingIds = isAssigned
    ? [...new Set([...currentIds, trainingId])]
    : currentIds.filter((id) => id !== trainingId)

  updatingTrainingUserId.value = user.id
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const updated = await apiRequest<ManagedUser>(`/api/admin/users/${user.id}/trainings/`, {
      method: 'PUT',
      body: JSON.stringify({ training_ids: trainingIds }),
    })
    users.value = users.value.map((item) => (item.id === updated.id ? updated : item))
    successMessage.value = `Les formations de ${updated.display_name || updated.username} ont été mises à jour.`
  } catch (error) {
    console.error("Échec de l'attribution de la formation :", error)
    errorMessage.value = "Impossible de modifier les formations de l'utilisateur."
  } finally {
    updatingTrainingUserId.value = null
  }
}

async function updateRole(user: ManagedUser, role: UserRole) {
  if (role === user.role) return

  updatingUserId.value = user.id
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const updated = await apiRequest<ManagedUser>(`/api/admin/users/${user.id}/role/`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    })

    users.value = users.value.map((item) => (item.id === updated.id ? updated : item))
    successMessage.value = `Le rôle de ${updated.display_name || updated.username} a été mis à jour.`
  } catch (error) {
    console.error('Échec de la mise à jour du rôle :', error)
    errorMessage.value =
      role === 'learner' && adminCount.value === 1
        ? 'Le dernier administrateur ne peut pas devenir apprenant.'
        : "Impossible de modifier le rôle de l'utilisateur."
  } finally {
    updatingUserId.value = null
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}

onMounted(() => {
  void loadUsers()
})
</script>

<template>
  <section>
    <div class="page-heading page-heading--compact">
      <div>
        <p class="eyebrow">Administration</p>
        <h1>Utilisateurs</h1>
        <p class="page-heading__intro">
          Gérez les accès et attribuez les formations à chaque utilisateur.
        </p>
      </div>
      <div class="user-total">
        <strong>{{ users.length }}</strong>
        <span>comptes actifs</span>
      </div>
    </div>

    <div class="users-panel">
      <div class="users-toolbar">
        <label class="search-field">
          <span class="sr-only">Rechercher un utilisateur</span>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="7"></circle>
            <path d="m20 20-4-4"></path>
          </svg>
          <input v-model="search" type="search" placeholder="Rechercher un utilisateur…" />
        </label>
        <span class="users-toolbar__hint">
          Le premier compte inscrit est administrateur par défaut.
        </span>
      </div>

      <p v-if="successMessage" class="feedback feedback--success" role="status">
        {{ successMessage }}
      </p>
      <p v-if="errorMessage" class="feedback feedback--error" role="alert">
        {{ errorMessage }}
      </p>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Utilisateur</th>
              <th>Inscription</th>
              <th>Rôle</th>
              <th>Formations</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isLoading">
              <td colspan="4" class="table-state">Chargement des utilisateurs…</td>
            </tr>
            <tr v-else-if="filteredUsers.length === 0">
              <td colspan="4" class="table-state">Aucun utilisateur trouvé.</td>
            </tr>
            <tr v-for="user in filteredUsers" v-else :key="user.id">
              <td>
                <div class="user-cell">
                  <span class="user-cell__avatar">
                    {{ (user.display_name || user.username).slice(0, 1).toUpperCase() }}
                  </span>
                  <div>
                    <strong>
                      {{ user.display_name || user.username }}
                      <small v-if="user.id === auth.user?.id">Vous</small>
                    </strong>
                    <span>{{ user.email || `@${user.username}` }}</span>
                  </div>
                </div>
              </td>
              <td>{{ formatDate(user.created_at) }}</td>
              <td>
                <label class="role-select" :class="`role-select--${user.role}`">
                  <span class="sr-only">Rôle de {{ user.username }}</span>
                  <select
                    :value="user.role"
                    :disabled="updatingUserId === user.id"
                    @change="
                      updateRole(user, ($event.target as HTMLSelectElement).value as UserRole)
                    "
                  >
                    <option value="admin">Administrateur</option>
                    <option value="learner">Apprenant</option>
                  </select>
                </label>
              </td>
              <td>
                <details class="training-assignment">
                  <summary>
                    <span>{{ assignmentLabel(user) }}</span>
                    <small v-if="updatingTrainingUserId === user.id">Enregistrement…</small>
                  </summary>
                  <div class="training-assignment__panel">
                    <p v-if="trainings.length === 0">Aucune formation disponible.</p>
                    <label v-for="training in trainings" v-else :key="training.id">
                      <input
                        type="checkbox"
                        :checked="hasTraining(user, training.id)"
                        :disabled="updatingTrainingUserId === user.id"
                        @change="
                          updateTrainingAssignment(
                            user,
                            training.id,
                            ($event.target as HTMLInputElement).checked,
                          )
                        "
                      />
                      <span>
                        <strong>{{ training.title }}</strong>
                        <small>{{ training.status_label }}</small>
                      </span>
                    </label>
                  </div>
                </details>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
