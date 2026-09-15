import client from './client'
import type { Conversation, Message, QueryResponse, SearchResult } from '../types'

export const queryApi = {
  ask: (
    repositoryId: string,
    question: string,
    conversationId?: string,
    includeGraph = false,
  ) =>
    client
      .post<QueryResponse>(`/repositories/${repositoryId}/query`, {
        question,
        conversation_id: conversationId ?? null,
        include_graph: includeGraph,
      })
      .then((r) => r.data),

  conversations: (repositoryId: string) =>
    client
      .get<Conversation[]>(`/repositories/${repositoryId}/conversations`)
      .then((r) => r.data),

  messages: (repositoryId: string, conversationId: string) =>
    client
      .get<Message[]>(
        `/repositories/${repositoryId}/conversations/${conversationId}/messages`,
      )
      .then((r) => r.data),

  search: (repositoryId: string, query: string, topK = 20) =>
    client
      .post<SearchResult[]>(`/repositories/${repositoryId}/search`, {
        query,
        top_k: topK,
      })
      .then((r) => r.data),
}
