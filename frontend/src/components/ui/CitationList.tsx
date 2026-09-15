import { ExternalLink, FileCode } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { cn, symbolTypeColor } from '../../utils'
import type { Citation } from '../../types'

interface Props {
  citations: Citation[]
  className?: string
}

export default function CitationList({ citations, className }: Props) {
  const navigate = useNavigate()
  const { repositoryId } = useParams()

  if (!citations.length) return null

  return (
    <div className={cn('space-y-1', className)}>
      <p className="text-[10px] uppercase tracking-widest text-gray-600 font-semibold mb-2">
        Source Evidence
      </p>
      {citations.map((c, i) => (
        <button
          key={i}
          onClick={() =>
            repositoryId &&
            navigate(
              `/repo/${repositoryId}/explorer?symbol=${c.symbol_id ?? ''}&file=${encodeURIComponent(c.file_path)}`,
            )
          }
          className="w-full text-left flex items-start gap-2 px-2 py-1.5 rounded hover:bg-surface-tertiary transition-colors group"
          title={`${c.file_path}:${c.start_line}-${c.end_line}`}
        >
          <FileCode size={12} className="mt-0.5 flex-shrink-0 text-gray-500" />
          <div className="min-w-0">
            <span className={cn('text-xs font-medium', symbolTypeColor(c.symbol_type ?? ''))}>
              {c.symbol_name ?? c.file_path.split('/').pop()}
            </span>
            <span className="text-gray-600 text-xs mx-1">·</span>
            <span className="text-gray-500 text-xs truncate">
              {c.file_path}
              {c.start_line != null && `:${c.start_line}`}
              {c.end_line != null && c.end_line !== c.start_line && `-${c.end_line}`}
            </span>
          </div>
          <ExternalLink size={10} className="ml-auto flex-shrink-0 text-gray-700 group-hover:text-gray-400 mt-0.5" />
        </button>
      ))}
    </div>
  )
}
