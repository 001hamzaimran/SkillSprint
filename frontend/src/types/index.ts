export interface User {
  _id: string
  email: string
  name: string
  role: 'admin' | 'training_manager' | 'reviewer' | 'manager' | 'employee'
  active: boolean
  created_at: string
}

export interface Role {
  _id: string
  name: string
  department: string
  description: string
  created_at: string
}

export interface Employee {
  _id: string
  name: string
  role_id: string
  role_name: string
  department: string
  joining_date: string
  experience: 'Beginner' | 'Intermediate' | 'Advanced'
  manager_id?: string
  user_id?: string
  active_plan_id?: string
  created_at: string
}

export interface Document {
  _id: string
  document_id: string
  version: string
  title: string
  status: 'draft' | 'active' | 'superseded'
  filename: string
  path: string
  effective_date: string
  category: string
  role_ids: string[]
  suspicious: boolean
  digest: string
  approved_by?: string
  approved_at?: string
  created_at: string
  created_by: string
}

export interface SourceSection {
  _id: string
  document_id: string
  section_id: string
  heading?: string
  location?: string
  page?: number
  text: string
  suspicious: boolean
}

export interface Requirement {
  _id: string
  document_id: string
  section_id: string
  requirement_id: string
  title: string
  text: string
  status: 'draft' | 'approved' | 'rejected'
  mandatory: boolean
  due_stage: string
  competency?: string
  role_ids: string[]
  prerequisites?: string[]
  policy_rule?: PolicyRule | null
  reviewed_by?: string
  reviewed_at?: string
  origin?: string
}

export interface PolicyRule {
  key: string
  value: string
  condition: string
  exception: string
  answer_fact: string
  module_category: string
  assessment_topic: string
}

export interface Job {
  _id: string
  kind: 'extract' | 'generate' | 'selective'
  status: 'queued' | 'running' | 'completed' | 'failed'
  actor_id: string
  target_id: string
  created_at: string
  started_at?: string
  finished_at?: string
  attempts: number
  result_id?: string
  summary?: string
  error?: string
}

export interface QuizQuestion {
  question: string
  options: string[]
  correct_index: number
  explanation: string
  evidence_quote: string
}

export interface Scenario {
  prompt: string
  expected_response: string
}

export interface RubricCriterion {
  criterion: string
  max_points: number
}

export interface LearningItem {
  requirement_id: string
  role_id: string
  source_document_id: string
  source_section_id: string
  source_quote: string
  mandatory: boolean
  stage: string
  module_title: string
  learning_objective: string
  practical_activity: string
  estimated_minutes: number
  lesson: string
  checklist: string[]
  scenario: Scenario
  quiz: QuizQuestion
  rubric: RubricCriterion[]
  policy_facts?: PolicyRule | null
}

export interface PlanContent {
  title: string
  summary: string
  role_id: string
  items: LearningItem[]
}

export interface ValidationResult {
  coverage: number
  traceability: number
  core_passed: boolean
  status: string
  findings: Array<{ code: string; message: string; requirement_id?: string }>
  warnings: Array<{ code: string; message: string; requirement_id?: string }>
  rows: Array<{
    requirement_id: string
    result: string
    expected_text: string
    actual_text: string
    errors: string[]
  }>
}

export interface Plan {
  _id: string
  employee_id: string
  role_id: string
  status: string
  content: PlanContent
  validation: ValidationResult
  learning_checks?: {
    passed: boolean
    findings: Array<{ code: string; message: string }>
  }
  source_document_ids: string[]
  model: string
  prompt_version: string
  origin?: string
  parent_plan_id?: string
  root_plan_id?: string
  carry_parent_plan_id?: string
  update_delta?: {
    retained: string[]
    regenerate: string[]
    removed: string[]
  }
  progress_carry?: boolean
  published_by?: string
  published_at?: string
  created_by?: string
  created_at: string
}

export interface AuditEvent {
  _id: string
  actor_id: string
  action: string
  target_id: string
  details?: Record<string, unknown>
  created_at: string
}

export interface PlanReview {
  _id: string
  plan_id: string
  actor_id: string
  actor_name: string
  decision: 'approve' | 'reject' | 'comment' | 'edit'
  comment: string
  created_at: string
}

export interface LearningProgress {
  plan_id: string
  employee_id: string
  requirement_id: string
  checked: number[]
  lesson_read: boolean
}

export interface QuizAttempt {
  _id: string
  plan_id: string
  employee_id: string
  requirement_id: string
  answer: number
  score: number
  passed: boolean
  feedback: string
  created_at: string
}

export interface PracticalSubmission {
  _id: string
  plan_id: string
  employee_id: string
  requirement_id: string
  status: 'pending' | 'graded'
  scenario_response: string
  practical_response: string
  scores?: number[]
  maximum?: number
  percent?: number
  passed?: boolean
  feedback?: string
  graded_by?: string
  graded_at?: string
  created_at: string
}

export interface ProgressReport {
  percent: number
  completed: number
  total: number
  mandatory_completed: number
  mandatory_total: number
  mandatory_complete: boolean
  overdue: number
  milestones: Array<{
    stage: string
    complete: number
    total: number
  }>
  weak: Array<{
    competency: string
    item: LearningItem
  }>
  rows: Array<{
    item: LearningItem
    saved: LearningProgress | null
    quiz_passed: boolean
    quiz_attempts: QuizAttempt[]
    practical_passed: boolean
    latest_submission: PracticalSubmission | null
    submissions: PracticalSubmission[]
    complete: boolean
    overdue: boolean
    due_date: string | null
    blocked_by: string[]
  }>
}

export interface LearningCard {
  employee: Employee
  plan: Plan | null
  fresh: boolean
  report: ProgressReport | null
}

export interface ComparisonRow {
  requirement_id: string
  status: 'Added' | 'Removed' | 'Changed' | 'Unchanged'
  left?: LearningItem
  right?: LearningItem
}

export interface Comparison {
  comparable: boolean
  categories: Array<{
    category: string
    score: number | null
    intersection: number
    union: number
  }>
  consistency_score: number | null
  method: string
  limitation: string
  rows: ComparisonRow[]
}

export interface ConflictGroup {
  _id: string
  key: string
  condition: string
  requirements: Requirement[]
  resolved: boolean
  winner_id?: string
}

export interface VerificationState {
  requirements: Requirement[]
  excluded: Requirement[]
  unresolved: ConflictGroup[]
  conflicts: ConflictGroup[]
}

export interface DependencyFinding {
  code: string
  message: string
  requirement_id?: string
}

export interface Experiment {
  _id: string
  employee_id: string
  actor_id: string
  snapshot_digest: string
  employee_snapshot: Record<string, string>
  job_ids: string[]
  result?: Record<string, unknown>
  created_at: string
}

export interface DashboardStats {
  employees: number
  plans: number
  documents?: number
  approved?: number
}

// Editor/Reviewer role sets for frontend permission checks
export const EDITORS = new Set(['admin', 'training_manager'])
export const REVIEWERS = new Set(['admin', 'reviewer'])
export const STAGES = ['Day 1', 'Week 1', 'Week 2', 'First 30 Days', 'First 60 Days', 'First 90 Days'] as const
