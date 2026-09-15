import { cn } from '../../utils'
import type { IndexStatus } from '../../types'

const STATUS_STYLE: Record<IndexStatus, string> = {
  READY: 'bg-green-900/40 text-green-400 border-green-800',
  FAILED: 'bg-red-900/40 text-red-400 border-red-800',
  QUEUED: 'bg-gray-800 text-gray-400 border-gray-700',
  CLONING: 'bg-blue-900/40 text-blue-400 border-blue-800',
  SCANNING: 'bg-blue-900/40 text-blue-400 border-blue-800',
  PARSING: 'bg-purple-900/40 text-purple-400 border-purple-800',
  EXTRACTING_SYMBOLS: 'bg-purple-900/40 text-purple-400 border-purple-800',
  BUILDING_GRAPH: 'bg-yellow-900/40 text-yellow-400 border-yellow-800',
  GENERATING_EMBEDDINGS: 'bg-orange-900/40 text-orange-400 border-orange-800',
  INDEXING: 'bg-orange-900/40 text-orange-400 border-orange-800',
  VALIDATING: 'bg-teal-900/40 text-teal-400 border-teal-800',
}

const PULSE: IndexStatus[] = [
  'CLONING','SCANNING','PARSING','EXTRACTING_SYMBOLS',
  'BUILDING_GRAPH','GENERATING_EMBEDDINGS','INDEXING','VALIDATING',
]

interface Props { status: IndexStatus; className?: string }

export default function StatusBadge({ status, className }: Props) {
  const style = STATUS_STYLE[status] ?? 'bg-gray-800 text-gray-400 border-gray-700'
  const pulsing = PULSE.includes(status)

  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-xs font-medium', style, className)}>
      {pulsing && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-current" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current" />
        </span>
      )}
      {status.replace(/_/g, ' ')}
    </span>
  )
}
