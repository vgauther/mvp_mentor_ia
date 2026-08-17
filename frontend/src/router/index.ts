import type { Pinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'

export function createAppRouter(pinia: Pinia) {
  const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
      {
        path: '/',
        name: 'home',
        component: () => import('../views/LearnerHomeView.vue'),
      },
      {
        path: '/admin',
        name: 'admin-home',
        component: () => import('../views/AdminHomeView.vue'),
        meta: { role: 'admin' },
      },
      {
        path: '/admin/users',
        name: 'admin-users',
        component: () => import('../views/AdminUsersView.vue'),
        meta: { role: 'admin' },
      },
      {
        path: '/admin/trainings',
        name: 'admin-trainings',
        component: () => import('../views/AdminTrainingsView.vue'),
        meta: { role: 'admin' },
      },
      {
        path: '/admin/trainings/:trainingId',
        name: 'admin-training-detail',
        component: () => import('../views/AdminTrainingDetailView.vue'),
        meta: { role: 'admin' },
      },
      {
        path: '/learner',
        name: 'learner-home',
        component: () => import('../views/LearnerHomeView.vue'),
        meta: { role: 'learner' },
      },
      {
        path: '/:pathMatch(.*)*',
        redirect: '/',
      },
    ],
  })

  router.beforeEach((to) => {
    const auth = useAuthStore(pinia)

    if (to.path === '/') {
      return auth.homePath
    }

    const requiredRole = to.meta.role
    if (requiredRole && auth.user?.role !== requiredRole) {
      return auth.homePath
    }

    return true
  })

  return router
}
