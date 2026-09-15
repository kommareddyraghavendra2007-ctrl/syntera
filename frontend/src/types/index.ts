// ── Repository ──────────────────────────────────────────────────────────────

export interface Repository {
  id: string
  name: string
  source_type: 'git' | 'zip'
  source_url: string | null
  branch: string | null
  commit_sha: string | null
  status: IndexStatus
  status_detail: string | null
  error_message: string | null
  file_count: number
  symbol_count: number
  relationship_count: number
  languages: Record<string, number>
  indexing_started_at: string | null
  indexing_finished_at: string | null
  created_at: string
}

export type IndexStatus =
  | 'QUEUED'
  | 'CLONING'
  | 'SCANNING'
  | 'PARSING'
  | 'EXTRACTING_SYMBOLS'
  | 'BUILDING_GRAPH'
  | 'GENERATING_EMBEDDINGS'
  | 'INDEXING'
  | 'VALIDATING'
  | 'READY'
  | 'FAILED'

// ── Query / Answer ───────────────────────────────────────────────────────────

export interface Citation {
  symbol_id: string | null
  symbol_name: string | null
  symbol_type: string | null
  file_path: string
  start_line: number | null
  end_line: number | null
  language: string | null
  score: number | null
}

export interface QueryResponse {
  answer: string
  citations: Citation[]
  intent: string
  confidence: string
  conversation_id: string | null
  retrieval_stats: Record<string, unknown>
  graph_data: GraphData | null
}

// ── Symbols ──────────────────────────────────────────────────────────────────

export interface Symbol {
  id: string
  repository_id: string
  file_path: string
  language: string | null
  symbol_type: string
  symbol_name: string
  qualified_name: string
  class_name: string | null
  start_line: number
  end_line: number
}

export interface SymbolDetail extends Symbol {
  code: string
  documentation: string | null
  parent_symbol: string | null
  module_name: string | null
}

export interface SearchResult {
  symbol_id: string | null
  symbol_name: string | null
  qualified_name: string | null
  symbol_type: string | null
  file_path: string
  start_line: number | null
  end_line: number | null
  language: string | null
  score: number
  code_snippet: string | null
}

// ── Graph ────────────────────────────────────────────────────────────────────

export interface GraphNode {
  id: string
  label: string
  symbol_type: string
  file_path: string
  start_line: number
  language: string | null
}

export interface GraphEdge {
  source: string
  target: string
  relation_type: string
  confidence: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  repository_id: string
  root_symbol: string | null
}

// ── Conversation ─────────────────────────────────────────────────────────────

export interface Conversation {
  id: string
  repository_id: string
  title: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
}
