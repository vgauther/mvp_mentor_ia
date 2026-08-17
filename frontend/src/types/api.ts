export type UserRole = 'admin' | 'learner'

export interface AuthUser {
  id: number
  keycloak_id: string
  username: string
  email: string | null
  display_name: string
  role: UserRole
  role_label: string
  roles: UserRole[]
}

export interface ManagedUser {
  id: number
  username: string
  email: string | null
  display_name: string
  role: UserRole
  role_label: string
  assigned_trainings: AssignedTraining[]
  created_at: string
  updated_at: string
}

export interface AssignedTraining {
  id: number
  title: string
  status: TrainingStatus
  status_label: string
}

export interface LearnerTraining extends AssignedTraining {
  description: string
  updated_at: string
}

export type TrainingStatus = 'draft' | 'structuring' | 'ready'
export type CourseUnitKind = 'module' | 'chapter' | 'section'
export type RawMaterialKind = 'video' | 'pdf' | 'text' | 'quiz'
export type QuizQuestionType = 'single_choice' | 'multiple_choice' | 'short_text'
export type EnrichmentStatus = 'pending' | 'queued' | 'processing' | 'ready' | 'error'
export type StructureGenerationStatus = 'pending' | 'queued' | 'processing' | 'ready' | 'error'

export interface QuizOption {
  text: string
  is_correct: boolean
}

export interface QuizQuestion {
  type: QuizQuestionType
  prompt: string
  options?: QuizOption[]
  accepted_answers?: string[]
}

export interface QuizData {
  title: string
  questions: QuizQuestion[]
}

export interface KeyConcept {
  name: string
  explanation: string
}

export interface GlossaryEntry {
  term: string
  definition: string
}

export interface RawMaterialEnrichment {
  status: EnrichmentStatus
  status_label: string
  progress_message: string
  transcript: string
  extracted_text: string
  media_purpose: string
  summary: string
  language: string
  key_concepts: KeyConcept[]
  glossary: GlossaryEntry[]
  keywords: string[]
  ai_model: string
  error_message: string
  started_at: string | null
  generated_at: string | null
  updated_at: string
}

export interface GeneratedSection {
  title: string
  rationale: string
  objective_ids: number[]
  resource_ids: number[]
}

export interface GeneratedChapter {
  title: string
  rationale: string
  sections: GeneratedSection[]
}

export interface GeneratedModule {
  title: string
  rationale: string
  chapters: GeneratedChapter[]
}

export interface GeneratedCourseStructure {
  title: string
  introduction: string
  modules: GeneratedModule[]
  unsupported_objective_ids: number[]
}

export interface CourseStructureGeneration {
  status: StructureGenerationStatus
  status_label: string
  progress_message: string
  structure: GeneratedCourseStructure | Record<string, never>
  ai_model: string
  error_message: string
  started_at: string | null
  generated_at: string | null
  published_at: string | null
  published_by_name: string
  updated_at: string
}

export interface LearningObjective {
  id: number
  title: string
  description: string
  position: number
  created_at: string
  updated_at: string
}

export interface CourseUnit {
  id: number
  parent: number | null
  kind: CourseUnitKind
  kind_label: string
  working_title: string
  notes: string
  position: number
  objective_ids: number[]
  resource_ids: number[]
  created_at: string
  updated_at: string
}

export interface RawMaterial {
  id: number
  kind: RawMaterialKind
  kind_label: string
  display_name: string
  content: string
  quiz_data: QuizData
  has_file: boolean
  download_url: string | null
  original_filename: string
  mime_type: string
  size: number
  created_at: string
  enrichment: RawMaterialEnrichment | null
}

export interface TrainingSummary {
  id: number
  title: string
  description: string
  status: TrainingStatus
  status_label: string
  created_by_name: string
  objective_count: number
  unit_count: number
  raw_material_count: number
  created_at: string
  updated_at: string
}

export interface TrainingDetail extends TrainingSummary {
  enrichment_ai_configured: boolean
  objectives: LearningObjective[]
  units: CourseUnit[]
  raw_materials: RawMaterial[]
  structure_generation: CourseStructureGeneration | null
}
