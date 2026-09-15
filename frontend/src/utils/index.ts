import { clsx, type ClassValue } from 'clsx'
import type { IndexStatus } from '../types'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

export function relativeTime(date: string): string {
  const diff = Date.now() - new Date(date).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export const STATUS_LABELS: Record<IndexStatus, string> = {
  QUEUED: 'Queued',
  CLONING: 'Cloning',
  SCANNING: 'Scanning',
  PARSING: 'Parsing',
  EXTRACTING_SYMBOLS: 'Extracting Symbols',
  BUILDING_GRAPH: 'Building Graph',
  GENERATING_EMBEDDINGS: 'Generating Embeddings',
  INDEXING: 'Indexing',
  VALIDATING: 'Validating',
  READY: 'Ready',
  FAILED: 'Failed',
}

export const STATUS_STEP: Record<IndexStatus, number> = {
  QUEUED: 0, CLONING: 1, SCANNING: 2, PARSING: 3,
  EXTRACTING_SYMBOLS: 4, BUILDING_GRAPH: 5,
  GENERATING_EMBEDDINGS: 6, INDEXING: 7,
  VALIDATING: 8, READY: 9, FAILED: -1,
}

export const SYMBOL_TYPE_COLORS: Record<string, string> = {
  class: 'text-purple-400',
  function: 'text-blue-400',
  method: 'text-cyan-400',
  interface: 'text-green-400',
  endpoint: 'text-orange-400',
  file: 'text-gray-400',
  configuration: 'text-yellow-400',
  test: 'text-pink-400',
  default: 'text-gray-400',
}

export function symbolTypeColor(type: string): string {
  return SYMBOL_TYPE_COLORS[type] ?? SYMBOL_TYPE_COLORS.default
}

export const LANGUAGE_COLORS: Record<string, string> = {
  python: '#3572A5',
  javascript: '#f1e05a',
  typescript: '#3178c6',
  java: '#b07219',
  go: '#00ADD8',
  cpp: '#f34b7d',
  c: '#555555',
  rust: '#dea584',
}
