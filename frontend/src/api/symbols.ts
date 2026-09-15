import client from './client'
import type { GraphData, Symbol, SymbolDetail } from '../types'

export const symbolsApi = {
  list: (repositoryId: string, params?: { symbol_type?: string; file_path?: string; limit?: number }) =>
    client
      .get<Symbol[]>(`/repositories/${repositoryId}/symbols`, { params })
      .then((r) => r.data),

  get: (repositoryId: string, symbolId: string) =>
    client
      .get<SymbolDetail>(`/repositories/${repositoryId}/symbols/${symbolId}`)
      .then((r) => r.data),

  graph: (repositoryId: string, rootSymbol?: string, depth = 2) =>
    client
      .get<GraphData>(`/repositories/${repositoryId}/graph`, {
        params: { root_symbol: rootSymbol, depth },
      })
      .then((r) => r.data),

  impact: (repositoryId: string, symbolId: string) =>
    client
      .get<Record<string, unknown>>(`/repositories/${repositoryId}/graph/impact/${symbolId}`)
      .then((r) => r.data),
}
