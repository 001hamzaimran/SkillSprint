import { create } from 'zustand'
import api from '@/lib/api'
import type { Employee, Role, User } from '@/types'

interface EmployeeState {
  employees: Employee[]
  roles: Role[]
  managers: User[]
  accounts: User[]
  isLoading: boolean
  fetchEmployees: () => Promise<void>
  addEmployee: (data: Record<string, string>) => Promise<void>
  generatePlan: (employeeId: string) => Promise<string>
  linkAccount: (employeeId: string, userId: string) => Promise<void>
}

export const useEmployeeStore = create<EmployeeState>((set) => ({
  employees: [],
  roles: [],
  managers: [],
  accounts: [],
  isLoading: false,

  fetchEmployees: async () => {
    set({ isLoading: true })
    const res = await api.get('employees').json<{
      employees: Employee[]
      roles: Role[]
      managers: User[]
      accounts: User[]
    }>()
    set({ ...res, isLoading: false })
  },

  addEmployee: async (data: Record<string, string>) => {
    await api.post('employees', { json: data })
  },

  generatePlan: async (employeeId: string) => {
    const res = await api.post(`employees/${employeeId}/generate`).json<{ job_id: string }>()
    return res.job_id
  },

  linkAccount: async (employeeId: string, userId: string) => {
    await api.post(`employees/${employeeId}/account`, { json: { user_id: userId } })
  },
}))
