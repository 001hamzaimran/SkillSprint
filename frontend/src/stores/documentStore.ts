import { create } from 'zustand'
import api from '@/lib/api'
import type { Document, SourceSection, Requirement, Job, Role } from '@/types'

interface DocumentState {
  documents: Document[]
  currentDocument: Document | null
  sections: SourceSection[]
  requirements: Requirement[]
  jobs: Job[]
  roles: Role[]
  searchQuery: string
  isLoading: boolean
  fetchDocuments: (q?: string) => Promise<void>
  fetchDocument: (id: string) => Promise<void>
  uploadDocument: (form: FormData) => Promise<Document>
  activateDocument: (id: string) => Promise<void>
  extractRequirements: (id: string) => Promise<string>
  reviewRequirement: (id: string, data: Record<string, string>) => Promise<void>
  annotateRules: (id: string, data: Record<string, unknown> | FormData) => Promise<void>
  setSearchQuery: (q: string) => void
}

export const useDocumentStore = create<DocumentState>((set) => ({
  documents: [],
  currentDocument: null,
  sections: [],
  requirements: [],
  jobs: [],
  roles: [],
  searchQuery: '',
  isLoading: false,

  fetchDocuments: async (q?: string) => {
    set({ isLoading: true })
    const params = q ? `?q=${encodeURIComponent(q)}` : ''
    const res = await api.get(`documents${params}`).json<{ documents: Document[]; roles: Role[] }>()
    set({ documents: res.documents, roles: res.roles, isLoading: false })
  },

  fetchDocument: async (id: string) => {
    set({ isLoading: true })
    const res = await api.get(`documents/${id}`).json<{
      document: Document
      sections: SourceSection[]
      requirements: Requirement[]
      jobs: Job[]
      roles: Role[]
    }>()
    set({
      currentDocument: res.document,
      sections: res.sections,
      requirements: res.requirements,
      jobs: res.jobs,
      roles: res.roles,
      isLoading: false,
    })
  },

  uploadDocument: async (form: FormData) => {
    const res = await api.post('documents/upload', { body: form }).json<{ document: Document }>()
    return res.document
  },

  activateDocument: async (id: string) => {
    await api.post(`documents/${id}/activate`)
  },

  extractRequirements: async (id: string) => {
    const res = await api.post(`documents/${id}/extract`).json<{ job_id: string }>()
    return res.job_id
  },

  reviewRequirement: async (id: string, data: Record<string, string>) => {
    await api.post(`requirements/${id}/review`, { json: data })
  },

  annotateRules: async (id: string, data: Record<string, unknown> | FormData) => {
    const json = data instanceof FormData ? Object.fromEntries(data.entries()) : data
    await api.post(`requirements/${id}/rules`, { json })
  },

  setSearchQuery: (q: string) => set({ searchQuery: q }),
}))
