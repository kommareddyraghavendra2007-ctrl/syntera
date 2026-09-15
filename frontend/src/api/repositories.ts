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

  uploadZip: (file: File, name: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('name', name)
    return client
      .post<Repository>('/repositories/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  delete: (id: string) =>
    client.delete(`/repositories/${id}`),

  reindex: (id: string) =>
    client.post<Repository>(`/repositories/${id}/reindex`).then((r) => r.data),
}
