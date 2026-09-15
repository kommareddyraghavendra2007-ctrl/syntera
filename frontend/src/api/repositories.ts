import client from './client'
import type { Repository } from '../types'

export const repoApi = {
  list: () =>
    client.get<Repository[]>('/repositories').then((r) => r.data),

  get: (id: string) =>
    client.get<Repository>(`/repositories/${id}`).then((r) => r.data),

  status: (id: string) =>
    client.get<Repository>(`/repositories/${id}/status`).then((r) => r.data),

  create: (url: string, branch?: string, name?: string) =>
    client
      .post<Repository>('/repositories', { url, branch, name })
      .then((r) => r.data),

  uploadZip: (file: File, name: string, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    form.append('name', name)
    // Do NOT set Content-Type manually — browser must set it with the boundary
    return client
      .post<Repository>('/repositories/upload', form, {
        onUploadProgress: (e) => {
          if (onProgress && e.total) {
            onProgress(Math.round((e.loaded * 100) / e.total))
          }
        },
      })
      .then((r) => r.data)
  },

  delete: (id: string) =>
    client.delete(`/repositories/${id}`),

  reindex: (id: string) =>
    client.post<Repository>(`/repositories/${id}/reindex`).then((r) => r.data),
}
