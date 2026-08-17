<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { apiRequest, downloadApiFile, resolveApiUrl } from '../api/client'
import type {
  GeneratedCourseStructure,
  LearningObjective,
  QuizData,
  QuizOption,
  QuizQuestion,
  QuizQuestionType,
  RawMaterial,
  RawMaterialKind,
  TrainingDetail,
} from '../types/api'

type DetailTab = 'objectives' | 'raw-materials' | 'enrichment' | 'generation'

interface QuizQuestionDraft {
  type: QuizQuestionType
  prompt: string
  options: QuizOption[]
  accepted_answers: string[]
}

const vFocus = {
  mounted(element: HTMLInputElement) {
    element.focus()
    element.select()
  },
}

const route = useRoute()
const router = useRouter()
const trainingId = Number(route.params.trainingId)
const training = ref<TrainingDetail | null>(null)
const isLoading = ref(true)
const isSaving = ref(false)
const isPublishing = ref(false)
const isTitleSaving = ref(false)
const isEditingTitle = ref(false)
const titleDraft = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const activeTab = ref<DetailTab>('objectives')

const objectiveTitle = ref('')
const objectiveDescription = ref('')

const materialKind = ref<RawMaterialKind>('pdf')
const materialContent = ref('')
const selectedFile = ref<File | null>(null)
const fileInputKey = ref(0)
const editingQuizId = ref<number | null>(null)
const quizTitle = ref('')
const quizQuestions = ref<QuizQuestionDraft[]>([createQuizQuestion()])
const previewMaterial = ref<RawMaterial | null>(null)
const previewUrl = ref('')
const isPreviewLoading = ref(false)
const previewError = ref('')
const enrichmentPoll = ref<number | null>(null)
const structurePoll = ref<number | null>(null)

const objectives = computed(() => training.value?.objectives ?? [])
const units = computed(() => training.value?.units ?? [])
const rawMaterials = computed(() => training.value?.raw_materials ?? [])
const enrichedMaterials = computed(
  () => rawMaterials.value.filter((material) => material.enrichment?.status === 'ready').length,
)
const enrichmentErrors = computed(
  () => rawMaterials.value.filter((material) => material.enrichment?.status === 'error').length,
)
const enrichmentInProgress = computed(() =>
  rawMaterials.value.some((material) =>
    ['queued', 'processing'].includes(material.enrichment?.status ?? ''),
  ),
)
const enrichmentProgress = computed(() =>
  rawMaterials.value.length === 0
    ? 0
    : Math.round((enrichedMaterials.value / rawMaterials.value.length) * 100),
)
const allMaterialsEnriched = computed(
  () => rawMaterials.value.length > 0 && enrichedMaterials.value === rawMaterials.value.length,
)
const structureGeneration = computed(() => training.value?.structure_generation ?? null)
const structureGenerationInProgress = computed(() =>
  ['queued', 'processing'].includes(structureGeneration.value?.status ?? ''),
)
const generatedStructure = computed(() => {
  const generation = structureGeneration.value
  if (generation?.status !== 'ready' || !('modules' in generation.structure)) return null
  return generation.structure as GeneratedCourseStructure
})
const isStructurePublished = computed(
  () => training.value?.status === 'ready' && Boolean(structureGeneration.value?.published_at),
)
const canPublishStructure = computed(
  () => Boolean(generatedStructure.value) && !structureGenerationInProgress.value && !isStructurePublished.value,
)
const canGenerateStructure = computed(
  () =>
    Boolean(training.value?.enrichment_ai_configured) &&
    objectives.value.length > 0 &&
    allMaterialsEnriched.value &&
    !structureGenerationInProgress.value,
)
const needsFile = computed(() => ['video', 'pdf'].includes(materialKind.value))
const isQuiz = computed(() => materialKind.value === 'quiz')
const acceptedFileTypes = computed(() =>
  materialKind.value === 'pdf' ? 'application/pdf,.pdf' : 'video/*',
)
const quizIsValid = computed(
  () => quizQuestions.value.length > 0 && quizQuestions.value.every(isQuizQuestionValid),
)

watch(materialKind, () => {
  selectedFile.value = null
  materialContent.value = ''
  fileInputKey.value += 1
  if (materialKind.value !== 'quiz') resetQuizDraft()
})

function createQuizQuestion(type: QuizQuestionType = 'single_choice'): QuizQuestionDraft {
  return {
    type,
    prompt: '',
    options:
      type === 'short_text'
        ? []
        : [
            { text: '', is_correct: false },
            { text: '', is_correct: false },
          ],
    accepted_answers: type === 'short_text' ? [''] : [],
  }
}

function isQuizQuestionValid(question: QuizQuestionDraft) {
  if (!question.prompt.trim()) return false
  if (question.type === 'short_text') {
    return question.accepted_answers.some((answer) => answer.trim())
  }
  if (question.options.length < 2 || question.options.some((option) => !option.text.trim())) {
    return false
  }
  const correctCount = question.options.filter((option) => option.is_correct).length
  return question.type === 'single_choice' ? correctCount === 1 : correctCount >= 1
}

function resetQuizDraft() {
  editingQuizId.value = null
  quizTitle.value = ''
  quizQuestions.value = [createQuizQuestion()]
}

function addQuizQuestion() {
  quizQuestions.value.push(createQuizQuestion())
}

function removeQuizQuestion(index: number) {
  if (quizQuestions.value.length === 1) return
  quizQuestions.value.splice(index, 1)
}

function changeQuizQuestionType(question: QuizQuestionDraft) {
  if (question.type === 'short_text') {
    question.options = []
    question.accepted_answers = ['']
    return
  }
  question.accepted_answers = []
  question.options = [
    { text: '', is_correct: false },
    { text: '', is_correct: false },
  ]
}

function addQuizOption(question: QuizQuestionDraft) {
  question.options.push({ text: '', is_correct: false })
}

function removeQuizOption(question: QuizQuestionDraft, index: number) {
  if (question.options.length === 2) return
  question.options.splice(index, 1)
}

function selectSingleCorrectOption(question: QuizQuestionDraft, selectedIndex: number) {
  question.options.forEach((option, index) => {
    option.is_correct = index === selectedIndex
  })
}

function addAcceptedAnswer(question: QuizQuestionDraft) {
  question.accepted_answers.push('')
}

function removeAcceptedAnswer(question: QuizQuestionDraft, index: number) {
  if (question.accepted_answers.length === 1) return
  question.accepted_answers.splice(index, 1)
}

function serializeQuiz(): QuizData {
  const questions: QuizQuestion[] = quizQuestions.value.map((question) => {
    if (question.type === 'short_text') {
      return {
        type: question.type,
        prompt: question.prompt.trim(),
        accepted_answers: question.accepted_answers.map((answer) => answer.trim()).filter(Boolean),
      }
    }
    return {
      type: question.type,
      prompt: question.prompt.trim(),
      options: question.options.map((option) => ({
        text: option.text.trim(),
        is_correct: option.is_correct,
      })),
    }
  })
  return { title: quizTitle.value.trim(), questions }
}

function editQuiz(material: RawMaterial) {
  materialKind.value = 'quiz'
  editingQuizId.value = material.id
  quizTitle.value = material.quiz_data.title
  quizQuestions.value = material.quiz_data.questions.map((question) => ({
    type: question.type,
    prompt: question.prompt,
    options: (question.options ?? []).map((option) => ({ ...option })),
    accepted_answers: [...(question.accepted_answers ?? [])],
  }))
}

function quizQuestionCount(material: RawMaterial) {
  return material.quiz_data.questions.length
}

async function loadTraining(showLoading = true) {
  if (showLoading) isLoading.value = true
  errorMessage.value = ''
  try {
    training.value = await apiRequest<TrainingDetail>(`/api/admin/trainings/${trainingId}/`)
  } catch (error) {
    console.error('Échec du chargement de la formation :', error)
    errorMessage.value = 'Cette formation est introuvable ou inaccessible.'
  } finally {
    if (showLoading) isLoading.value = false
  }
}

function startTitleEditing() {
  if (!training.value) return
  titleDraft.value = training.value.title
  isEditingTitle.value = true
}

function cancelTitleEditing() {
  isEditingTitle.value = false
  titleDraft.value = ''
}

async function saveTrainingTitle() {
  const title = titleDraft.value.trim()
  if (!training.value || !title) return
  if (title === training.value.title) {
    cancelTitleEditing()
    return
  }

  isTitleSaving.value = true
  resetFeedback()
  try {
    training.value = await apiRequest<TrainingDetail>(`/api/admin/trainings/${trainingId}/`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    })
    isEditingTitle.value = false
    titleDraft.value = ''
    successMessage.value = 'Titre de la formation mis à jour.'
  } catch (error) {
    console.error('Échec de la modification du titre :', error)
    errorMessage.value = 'Impossible de modifier le titre de la formation.'
  } finally {
    isTitleSaving.value = false
  }
}

function stopEnrichmentPolling() {
  if (enrichmentPoll.value) window.clearInterval(enrichmentPoll.value)
  enrichmentPoll.value = null
}

function startEnrichmentPolling() {
  stopEnrichmentPolling()
  enrichmentPoll.value = window.setInterval(async () => {
    await loadTraining(false)
    if (!enrichmentInProgress.value) stopEnrichmentPolling()
  }, 3000)
}

function stopStructurePolling() {
  if (structurePoll.value) window.clearInterval(structurePoll.value)
  structurePoll.value = null
}

function startStructurePolling() {
  stopStructurePolling()
  structurePoll.value = window.setInterval(async () => {
    await loadTraining(false)
    if (!structureGenerationInProgress.value) stopStructurePolling()
  }, 3000)
}

async function generateEnrichments() {
  if (!training.value?.enrichment_ai_configured || rawMaterials.value.length === 0) return
  const force = allMaterialsEnriched.value
  if (force && !window.confirm('Relancer l’enrichissement de toutes les ressources ?')) return

  isSaving.value = true
  resetFeedback()
  try {
    const response = await apiRequest<{ queued: number; total: number }>(
      `/api/admin/trainings/${trainingId}/enrichments/generate/`,
      {
        method: 'POST',
        body: JSON.stringify({ force }),
      },
    )
    successMessage.value = `${response.queued} ressource${response.queued > 1 ? 's' : ''} placée${response.queued > 1 ? 's' : ''} dans la file d’enrichissement.`
    await loadTraining(false)
    if (response.queued > 0 && enrichmentInProgress.value) startEnrichmentPolling()
  } catch (error) {
    console.error('Échec du lancement de l’enrichissement :', error)
    const detail = (error as { body?: { detail?: string } }).body?.detail
    errorMessage.value = detail || 'Impossible de lancer l’enrichissement.'
  } finally {
    isSaving.value = false
  }
}

async function generateStructure() {
  if (!canGenerateStructure.value) return
  const force = structureGeneration.value?.status === 'ready'
  if (force && !window.confirm('Remplacer la proposition de structure actuelle ?')) return

  isSaving.value = true
  resetFeedback()
  try {
    await apiRequest<{ status: string }>(
      `/api/admin/trainings/${trainingId}/structure/generate/`,
      {
        method: 'POST',
        body: JSON.stringify({ force }),
      },
    )
    successMessage.value = 'La génération de la structure a démarré.'
    await loadTraining(false)
    if (structureGenerationInProgress.value) startStructurePolling()
  } catch (error) {
    console.error('Échec de la génération de structure :', error)
    const detail = (error as { body?: { detail?: string } }).body?.detail
    errorMessage.value = detail || 'Impossible de générer la structure.'
  } finally {
    isSaving.value = false
  }
}

async function publishStructure() {
  if (!canPublishStructure.value) return
  if (
    !window.confirm(
      'Valider cette proposition et la publier comme structure de la formation ?',
    )
  ) {
    return
  }

  isPublishing.value = true
  resetFeedback()
  try {
    training.value = await apiRequest<TrainingDetail>(
      `/api/admin/trainings/${trainingId}/structure/publish/`,
      { method: 'POST' },
    )
    successMessage.value = 'La structure a été validée et publiée.'
  } catch (error) {
    console.error('Échec de la publication de la structure :', error)
    const detail = (error as { body?: { detail?: string } }).body?.detail
    errorMessage.value = detail || 'Impossible de valider et publier cette structure.'
  } finally {
    isPublishing.value = false
  }
}

function resetFeedback() {
  errorMessage.value = ''
  successMessage.value = ''
}

async function addObjective() {
  if (!objectiveTitle.value.trim()) return
  isSaving.value = true
  resetFeedback()
  try {
    await apiRequest<LearningObjective>(`/api/admin/trainings/${trainingId}/objectives/`, {
      method: 'POST',
      body: JSON.stringify({
        title: objectiveTitle.value.trim(),
        description: objectiveDescription.value.trim(),
      }),
    })
    objectiveTitle.value = ''
    objectiveDescription.value = ''
    successMessage.value = 'Objectif pédagogique ajouté.'
    await loadTraining()
  } catch (error) {
    console.error('Échec de la création de l’objectif :', error)
    errorMessage.value = 'Impossible d’ajouter cet objectif.'
  } finally {
    isSaving.value = false
  }
}

async function deleteObjective(objective: LearningObjective) {
  if (!window.confirm(`Supprimer l’objectif « ${objective.title} » ?`)) return
  resetFeedback()
  try {
    await apiRequest<void>(`/api/admin/trainings/${trainingId}/objectives/${objective.id}/`, {
      method: 'DELETE',
    })
    successMessage.value = 'Objectif supprimé.'
    await loadTraining()
  } catch (error) {
    console.error('Échec de la suppression de l’objectif :', error)
    errorMessage.value = 'Impossible de supprimer cet objectif.'
  }
}

function handleFileSelection(event: Event) {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function addRawMaterial() {
  if (needsFile.value && !selectedFile.value) return
  if (materialKind.value === 'text' && !materialContent.value.trim()) return
  if (isQuiz.value && !quizIsValid.value) return

  isSaving.value = true
  resetFeedback()
  try {
    if (isQuiz.value) {
      const quizId = editingQuizId.value
      await apiRequest<RawMaterial>(
        quizId
          ? `/api/admin/trainings/${trainingId}/raw-materials/${quizId}/`
          : `/api/admin/trainings/${trainingId}/raw-materials/`,
        {
          method: quizId ? 'PATCH' : 'POST',
          body: JSON.stringify({ kind: 'quiz', quiz_data: serializeQuiz() }),
        },
      )
      successMessage.value = quizId ? 'Quiz structuré mis à jour.' : 'Quiz structuré créé.'
      resetQuizDraft()
      await loadTraining()
      return
    }

    const form = new FormData()
    form.append('kind', materialKind.value)
    if (selectedFile.value) form.append('file', selectedFile.value)
    if (materialContent.value.trim()) form.append('content', materialContent.value.trim())

    await apiRequest<RawMaterial>(`/api/admin/trainings/${trainingId}/raw-materials/`, {
      method: 'POST',
      body: form,
    })
    selectedFile.value = null
    materialContent.value = ''
    fileInputKey.value += 1
    successMessage.value = 'Source ajoutée à la bibliothèque.'
    await loadTraining()
  } catch (error) {
    console.error('Échec de l’ajout de la donnée brute :', error)
    errorMessage.value = 'La ressource n’a pas pu être enregistrée. Vérifiez son format.'
  } finally {
    isSaving.value = false
  }
}

async function deleteRawMaterial(material: RawMaterial) {
  if (!window.confirm(`Supprimer « ${material.display_name} » ?`)) return
  resetFeedback()
  try {
    await apiRequest<void>(`/api/admin/trainings/${trainingId}/raw-materials/${material.id}/`, {
      method: 'DELETE',
    })
    successMessage.value = 'Donnée brute supprimée.'
    await loadTraining()
  } catch (error) {
    console.error('Échec de la suppression de la donnée :', error)
    errorMessage.value = 'Impossible de supprimer cette donnée.'
  }
}

async function downloadMaterial(material: RawMaterial) {
  if (!material.download_url) return
  resetFeedback()
  try {
    await downloadApiFile(material.download_url, material.original_filename)
  } catch (error) {
    console.error('Échec du téléchargement :', error)
    errorMessage.value = 'Impossible de télécharger ce fichier.'
  }
}

async function openMaterialPreview(material: RawMaterial) {
  previewMaterial.value = material
  previewUrl.value = ''
  previewError.value = ''
  isPreviewLoading.value = material.has_file
  document.body.style.overflow = 'hidden'

  if (!material.has_file) return

  try {
    const response = await apiRequest<{ url: string }>(
      '/api/admin/trainings/' + trainingId + '/raw-materials/' + material.id + '/preview-token/',
    )
    if (previewMaterial.value?.id === material.id) {
      previewUrl.value = resolveApiUrl(response.url)
    }
  } catch (error) {
    console.error('Échec de la prévisualisation :', error)
    if (previewMaterial.value?.id === material.id) {
      previewError.value = 'Impossible de charger cette ressource.'
    }
  } finally {
    if (previewMaterial.value?.id === material.id) {
      isPreviewLoading.value = false
    }
  }
}

function closeMaterialPreview() {
  previewMaterial.value = null
  previewUrl.value = ''
  previewError.value = ''
  isPreviewLoading.value = false
  document.body.style.overflow = ''
}

function handlePreviewKeyboard(event: KeyboardEvent) {
  if (event.key === 'Escape' && previewMaterial.value) closeMaterialPreview()
}

function quizQuestionTypeLabel(type: QuizQuestionType) {
  return {
    single_choice: 'Choix unique',
    multiple_choice: 'Choix multiples',
    short_text: 'Réponse courte',
  }[type]
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
}

function materialIcon(kind: RawMaterialKind) {
  return { video: '▶', pdf: 'PDF', text: 'TXT', quiz: '?' }[kind]
}

function materialForStructure(materialId: number) {
  return rawMaterials.value.find((material) => material.id === materialId)
}

function objectiveForStructure(objectiveId: number) {
  return objectives.value.find((objective) => objective.id === objectiveId)
}

function openStructureMaterial(materialId: number) {
  const material = materialForStructure(materialId)
  if (material) void openMaterialPreview(material)
}

function materialIconForStructure(materialId: number) {
  const material = materialForStructure(materialId)
  return material ? materialIcon(material.kind) : '•'
}

onMounted(() => {
  window.addEventListener('keydown', handlePreviewKeyboard)
  if (!Number.isInteger(trainingId) || trainingId <= 0) {
    void router.replace('/admin/trainings')
    return
  }
  void loadTraining().then(() => {
    if (enrichmentInProgress.value) startEnrichmentPolling()
    if (structureGenerationInProgress.value) startStructurePolling()
  })
})

onBeforeUnmount(() => {
  stopEnrichmentPolling()
  stopStructurePolling()
  window.removeEventListener('keydown', handlePreviewKeyboard)
  document.body.style.overflow = ''
})
</script>

<template>
  <section v-if="isLoading" class="empty-state">Chargement de la formation…</section>
  <section v-else-if="training" class="training-workspace">
    <RouterLink to="/admin/trainings" class="back-link">← Toutes les formations</RouterLink>

    <header class="training-detail-heading">
      <div>
        <div class="training-detail-heading__meta">
          <span class="status-badge">{{ training.status_label }}</span>
          <span>Formation #{{ training.id }}</span>
        </div>
        <div v-if="!isEditingTitle" class="training-title-display">
          <h1>{{ training.title }}</h1>
          <button type="button" class="title-edit-button" @click="startTitleEditing">
            <span aria-hidden="true">✎</span>
            Modifier le titre
          </button>
        </div>
        <form
          v-else
          class="training-title-editor"
          @submit.prevent="saveTrainingTitle"
          @keydown.esc.prevent="cancelTitleEditing"
        >
          <label class="sr-only" for="training-title">Titre de la formation</label>
          <input
            id="training-title"
            v-model="titleDraft"
            v-focus
            required
            maxlength="255"
          />
          <button
            type="submit"
            class="button button--primary"
            :disabled="isTitleSaving || !titleDraft.trim()"
          >
            {{ isTitleSaving ? 'Enregistrement…' : 'Enregistrer' }}
          </button>
          <button
            type="button"
            class="button button--secondary"
            :disabled="isTitleSaving"
            @click="cancelTitleEditing"
          >
            Annuler
          </button>
        </form>
        <p>{{ training.description || 'Ajoutez les premières informations de conception.' }}</p>
      </div>
      <div class="training-progress" aria-label="Avancement de la préparation">
        <div>
          <strong>{{ objectives.length }}</strong
          ><span>objectifs</span>
        </div>
        <div>
          <strong>{{ rawMaterials.length }}</strong
          ><span>sources</span>
        </div>
        <div>
          <strong>{{ enrichedMaterials }}</strong
          ><span>enrichies</span>
        </div>
        <div>
          <strong>{{ units.length }}</strong
          ><span>structure</span>
        </div>
      </div>
    </header>

    <nav class="workspace-tabs" aria-label="Préparation de la formation">
      <button
        type="button"
        data-test="training-tab-objectives"
        :class="{ active: activeTab === 'objectives' }"
        @click="activeTab = 'objectives'"
      >
        <span>1</span> Objectifs pédagogiques
      </button>
      <button
        type="button"
        data-test="training-tab-raw-materials"
        :class="{ active: activeTab === 'raw-materials' }"
        @click="activeTab = 'raw-materials'"
      >
        <span>2</span> Sources et quiz
      </button>
      <button
        type="button"
        data-test="training-tab-enrichment"
        :class="{ active: activeTab === 'enrichment' }"
        @click="activeTab = 'enrichment'"
      >
        <span>3</span> Enrichissement
      </button>
      <button
        type="button"
        data-test="training-tab-generation"
        :class="{ active: activeTab === 'generation' }"
        @click="activeTab = 'generation'"
      >
        <span>4</span> Structure IA
      </button>
    </nav>

    <p v-if="successMessage" class="feedback feedback--success" role="status">
      {{ successMessage }}
    </p>
    <p v-if="errorMessage" class="feedback feedback--error" role="alert">
      {{ errorMessage }}
    </p>

    <div v-if="activeTab === 'objectives'" class="workspace-layout">
      <div class="workspace-main">
        <div class="workspace-section-heading">
          <div>
            <span class="section-kicker">Intention pédagogique</span>
            <h2>Objectifs à acquérir</h2>
          </div>
          <span class="count-badge">{{ objectives.length }}</span>
        </div>
        <p class="section-intro">
          Chaque objectif décrit une capacité observable que l’apprenant devra maîtriser. Ils
          serviront ensuite de boussole à la génération du parcours.
        </p>

        <div v-if="objectives.length === 0" class="inline-empty">
          Aucun objectif pour le moment. Commencez par le résultat attendu le plus important.
        </div>
        <ol v-else class="objective-list">
          <li v-for="objective in objectives" :key="objective.id">
            <span class="objective-list__number">{{ objective.position }}</span>
            <div>
              <strong>{{ objective.title }}</strong>
              <p v-if="objective.description">{{ objective.description }}</p>
            </div>
            <button
              type="button"
              class="icon-button icon-button--danger"
              :aria-label="`Supprimer ${objective.title}`"
              @click="deleteObjective(objective)"
            >
              ×
            </button>
          </li>
        </ol>
      </div>

      <form class="workspace-aside" @submit.prevent="addObjective">
        <span class="section-kicker">Ajouter</span>
        <h3>Nouvel objectif</h3>
        <label class="form-field">
          <span>Objectif pédagogique *</span>
          <input
            v-model="objectiveTitle"
            required
            maxlength="255"
            placeholder="Ex. Savoir structurer un argumentaire clair"
          />
        </label>
        <label class="form-field">
          <span>Précisions</span>
          <textarea
            v-model="objectiveDescription"
            rows="4"
            placeholder="Conditions, niveau attendu, critères de réussite…"
          ></textarea>
        </label>
        <button class="button button--primary button--full" :disabled="isSaving">
          {{ isSaving ? 'Ajout…' : 'Ajouter l’objectif' }}
        </button>
      </form>
    </div>

    <div
      v-else-if="activeTab === 'raw-materials'"
      class="workspace-layout"
      :class="{ 'workspace-layout--quiz': isQuiz }"
    >
      <div class="workspace-main">
        <div class="workspace-section-heading">
          <div>
            <span class="section-kicker">Bibliothèque source</span>
            <h2>Sources et quiz</h2>
          </div>
          <span class="count-badge">{{ rawMaterials.length }}</span>
        </div>
        <p class="section-intro">
          Importez les vidéos, PDF et textes sans transformation. Les quiz sont créés séparément
          avec des questions et des réponses structurées.
        </p>

        <div v-if="rawMaterials.length === 0" class="inline-empty">
          Aucun contenu disponible. Ajoutez une source ou créez un quiz structuré.
        </div>
        <div v-else class="material-list">
          <article
            v-for="material in rawMaterials"
            :key="material.id"
            class="material-card material-card--previewable"
            role="button"
            tabindex="0"
            @click="openMaterialPreview(material)"
            @keydown.enter.prevent="openMaterialPreview(material)"
          >
            <span class="material-card__icon" :class="`material-card__icon--${material.kind}`">
              {{ materialIcon(material.kind) }}
            </span>
            <div class="material-card__body">
              <span v-if="material.kind === 'quiz'">
                Quiz structuré · {{ quizQuestionCount(material) }} question{{
                  quizQuestionCount(material) > 1 ? 's' : ''
                }}
              </span>
              <span v-else>{{ material.kind_label }} · {{ formatSize(material.size) }}</span>
              <strong>{{ material.display_name }}</strong>
              <p v-if="material.kind === 'quiz'">
                {{ material.quiz_data.questions.map((question) => question.prompt).join(' · ') }}
              </p>
              <p v-else-if="material.content">{{ material.content }}</p>
            </div>
            <div class="material-card__actions" @click.stop>
              <button
                type="button"
                class="button button--secondary button--small"
                @click="openMaterialPreview(material)"
              >
                Consulter
              </button>
              <button
                v-if="material.kind === 'quiz'"
                type="button"
                class="button button--secondary button--small"
                @click="editQuiz(material)"
              >
                Modifier
              </button>
              <button
                v-if="material.download_url"
                type="button"
                class="button button--secondary button--small"
                @click="downloadMaterial(material)"
              >
                Télécharger
              </button>
              <button
                type="button"
                class="icon-button icon-button--danger"
                :aria-label="`Supprimer ${material.display_name}`"
                @click="deleteRawMaterial(material)"
              >
                ×
              </button>
            </div>
          </article>
        </div>
      </div>

      <form
        class="workspace-aside"
        :class="{ 'quiz-builder-form': isQuiz }"
        @submit.prevent="addRawMaterial"
      >
        <span class="section-kicker">{{ isQuiz ? 'Créer' : 'Importer' }}</span>
        <h3>
          {{ isQuiz ? (editingQuizId ? 'Modifier le quiz' : 'Nouveau quiz') : 'Nouvelle source' }}
        </h3>
        <label class="form-field">
          <span>Type de contenu *</span>
          <select v-model="materialKind">
            <option value="pdf">Document PDF</option>
            <option value="video">Vidéo</option>
            <option value="text">Texte libre</option>
            <option value="quiz">Quiz structuré</option>
          </select>
        </label>

        <label v-if="needsFile" class="upload-dropzone">
          <input
            :key="fileInputKey"
            required
            type="file"
            :accept="acceptedFileTypes"
            @change="handleFileSelection"
          />
          <span class="upload-dropzone__icon">↑</span>
          <strong>{{ selectedFile?.name || 'Choisir un fichier' }}</strong>
          <small>
            {{ materialKind === 'pdf' ? 'PDF uniquement' : 'Formats vidéo' }} · 500 Mo max.
          </small>
        </label>

        <div v-else-if="isQuiz" class="quiz-builder" data-test="quiz-builder">
          <label class="form-field quiz-builder__title">
            <span>Titre du quiz</span>
            <input v-model="quizTitle" maxlength="255" placeholder="Titre facultatif" />
          </label>

          <section
            v-for="(question, questionIndex) in quizQuestions"
            :key="questionIndex"
            class="quiz-question-card"
          >
            <header class="quiz-question-card__header">
              <strong>Question {{ questionIndex + 1 }}</strong>
              <div>
                <select
                  v-model="question.type"
                  :aria-label="'Type de la question ' + (questionIndex + 1)"
                  @change="changeQuizQuestionType(question)"
                >
                  <option value="single_choice">Choix unique</option>
                  <option value="multiple_choice">Choix multiples</option>
                  <option value="short_text">Réponse courte</option>
                </select>
                <button
                  type="button"
                  class="icon-button icon-button--danger"
                  :disabled="quizQuestions.length === 1"
                  :aria-label="'Supprimer la question ' + (questionIndex + 1)"
                  @click="removeQuizQuestion(questionIndex)"
                >
                  ×
                </button>
              </div>
            </header>

            <label class="form-field">
              <span>Question *</span>
              <textarea
                v-model="question.prompt"
                required
                rows="2"
                placeholder="Saisissez la question"
              ></textarea>
            </label>

            <div v-if="question.type === 'short_text'" class="quiz-answer-list">
              <span class="quiz-field-label">Réponses acceptées *</span>
              <div
                v-for="(_, answerIndex) in question.accepted_answers"
                :key="answerIndex"
                class="quiz-answer-row"
              >
                <span class="quiz-answer-row__marker">Aa</span>
                <input
                  v-model="question.accepted_answers[answerIndex]"
                  required
                  :aria-label="'Réponse acceptée ' + (answerIndex + 1)"
                  placeholder="Réponse correcte"
                />
                <button
                  type="button"
                  class="icon-button"
                  :disabled="question.accepted_answers.length === 1"
                  :aria-label="'Supprimer la réponse ' + (answerIndex + 1)"
                  @click="removeAcceptedAnswer(question, answerIndex)"
                >
                  ×
                </button>
              </div>
              <button type="button" class="quiz-inline-action" @click="addAcceptedAnswer(question)">
                + Ajouter une réponse acceptée
              </button>
            </div>

            <div v-else class="quiz-answer-list">
              <span class="quiz-field-label">Choix de réponse *</span>
              <div
                v-for="(option, optionIndex) in question.options"
                :key="optionIndex"
                class="quiz-answer-row"
              >
                <input
                  v-if="question.type === 'single_choice'"
                  type="radio"
                  :name="'question-' + questionIndex"
                  :checked="option.is_correct"
                  :aria-label="'Bonne réponse ' + (optionIndex + 1)"
                  @change="selectSingleCorrectOption(question, optionIndex)"
                />
                <input
                  v-else
                  v-model="option.is_correct"
                  type="checkbox"
                  :aria-label="'Bonne réponse ' + (optionIndex + 1)"
                />
                <input
                  v-model="option.text"
                  required
                  :aria-label="'Choix ' + (optionIndex + 1)"
                  :placeholder="'Option ' + (optionIndex + 1)"
                />
                <button
                  type="button"
                  class="icon-button"
                  :disabled="question.options.length === 2"
                  :aria-label="'Supprimer le choix ' + (optionIndex + 1)"
                  @click="removeQuizOption(question, optionIndex)"
                >
                  ×
                </button>
              </div>
              <button type="button" class="quiz-inline-action" @click="addQuizOption(question)">
                + Ajouter un choix
              </button>
            </div>
          </section>

          <button type="button" class="quiz-add-question" @click="addQuizQuestion">
            + Ajouter une question
          </button>
        </div>

        <label v-else class="form-field">
          <span>Texte source *</span>
          <textarea
            v-model="materialContent"
            required
            rows="9"
            placeholder="Collez ici les notes, transcriptions ou contenus existants…"
          ></textarea>
        </label>

        <p class="privacy-note">
          <span aria-hidden="true">✓</span>
          {{
            isQuiz
              ? 'Questions et réponses enregistrées sous forme structurée.'
              : 'Fichiers stockés dans l’espace privé de la formation.'
          }}
        </p>
        <button
          class="button button--primary button--full"
          :disabled="isSaving || (isQuiz && !quizIsValid)"
        >
          {{
            isSaving
              ? 'Enregistrement…'
              : isQuiz
                ? editingQuizId
                  ? 'Enregistrer le quiz'
                  : 'Créer le quiz'
                : 'Ajouter la source'
          }}
        </button>
        <button
          v-if="editingQuizId"
          type="button"
          class="button button--secondary button--full"
          @click="resetQuizDraft"
        >
          Annuler la modification
        </button>
      </form>
    </div>

    <div v-else-if="activeTab === 'enrichment'" class="workspace-layout enrichment-layout">
      <div class="workspace-main">
        <div class="workspace-section-heading">
          <div>
            <span class="section-kicker">Préparation du matériel</span>
            <h2>Enrichissement des ressources</h2>
          </div>
          <span class="count-badge">{{ enrichedMaterials }}/{{ rawMaterials.length }}</span>
        </div>
        <p class="section-intro">
          L’IA extrait le contenu utile de chaque ressource et produit une couche descriptive :
          transcription, rôle du média, résumé, concepts clés et définitions. Les fichiers bruts
          restent inchangés et aucun objectif pédagogique n’est généré ici.
        </p>

        <div v-if="rawMaterials.length === 0" class="inline-empty">
          Ajoutez d’abord des sources ou des quiz à enrichir.
        </div>
        <div v-else class="enrichment-list">
          <article
            v-for="material in rawMaterials"
            :key="material.id"
            class="enrichment-card"
            :class="`enrichment-card--${material.enrichment?.status ?? 'pending'}`"
          >
            <header class="enrichment-card__header">
              <span class="material-card__icon" :class="`material-card__icon--${material.kind}`">
                {{ materialIcon(material.kind) }}
              </span>
              <div>
                <span>{{ material.kind_label }}</span>
                <strong>{{ material.display_name }}</strong>
              </div>
              <span
                class="enrichment-status"
                :class="`enrichment-status--${material.enrichment?.status ?? 'pending'}`"
              >
                {{ material.enrichment?.status_label ?? 'À enrichir' }}
              </span>
            </header>

            <div
              v-if="['queued', 'processing'].includes(material.enrichment?.status ?? '')"
              class="enrichment-card__processing"
            >
              <span class="enrichment-spinner" aria-hidden="true"></span>
              {{ material.enrichment?.progress_message || 'Traitement en cours' }}
            </div>
            <div v-else-if="material.enrichment?.status === 'error'" class="enrichment-card__error">
              <strong>Cette ressource n’a pas pu être enrichie.</strong>
              <p>{{ material.enrichment.error_message }}</p>
            </div>
            <div v-else-if="material.enrichment?.status === 'ready'" class="enrichment-result">
              <section>
                <span>Rôle du média</span>
                <p>{{ material.enrichment.media_purpose }}</p>
              </section>
              <section>
                <span>Résumé</span>
                <p>{{ material.enrichment.summary }}</p>
              </section>
              <section v-if="material.enrichment.key_concepts.length">
                <span>Concepts clés</span>
                <div class="enrichment-concepts">
                  <article v-for="concept in material.enrichment.key_concepts" :key="concept.name">
                    <strong>{{ concept.name }}</strong>
                    <p>{{ concept.explanation }}</p>
                  </article>
                </div>
              </section>
              <details v-if="material.enrichment.glossary.length">
                <summary>Définitions ({{ material.enrichment.glossary.length }})</summary>
                <dl class="enrichment-glossary">
                  <template v-for="entry in material.enrichment.glossary" :key="entry.term">
                    <dt>{{ entry.term }}</dt>
                    <dd>{{ entry.definition }}</dd>
                  </template>
                </dl>
              </details>
              <details v-if="material.enrichment.transcript || material.enrichment.extracted_text">
                <summary>
                  {{ material.enrichment.transcript ? 'Transcription' : 'Texte extrait' }}
                </summary>
                <pre>{{ material.enrichment.transcript || material.enrichment.extracted_text }}</pre>
              </details>
              <div v-if="material.enrichment.keywords.length" class="enrichment-keywords">
                <span v-for="keyword in material.enrichment.keywords" :key="keyword">{{ keyword }}</span>
              </div>
            </div>
            <p v-else class="enrichment-card__empty">
              Cette ressource est intacte et n’a pas encore été analysée.
            </p>

            <footer>
              <button
                type="button"
                class="button button--secondary button--small"
                @click="openMaterialPreview(material)"
              >
                Consulter la source brute
              </button>
              <small v-if="material.enrichment?.ai_model">
                Généré avec {{ material.enrichment.ai_model }}
              </small>
            </footer>
          </article>
        </div>
      </div>

      <aside class="workspace-aside enrichment-panel">
        <span class="section-kicker">Étape 3</span>
        <h3>Préparer les ressources</h3>
        <p>
          Un seul lancement traite les ressources non enrichies. Les vidéos sont transcrites, les
          PDF sont extraits et chaque contenu reçoit des métadonnées structurées.
        </p>
        <div class="enrichment-progress" :style="{ '--progress': enrichmentProgress + '%' }">
          <div><span></span></div>
          <strong>{{ enrichmentProgress }} %</strong>
          <small>{{ enrichedMaterials }} sur {{ rawMaterials.length }} prêtes</small>
        </div>
        <div class="generation-summary">
          <div><span>Prêtes</span><strong>{{ enrichedMaterials }}</strong></div>
          <div><span>En cours</span><strong>{{ enrichmentInProgress ? 'Oui' : 'Non' }}</strong></div>
          <div><span>Erreurs</span><strong>{{ enrichmentErrors }}</strong></div>
        </div>
        <button
          type="button"
          class="button button--primary button--full"
          data-test="generate-enrichment-button"
          :disabled="
            isSaving ||
            enrichmentInProgress ||
            rawMaterials.length === 0 ||
            !training.enrichment_ai_configured
          "
          @click="generateEnrichments"
        >
          {{
            enrichmentInProgress
              ? 'Enrichissement en cours…'
              : allMaterialsEnriched
                ? 'Relancer l’enrichissement'
                : 'Enrichir avec l’IA'
          }}
        </button>
        <small v-if="!training.enrichment_ai_configured" class="generation-panel__note">
          Configurez OPENAI_API_KEY dans le backend pour activer le traitement.
        </small>
        <small v-else class="generation-panel__note">
          Le traitement peut prendre du temps, particulièrement pour les vidéos.
        </small>
      </aside>
    </div>

    <div v-else class="workspace-layout generation-layout">
      <div class="workspace-main">
        <div class="workspace-section-heading">
          <div>
            <span class="section-kicker">Construction du parcours</span>
            <h2>Génération de la structure par IA</h2>
          </div>
          <span class="generation-status">
            {{ structureGeneration?.status_label ?? 'À générer' }}
          </span>
        </div>
        <p class="section-intro">
          L’IA utilisera exclusivement les objectifs pédagogiques renseignés et les ressources
          enrichies pour proposer les modules, chapitres et sections de la formation.
        </p>

        <div class="generation-prerequisites" aria-label="Prérequis de la génération">
          <article :class="{ ready: objectives.length > 0 }">
            <span class="generation-prerequisites__icon" aria-hidden="true">
              {{ objectives.length > 0 ? '✓' : '1' }}
            </span>
            <div>
              <strong>Objectifs pédagogiques</strong>
              <p v-if="objectives.length > 0">
                {{ objectives.length }} objectif{{ objectives.length > 1 ? 's' : '' }} disponible{{
                  objectives.length > 1 ? 's' : ''
                }}.
              </p>
              <p v-else>Renseignez au moins un objectif pédagogique.</p>
            </div>
          </article>
          <article :class="{ ready: rawMaterials.length > 0 }">
            <span class="generation-prerequisites__icon" aria-hidden="true">
              {{ rawMaterials.length > 0 ? '✓' : '2' }}
            </span>
            <div>
              <strong>Sources et quiz</strong>
              <p v-if="rawMaterials.length > 0">
                {{ rawMaterials.length }} source{{ rawMaterials.length > 1 ? 's' : '' }} disponible{{
                  rawMaterials.length > 1 ? 's' : ''
                }}
                pour l’enrichissement.
              </p>
              <p v-else>Ajoutez une source ou créez un quiz structuré.</p>
            </div>
          </article>
          <article :class="{ ready: allMaterialsEnriched }">
            <span class="generation-prerequisites__icon" aria-hidden="true">
              {{ allMaterialsEnriched ? '✓' : '3' }}
            </span>
            <div>
              <strong>Enrichissement</strong>
              <p v-if="allMaterialsEnriched">Toutes les ressources sont prêtes.</p>
              <p v-else>
                {{ enrichedMaterials }} ressource{{ enrichedMaterials > 1 ? 's' : '' }} enrichie{{
                  enrichedMaterials > 1 ? 's' : ''
                }} sur {{ rawMaterials.length }}.
              </p>
            </div>
          </article>
        </div>

        <div v-if="structureGenerationInProgress" class="generation-output">
          <span class="enrichment-spinner" aria-hidden="true"></span>
          <div>
            <strong>Génération en cours</strong>
            <p>{{ structureGeneration?.progress_message }}</p>
          </div>
        </div>

        <div
          v-else-if="structureGeneration?.status === 'error'"
          class="generation-output generation-output--error"
        >
          <span class="generation-output__icon" aria-hidden="true">!</span>
          <div>
            <strong>La génération a échoué</strong>
            <p>{{ structureGeneration.error_message }}</p>
          </div>
        </div>

        <div v-else-if="generatedStructure" class="generated-course">
          <header class="generated-course__heading">
            <span class="generation-output__icon" aria-hidden="true">✦</span>
            <div>
              <span>Proposition IA</span>
              <h3>{{ generatedStructure.title }}</h3>
              <p>{{ generatedStructure.introduction }}</p>
            </div>
            <span v-if="isStructurePublished" class="published-structure-badge">
              ✓ Structure publiée
            </span>
          </header>

          <ol class="generated-modules">
            <li v-for="(module, moduleIndex) in generatedStructure.modules" :key="moduleIndex">
              <div class="generated-node generated-node--module">
                <span>Module {{ moduleIndex + 1 }}</span>
                <strong>{{ module.title }}</strong>
                <p>{{ module.rationale }}</p>
              </div>
              <ol>
                <li v-for="(chapter, chapterIndex) in module.chapters" :key="chapterIndex">
                  <div class="generated-node generated-node--chapter">
                    <span>Chapitre {{ chapterIndex + 1 }}</span>
                    <strong>{{ chapter.title }}</strong>
                    <p>{{ chapter.rationale }}</p>
                  </div>
                  <ol>
                    <li v-for="(section, sectionIndex) in chapter.sections" :key="sectionIndex">
                      <div class="generated-node generated-node--section">
                        <span>Section {{ sectionIndex + 1 }}</span>
                        <strong>{{ section.title }}</strong>
                        <p>{{ section.rationale }}</p>
                        <div v-if="section.objective_ids.length" class="generated-objectives">
                          <span
                            v-for="objectiveId in section.objective_ids"
                            :key="objectiveId"
                          >
                            Objectif · {{ objectiveForStructure(objectiveId)?.title ?? objectiveId }}
                          </span>
                        </div>
                        <div class="generated-resources">
                          <button
                            v-for="materialId in section.resource_ids"
                            :key="materialId"
                            type="button"
                            @click="openStructureMaterial(materialId)"
                          >
                            <span aria-hidden="true">{{
                              materialIconForStructure(materialId)
                            }}</span>
                            {{ materialForStructure(materialId)?.display_name ?? materialId }}
                          </button>
                        </div>
                      </div>
                    </li>
                  </ol>
                </li>
              </ol>
            </li>
          </ol>

          <aside
            v-if="generatedStructure.unsupported_objective_ids.length"
            class="unsupported-objectives"
          >
            <strong>Objectifs non couverts par les ressources</strong>
            <ul>
              <li
                v-for="objectiveId in generatedStructure.unsupported_objective_ids"
                :key="objectiveId"
              >
                {{ objectiveForStructure(objectiveId)?.title ?? objectiveId }}
              </li>
            </ul>
          </aside>
        </div>

        <div v-else class="generation-output">
          <span class="generation-output__icon" aria-hidden="true">✦</span>
          <div>
            <strong>Aucune proposition générée</strong>
            <p>
              La proposition présentera ici la structure du cours, la couverture des objectifs et
              les sources utilisées dans chaque section.
            </p>
          </div>
        </div>
      </div>

      <aside class="workspace-aside generation-panel">
        <span class="section-kicker">Étape suivante</span>
        <h3>Générer le cours</h3>
        <p>
          Le moteur organise les ressources enrichies sans modifier les objectifs saisis
          manuellement. Chaque ressource est placée une seule fois dans la proposition.
        </p>
        <div class="generation-summary">
          <div>
            <span>Objectifs</span><strong>{{ objectives.length }}</strong>
          </div>
          <div>
            <span>Sources et quiz</span><strong>{{ rawMaterials.length }}</strong>
          </div>
          <div>
            <span>Ressources enrichies</span><strong>{{ enrichedMaterials }}</strong>
          </div>
        </div>
        <button
          type="button"
          class="button button--primary button--full"
          data-test="generate-course-button"
          :disabled="isSaving || !canGenerateStructure"
          @click="generateStructure"
        >
          {{
            structureGenerationInProgress
              ? 'Génération en cours…'
              : generatedStructure
                ? 'Régénérer la structure'
                : 'Générer la structure avec l’IA'
          }}
        </button>
        <div class="publication-action">
          <span>Validation humaine</span>
          <p>
            La publication fige cette proposition comme structure active de la formation.
          </p>
          <button
            type="button"
            class="button button--publish button--full"
            data-test="publish-structure-button"
            :disabled="isPublishing || !canPublishStructure"
            @click="publishStructure"
          >
            {{
              isPublishing
                ? 'Publication…'
                : isStructurePublished
                  ? 'Structure publiée'
                  : 'Valider et publier la structure'
            }}
          </button>
        </div>
        <small v-if="objectives.length === 0" class="generation-panel__note">
          Ajoutez au moins un objectif pédagogique.
        </small>
        <small v-else-if="!allMaterialsEnriched" class="generation-panel__note">
          Terminez l’enrichissement des {{ rawMaterials.length }} ressources.
        </small>
        <small v-else-if="!isStructurePublished" class="generation-panel__note">
          La proposition restera un brouillon à examiner avant validation.
        </small>
        <small v-else class="generation-panel__note">
          Cette structure est maintenant la version active de la formation.
        </small>
      </aside>
    </div>

    <Teleport to="body">
      <div
        v-if="previewMaterial"
        class="resource-preview-backdrop"
        @click.self="closeMaterialPreview"
      >
        <section
          class="resource-preview"
          role="dialog"
          aria-modal="true"
          :aria-label="'Consulter ' + previewMaterial.display_name"
        >
          <header class="resource-preview__header">
            <div>
              <span class="section-kicker">{{ previewMaterial.kind_label }}</span>
              <h2>{{ previewMaterial.display_name }}</h2>
            </div>
            <button
              type="button"
              class="icon-button"
              aria-label="Fermer la prévisualisation"
              @click="closeMaterialPreview"
            >
              ×
            </button>
          </header>

          <div class="resource-preview__content">
            <div v-if="isPreviewLoading" class="resource-preview__state">
              Chargement de la ressource…
            </div>
            <div
              v-else-if="previewError"
              class="resource-preview__state resource-preview__state--error"
            >
              {{ previewError }}
            </div>
            <video
              v-else-if="previewMaterial.kind === 'video' && previewUrl"
              class="resource-preview__video"
              :src="previewUrl"
              controls
              preload="metadata"
            ></video>
            <iframe
              v-else-if="previewMaterial.kind === 'pdf' && previewUrl"
              class="resource-preview__pdf"
              :src="previewUrl"
              :title="previewMaterial.display_name"
            ></iframe>
            <pre v-else-if="previewMaterial.kind === 'text'" class="resource-preview__text">{{
              previewMaterial.content
            }}</pre>
            <ol v-else-if="previewMaterial.kind === 'quiz'" class="quiz-preview">
              <li
                v-for="(question, questionIndex) in previewMaterial.quiz_data.questions"
                :key="questionIndex"
              >
                <div class="quiz-preview__question-heading">
                  <strong>{{ questionIndex + 1 }}. {{ question.prompt }}</strong>
                  <span>{{ quizQuestionTypeLabel(question.type) }}</span>
                </div>
                <ul v-if="question.options" class="quiz-preview__options">
                  <li
                    v-for="(option, optionIndex) in question.options"
                    :key="optionIndex"
                    :class="{ correct: option.is_correct }"
                  >
                    <span aria-hidden="true">{{
                      question.type === 'multiple_choice' ? '□' : '○'
                    }}</span>
                    {{ option.text }}
                    <strong v-if="option.is_correct">Bonne réponse</strong>
                  </li>
                </ul>
                <div v-else class="quiz-preview__answers">
                  <span
                    >Réponse{{ (question.accepted_answers?.length ?? 0) > 1 ? 's' : '' }} :</span
                  >
                  <strong v-for="answer in question.accepted_answers" :key="answer">
                    {{ answer }}
                  </strong>
                </div>
              </li>
            </ol>
          </div>

          <footer v-if="previewMaterial.download_url" class="resource-preview__footer">
            <button
              type="button"
              class="button button--secondary"
              @click="downloadMaterial(previewMaterial)"
            >
              Télécharger le fichier
            </button>
          </footer>
        </section>
      </div>
    </Teleport>
  </section>

  <section v-else class="empty-state empty-state--illustrated">
    <h2>Formation indisponible</h2>
    <p>{{ errorMessage }}</p>
    <RouterLink to="/admin/trainings" class="button button--primary"
      >Retour aux formations</RouterLink
    >
  </section>
</template>
