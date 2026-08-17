import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminTrainingDetailView from '../views/AdminTrainingDetailView.vue'
import type { TrainingDetail } from '../types/api'

const { apiRequestMock, replaceMock } = vi.hoisted(() => ({
  apiRequestMock: vi.fn<(url: string, options?: RequestInit) => Promise<unknown>>(),
  replaceMock: vi.fn<(path: string) => void>(),
}))

vi.mock('../api/client', () => ({
  apiRequest: apiRequestMock,
  downloadApiFile: vi.fn<() => Promise<void>>(),
  resolveApiUrl: (path: string) => 'http://api.test' + path,
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { trainingId: '7' } }),
  useRouter: () => ({ replace: replaceMock }),
}))

const training: TrainingDetail = {
  id: 7,
  title: 'Fondamentaux des marchés des changes',
  description: 'Formation de test',
  status: 'draft',
  status_label: 'Brouillon',
  created_by_name: 'Victor',
  objective_count: 1,
  unit_count: 0,
  raw_material_count: 1,
  created_at: '2026-08-14T08:00:00Z',
  updated_at: '2026-08-14T08:00:00Z',
  enrichment_ai_configured: true,
  structure_generation: null,
  objectives: [
    {
      id: 11,
      title: 'Comprendre les mécanismes des marchés de change',
      description: '',
      position: 1,
      created_at: '2026-08-14T08:00:00Z',
      updated_at: '2026-08-14T08:00:00Z',
    },
  ],
  units: [],
  raw_materials: [
    {
      id: 21,
      kind: 'text',
      kind_label: 'Texte',
      display_name: 'Notes de cours',
      content: 'Notes de cours',
      quiz_data: { title: '', questions: [] },
      has_file: false,
      download_url: null,
      original_filename: '',
      mime_type: '',
      size: 14,
      created_at: '2026-08-14T08:00:00Z',
      enrichment: null,
    },
  ],
}

beforeEach(() => {
  apiRequestMock.mockReset()
  apiRequestMock.mockResolvedValue(training)
  replaceMock.mockReset()
})

describe('AdminTrainingDetailView', () => {
  it('présente les objectifs, les données brutes, l’enrichissement puis la structure IA', async () => {
    const wrapper = mount(AdminTrainingDetailView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })

    await flushPromises()

    const tabs = wrapper.findAll('[data-test^="training-tab-"]')
    expect(tabs.map((tab) => tab.text())).toEqual([
      '1 Objectifs pédagogiques',
      '2 Sources et quiz',
      '3 Enrichissement',
      '4 Structure IA',
    ])

    await wrapper.get('[data-test="training-tab-enrichment"]').trigger('click')
    expect(wrapper.text()).toContain('Enrichissement des ressources')
    expect(wrapper.text()).toContain('Cette ressource est intacte')

    await wrapper.get('[data-test="training-tab-generation"]').trigger('click')

    expect(wrapper.text()).toContain('Génération de la structure par IA')
    expect(wrapper.text()).toContain('1 objectif disponible')
    expect(wrapper.text()).toContain('1 source disponible pour l’enrichissement')
    expect(wrapper.text()).toContain('0 ressource enrichie sur 1')
    expect(wrapper.text()).not.toContain('Élément de structure')
  })

  it('lance l’enrichissement de toutes les ressources depuis un seul bouton', async () => {
    apiRequestMock.mockImplementation((url, options) => {
      if (url.endsWith('/enrichments/generate/') && options?.method === 'POST') {
        return Promise.resolve({ queued: 1, total: 1 })
      }
      return Promise.resolve(training)
    })
    const wrapper = mount(AdminTrainingDetailView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })

    await flushPromises()
    await wrapper.get('[data-test="training-tab-enrichment"]').trigger('click')
    await wrapper.get('[data-test="generate-enrichment-button"]').trigger('click')
    await flushPromises()

    expect(apiRequestMock).toHaveBeenCalledWith(
      '/api/admin/trainings/7/enrichments/generate/',
      {
        method: 'POST',
        body: JSON.stringify({ force: false }),
      },
    )
    expect(wrapper.text()).toContain('1 ressource placée dans la file d’enrichissement')
  })

  it("affiche un bouton de génération inactif sans lancer d'appel API", async () => {
    const wrapper = mount(AdminTrainingDetailView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })

    await flushPromises()
    await wrapper.get('[data-test="training-tab-generation"]').trigger('click')

    const generationButton = wrapper.get('[data-test="generate-course-button"]')
    expect(generationButton.attributes('disabled')).toBeDefined()
    expect(apiRequestMock).toHaveBeenCalledTimes(1)
    expect(apiRequestMock).toHaveBeenCalledWith('/api/admin/trainings/7/')
  })

  it('active la génération lorsque les objectifs et les enrichissements sont prêts', async () => {
    const readyTraining: TrainingDetail = {
      ...training,
      raw_materials: [
        {
          ...training.raw_materials[0]!,
          enrichment: {
            status: 'ready',
            status_label: 'Prête',
            progress_message: 'Enrichissement terminé',
            transcript: '',
            extracted_text: 'Notes de cours',
            media_purpose: 'Expliquer les fondamentaux',
            summary: 'Résumé fidèle',
            language: 'fr',
            key_concepts: [{ name: 'Change', explanation: 'Échange de devises' }],
            glossary: [],
            keywords: ['change'],
            ai_model: 'gpt-5.6',
            error_message: '',
            started_at: '2026-08-14T08:00:00Z',
            generated_at: '2026-08-14T08:01:00Z',
            updated_at: '2026-08-14T08:01:00Z',
          },
        },
      ],
    }
    apiRequestMock.mockImplementation((url, options) => {
      if (url.endsWith('/structure/generate/') && options?.method === 'POST') {
        return Promise.resolve({ status: 'queued' })
      }
      return Promise.resolve(readyTraining)
    })
    const wrapper = mount(AdminTrainingDetailView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })

    await flushPromises()
    await wrapper.get('[data-test="training-tab-generation"]').trigger('click')
    const button = wrapper.get('[data-test="generate-course-button"]')
    expect(button.attributes('disabled')).toBeUndefined()
    await button.trigger('click')
    await flushPromises()

    expect(apiRequestMock).toHaveBeenCalledWith(
      '/api/admin/trainings/7/structure/generate/',
      {
        method: 'POST',
        body: JSON.stringify({ force: false }),
      },
    )
    expect(wrapper.text()).toContain('La génération de la structure a démarré')
  })

  it('affiche une proposition structurée et ses ressources', async () => {
    const generatedTraining: TrainingDetail = {
      ...training,
      structure_generation: {
        status: 'ready',
        status_label: 'Proposition prête',
        progress_message: 'Proposition prête à être examinée',
        structure: {
          title: 'Parcours marché des changes',
          introduction: 'Une progression fondée sur les ressources enrichies disponibles.',
          unsupported_objective_ids: [],
          modules: [
            {
              title: 'Fondamentaux',
              rationale: 'Installer les bases avant la mise en application.',
              chapters: [
                {
                  title: 'Comprendre le marché',
                  rationale: 'Présenter les notions indispensables.',
                  sections: [
                    {
                      title: 'Mécanismes essentiels',
                      rationale: 'La ressource explique directement les mécanismes.',
                      objective_ids: [11],
                      resource_ids: [21],
                    },
                  ],
                },
              ],
            },
          ],
        },
        ai_model: 'gpt-5.6',
        error_message: '',
        started_at: '2026-08-14T08:00:00Z',
        generated_at: '2026-08-14T08:01:00Z',
        published_at: null,
        published_by_name: '',
        updated_at: '2026-08-14T08:01:00Z',
      },
    }
    apiRequestMock.mockResolvedValue(generatedTraining)
    const wrapper = mount(AdminTrainingDetailView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })

    await flushPromises()
    await wrapper.get('[data-test="training-tab-generation"]').trigger('click')

    expect(wrapper.text()).toContain('Parcours marché des changes')
    expect(wrapper.text()).toContain('Fondamentaux')
    expect(wrapper.text()).toContain('Mécanismes essentiels')
    expect(wrapper.text()).toContain('Notes de cours')
    expect(wrapper.get('[data-test="publish-structure-button"]').attributes('disabled')).toBeUndefined()
  })

  it('valide et publie une proposition après confirmation', async () => {
    const generatedTraining: TrainingDetail = {
      ...training,
      status: 'structuring',
      status_label: 'En structuration',
      structure_generation: {
        status: 'ready',
        status_label: 'Proposition prête',
        progress_message: 'Proposition prête à être examinée',
        structure: {
          title: 'Parcours marché des changes',
          introduction: 'Une progression fondée sur les ressources enrichies disponibles.',
          unsupported_objective_ids: [],
          modules: [
            {
              title: 'Fondamentaux',
              rationale: 'Installer les bases avant la mise en application.',
              chapters: [
                {
                  title: 'Comprendre le marché',
                  rationale: 'Présenter les notions indispensables.',
                  sections: [
                    {
                      title: 'Mécanismes essentiels',
                      rationale: 'La ressource explique directement les mécanismes.',
                      objective_ids: [11],
                      resource_ids: [21],
                    },
                  ],
                },
              ],
            },
          ],
        },
        ai_model: 'gpt-5.6',
        error_message: '',
        started_at: '2026-08-14T08:00:00Z',
        generated_at: '2026-08-14T08:01:00Z',
        published_at: null,
        published_by_name: '',
        updated_at: '2026-08-14T08:01:00Z',
      },
    }
    const publishedTraining: TrainingDetail = {
      ...generatedTraining,
      status: 'ready',
      status_label: 'Prête',
      structure_generation: {
        ...generatedTraining.structure_generation!,
        progress_message: 'Structure validée et publiée',
        published_at: '2026-08-14T08:02:00Z',
        published_by_name: 'Victor',
      },
    }
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    apiRequestMock.mockImplementation((url, options) => {
      if (url.endsWith('/structure/publish/') && options?.method === 'POST') {
        return Promise.resolve(publishedTraining)
      }
      return Promise.resolve(generatedTraining)
    })
    const wrapper = mount(AdminTrainingDetailView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })

    await flushPromises()
    await wrapper.get('[data-test="training-tab-generation"]').trigger('click')
    await wrapper.get('[data-test="publish-structure-button"]').trigger('click')
    await flushPromises()

    expect(apiRequestMock).toHaveBeenCalledWith(
      '/api/admin/trainings/7/structure/publish/',
      { method: 'POST' },
    )
    expect(wrapper.text()).toContain('La structure a été validée et publiée')
    expect(wrapper.text()).toContain('Structure publiée')
  })

  it('crée un quiz avec des questions et réponses structurées', async () => {
    const wrapper = mount(AdminTrainingDetailView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })

    await flushPromises()
    await wrapper.get('[data-test="training-tab-raw-materials"]').trigger('click')
    await wrapper.get('select').setValue('quiz')

    expect(wrapper.find('[data-test="quiz-builder"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Questions et réponses brutes')

    await wrapper
      .get('textarea[placeholder="Saisissez la question"]')
      .setValue('Quel est le spot ?')
    await wrapper.get('input[aria-label="Choix 1"]').setValue('1,10')
    await wrapper.get('input[aria-label="Choix 2"]').setValue('1,20')
    await wrapper.get('input[aria-label="Bonne réponse 1"]').setValue(true)
    await wrapper.get('form.workspace-aside').trigger('submit')
    await flushPromises()

    const createCall = apiRequestMock.mock.calls.find(
      ([url, options]) =>
        url === '/api/admin/trainings/7/raw-materials/' && options?.method === 'POST',
    )
    expect(createCall).toBeDefined()
    expect(JSON.parse(createCall?.[1]?.body as string)).toEqual({
      kind: 'quiz',
      quiz_data: {
        title: '',
        questions: [
          {
            type: 'single_choice',
            prompt: 'Quel est le spot ?',
            options: [
              { text: '1,10', is_correct: true },
              { text: '1,20', is_correct: false },
            ],
          },
        ],
      },
    })
  })

  it('permet de consulter les textes, quiz, PDF et vidéos', async () => {
    const previewTraining: TrainingDetail = {
      ...training,
      raw_material_count: 4,
      raw_materials: [
        training.raw_materials[0]!,
        {
          id: 22,
          kind: 'quiz',
          kind_label: 'Quiz',
          display_name: 'Quiz · 1 question',
          content: '',
          quiz_data: {
            title: '',
            questions: [
              {
                type: 'short_text',
                prompt: 'Quel est le taux spot ?',
                accepted_answers: ['1,10'],
              },
            ],
          },
          has_file: false,
          download_url: null,
          original_filename: '',
          mime_type: '',
          size: 120,
          created_at: '2026-08-14T08:00:00Z',
          enrichment: null,
        },
        {
          id: 23,
          kind: 'pdf',
          kind_label: 'PDF',
          display_name: 'support.pdf',
          content: '',
          quiz_data: { title: '', questions: [] },
          has_file: true,
          download_url: '/api/download/23/',
          original_filename: 'support.pdf',
          mime_type: 'application/pdf',
          size: 200,
          created_at: '2026-08-14T08:00:00Z',
          enrichment: null,
        },
        {
          id: 24,
          kind: 'video',
          kind_label: 'Vidéo',
          display_name: 'video.mp4',
          content: '',
          quiz_data: { title: '', questions: [] },
          has_file: true,
          download_url: '/api/download/24/',
          original_filename: 'video.mp4',
          mime_type: 'video/mp4',
          size: 300,
          created_at: '2026-08-14T08:00:00Z',
          enrichment: null,
        },
      ],
    }
    apiRequestMock.mockImplementation((url) => {
      if (url.endsWith('/preview-token/')) {
        return Promise.resolve({ url: '/api/raw-material-previews/token/' })
      }
      return Promise.resolve(previewTraining)
    })

    const wrapper = mount(AdminTrainingDetailView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
          Teleport: true,
        },
      },
    })
    await flushPromises()
    await wrapper.get('[data-test="training-tab-raw-materials"]').trigger('click')

    const card = (name: string) =>
      wrapper.findAll('.material-card').find((material) => material.text().includes(name))!

    await card('Notes de cours').trigger('click')
    expect(wrapper.get('.resource-preview__text').text()).toBe('Notes de cours')
    await wrapper.get('[aria-label="Fermer la prévisualisation"]').trigger('click')

    await card('Quiz · 1 question').trigger('click')
    expect(wrapper.get('.quiz-preview').text()).toContain('Quel est le taux spot ?')
    expect(wrapper.get('.quiz-preview').text()).toContain('1,10')
    await wrapper.get('[aria-label="Fermer la prévisualisation"]').trigger('click')

    await card('support.pdf').trigger('click')
    await flushPromises()
    expect(wrapper.get('.resource-preview__pdf').attributes('src')).toBe(
      'http://api.test/api/raw-material-previews/token/',
    )
    await wrapper.get('[aria-label="Fermer la prévisualisation"]').trigger('click')

    await card('video.mp4').trigger('click')
    await flushPromises()
    expect(wrapper.get('.resource-preview__video').attributes('src')).toBe(
      'http://api.test/api/raw-material-previews/token/',
    )
    await wrapper.get('[aria-label="Fermer la prévisualisation"]').trigger('click')
  })
})
