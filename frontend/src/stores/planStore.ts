import { create } from 'zustand'
import api from '@/lib/api'
import type { Plan, Employee, PlanReview, Comparison } from '@/types'

interface PlanState {
  plans: Plan[]
  employees: Record<string, Employee>
  currentPlan: Plan | null
  currentEmployee: Employee | null
  teaching: { passed: boolean; findings: string[] } | null
  fresh: boolean
  decisions: PlanReview[]
  comparison: Comparison | null
  alternatives: Plan[]
  isLoading: boolean
  fetchPlans: () => Promise<void>
  fetchPlan: (id: string) => Promise<void>
  reviewPlan: (id: string, data: Record<string, string>) => Promise<void>
  regeneratePlan: (id: string) => Promise<string>
  editItem: (planId: string, reqId: string, data: Record<string, unknown> | FormData) => Promise<string>
  fetchEditItem: (planId: string, reqId: string) => Promise<{ plan: Plan; item: Record<string, unknown> }>
  fetchCompare: (planId: string, otherId?: string) => Promise<void>
  fetchUpdatePreview: (planId: string) => Promise<Record<string, unknown>>
  triggerUpdate: (planId: string) => Promise<string>
  runConsistency: (planId: string) => Promise<string>
}

export const usePlanStore = create<PlanState>((set) => ({
  plans: [],
  employees: {},
  currentPlan: null,
  currentEmployee: null,
  teaching: null,
  fresh: false,
  decisions: [],
  comparison: null,
  alternatives: [],
  isLoading: false,

  fetchPlans: async () => {
    set({ isLoading: true })
    const res = await api.get('plans').json<{ plans: Plan[]; employees: Record<string, Employee> }>()
    set({ plans: res.plans, employees: res.employees, isLoading: false })
  },

  fetchPlan: async (id: string) => {
    set({ isLoading: true })
    const res = await api.get(`plans/${id}`).json<{
      plan: Plan
      employee: Employee
      teaching: { passed: boolean; findings: string[] }
      fresh: boolean
      decisions: PlanReview[]
    }>()
    set({
      currentPlan: res.plan,
      currentEmployee: res.employee,
      teaching: res.teaching,
      fresh: res.fresh,
      decisions: res.decisions,
      isLoading: false,
    })
  },

  reviewPlan: async (id: string, data: Record<string, string>) => {
    await api.post(`plans/${id}/review`, { json: data })
  },

  regeneratePlan: async (id: string) => {
    const res = await api.post(`plans/${id}/regenerate`).json<{ job_id: string }>()
    return res.job_id
  },

  editItem: async (planId: string, reqId: string, data: Record<string, unknown> | FormData) => {
    const json = data instanceof FormData ? Object.fromEntries(data.entries()) : data
    const res = await api.post(`plans/${planId}/items/${reqId}/edit`, { json }).json<{ plan_id: string }>()
    return res.plan_id
  },

  fetchEditItem: async (planId: string, reqId: string) => {
    return api.get(`plans/${planId}/items/${reqId}/edit`).json()
  },

  fetchCompare: async (planId: string, otherId?: string) => {
    set({ isLoading: true })
    const params = otherId ? `?other=${otherId}` : ''
    const res = await api.get(`plans/${planId}/compare${params}`).json<{
      left: Plan
      right: Plan | null
      alternatives: Plan[]
      comparison: Comparison | null
    }>()
    set({
      currentPlan: res.left,
      alternatives: res.alternatives,
      comparison: res.comparison ? {
        ...res.comparison,
        rows: res.comparison.rows.map(row => ({ ...row, left: row.before, right: row.after })),
      } : null,
      isLoading: false,
    })
  },

  fetchUpdatePreview: async (planId: string) => {
    return api.get(`plans/${planId}/update`).json()
  },

  triggerUpdate: async (planId: string) => {
    const res = await api.post(`plans/${planId}/update`).json<{ job_id: string }>()
    return res.job_id
  },

  runConsistency: async (planId: string) => {
    const res = await api.post(`plans/${planId}/consistency`).json<{ experiment_id: string }>()
    return res.experiment_id
  },
}))
