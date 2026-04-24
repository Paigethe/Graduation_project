export type Role = 'student' | 'counselor' | 'college_admin' | 'sys_admin'

export interface College {
  id: number
  name: string
}

export interface MajorLite {
  id: number
  name: string
  college: College | null
}

export interface ClassGroupLite {
  id: number
  name: string
  major: MajorLite | null
}

export interface UserLite {
  id: number
  username: string
  real_name: string
  role: Role
  college: College | null
  major: MajorLite | null
  class_group: ClassGroupLite | null
}

export interface UserMe extends UserLite {}

export type RiskLevel = 'low' | 'medium' | 'high'

export interface PageResp<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface KnowledgeCategory {
  id: number
  name: string
}

export interface KnowledgeArticle {
  id: number
  title: string
  summary: string
  content: string
  document?: string | null
  document_url?: string | null
  category: KnowledgeCategory | null
  is_published: boolean
  target_college: College | null
  created_by: UserLite | null
  created_at: string
  updated_at: string
  is_favorited: boolean
}

export interface QuestionnaireQuestion {
  id: number
  text: string
  dimension?: string
  weight?: number
}

export interface QuestionnaireTemplate {
  id: number
  name: string
  scale_type: string
  description: string
  questions: QuestionnaireQuestion[]
  created_at: string
}

export interface Questionnaire {
  id: number
  title: string
  description: string
  is_active: boolean
  start_at: string | null
  end_at: string | null
  template: QuestionnaireTemplate
  target_college: College | null
  created_by: UserLite | null
  created_at: string
  retest_pending?: boolean
}

export interface QuestionnaireRetestTask {
  id: number
  questionnaire: Questionnaire
  student: UserLite
  created_by: UserLite | null
  reason: string
  due_date: string | null
  status: 'pending' | 'completed' | 'canceled' | string
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface AssessmentResult {
  id: number
  total_score: number
  avg_score: number
  dimension_scores: Record<string, number>
  risk_level: RiskLevel
  predicted_risk_level: RiskLevel
  model_meta?: {
    model_version?: string
    confidence?: number
    [key: string]: any
  }
  created_at: string
  student: UserLite
  questionnaire: Questionnaire
}

export interface RiskAlert {
  id: number
  student: UserLite
  level: RiskLevel
  message: string
  created_at: string
  is_acknowledged: boolean
  acknowledged_by: UserLite | null
  acknowledged_at: string | null
}

export type InterventionStatus = 'draft' | 'sent' | 'in_progress' | 'done' | string

export interface InterventionPlan {
  id: number
  title: string
  content: string
  status: InterventionStatus
  created_at: string
  updated_at: string
  student: UserLite
  counselor: UserLite | null
  assessment: number | null
  knowledge_article?: KnowledgeArticle | null
}

export type ConversationKind = 'ai' | 'human'

export interface ConversationLastMessage {
  id: number
  sender_kind: 'user' | 'ai' | 'system'
  content: string
  created_at: string
}

export interface Conversation {
  id: number
  kind: ConversationKind
  student: UserLite
  counselor: UserLite | null
  created_at: string
  updated_at: string
  last_message: ConversationLastMessage | null
}

export interface ChatMessage {
  id: number
  sender_kind: 'user' | 'ai' | 'system'
  sender: UserLite | null
  content: string
  created_at: string
  read_at: string | null
}
