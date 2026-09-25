import { create } from 'zustand'
import api from '@/lib/api'
import type { Plan, Employee, ProgressReport, LearningCard, PracticalSubmission } from '@/types'

interface LearningState {
  cards: LearningCard[]
  currentPlan: Plan | null
  currentEmployee: Employee | null
  report: ProgressReport | null
  active: boolean
  isLearner: boolean
  passPercent: number
  submissions: PracticalSubmission[]
  assessmentEmployees: Record<string, Employee>
  isLoading: boolean
  fetchLearningHome: () => Promise<void>
  fetchLearnWorkspace: (planId: string) => Promise<void>
  saveProgress: (planId: string, reqId: string, data: Record<string, unknown>) => Promise<void>
  submitQuiz: (planId: string, reqId: string, answer: number) => Promise<void>
  submitPractical: (planId: string, reqId: string, data: Record<string, string>) => Promise<void>
  gradeSubmission: (submissionId: string, data: Record<string, unknown> | FormData) => Promise<void>
  fetchAssessments: () => Promise<void>
}

export const useLearningStore = create<LearningState>((set) => ({
  cards: [],
  currentPlan: null,
  currentEmployee: null,
  report: null,
  active: false,
  isLearner: false,
  passPercent: 80,
  submissions: [],
  assessmentEmployees: {},
  isLoading: false,

  fetchLearningHome: async () => {
    set({ isLoading: true })
    const res = await api.get('learning').json<{ cards: LearningCard[] }>()
    set({ cards: res.cards, isLoading: false })
  },

  fetchLearnWorkspace: async (planId: string) => {
    set({ isLoading: true })
    const res = await api.get(`learning/${planId}`).json<{
      plan: Plan
      employee: Employee
      report: ProgressReport
      active: boolean
      is_learner: boolean
      pass_percent: number
    }>()
    set({
      currentPlan: res.plan,
      currentEmployee: res.employee,
      report: res.report,
      active: res.active,
      isLearner: res.is_learner,
      passPercent: res.pass_percent,
      isLoading: false,
    })
  },

  saveProgress: async (planId: string, reqId: string, data: Record<string, unknown>) => {
    await api.post(`learning/${planId}/${reqId}/progress`, { json: data })
  },

  submitQuiz: async (planId: string, reqId: string, answer: number) => {
    await api.post(`learning/${planId}/${reqId}/quiz`, { json: { answer } })
  },

  submitPractical: async (planId: string, reqId: string, data: Record<string, string>) => {
    await api.post(`learning/${planId}/${reqId}/submit`, { json: data })
  },

  gradeSubmission: async (submissionId: string, data: Record<string, unknown> | FormData) => {
    const json = data instanceof FormData ? Object.fromEntries(data.entries()) : data
    await api.post(`submissions/${submissionId}/grade`, { json })
  },

  fetchAssessments: async () => {
    set({ isLoading: true })
    const res = await api.get('assessments').json<{
      submissions: PracticalSubmission[]
      employees: Record<string, Employee>
    }>()
    set({ submissions: res.submissions, assessmentEmployees: res.employees, isLoading: false })
  },
}))
