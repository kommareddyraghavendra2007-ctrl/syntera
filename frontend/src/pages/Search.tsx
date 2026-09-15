import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Search as SearchIcon, FileCode, ChevronRight } from 'lucide-react'
import { queryApi } from '../api/query'
import Spinner from '../components/ui/Spinner'
import { cn, symbolTypeColor } from '../utils'
import type { SearchResult } from '../types'

export default function Search() {
  const { repositoryId } = useParams<{ repositoryId: string }>()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  const searchMut = useMutation({
    mutationFn: (q: string) => queryApi.search(repositoryId!, q, 30),
  })

  const handleSearch = () => {
    const q = query.trim()
    if (!q) return
    searchMut.mutate(q)
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">Code Search</h1>
        <p className="text-sm text-gray-500">
          Hybrid search: semantic similarity + BM25 keyword matching + exact symbol lookup.
        </p>
      </div>

      {/* Search bar */}
      <div className="flex gap-3 mb-8">
        <div className="relative flex-1">
          <SearchIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-9"
            placeholder="Search functions, classes, methods, or natural language…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            autoFocus
          />
        </div>
        <button
          className="btn-primary"
          onClick={handleSearch}
          disabled={!query.trim() || searchMut.isPending}
        >
          {searchMut.isPending ? <Spinner className="h-4 w-4" /> : <SearchIcon size={14} />}
          Search
        </button>
      </div>

      {/* Results */}
      {searchMut.data && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 mb-4">
            {searchMut.data.length} result{searchMut.data.length !== 1 ? 's' : ''}
          </p>
          {searchMut.data.length === 0 ? (
            <div className="card p-8 text-center">
              <p className="text-gray-500">No results found for "{query}"</p>
            </div>
          ) : (
            searchMut.data.map((r, i) => (
              <SearchResultCard
                key={i}
                result={r}
                onClick={() =>
                  navigate(
                    `/repo/${repositoryId}/explorer?symbol=${r.symbol_id ?? ''}&file=${encodeURIComponent(r.file_path)}`,
                  )
                }
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}

function SearchResultCard({ result, onClick }: { result: SearchResult; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="card w-full text-left p-4 hover:border-syntera-800/60 transition-colors group"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn('text-sm font-semibold', symbolTypeColor(result.symbol_type ?? ''))}>
              {result.symbol_name ?? result.file_path.split('/').pop()}
            </span>
            {result.symbol_type && (
              <span className="badge-gray text-[10px]">{result.symbol_type}</span>
            )}
            {result.language && (
              <span className="badge-blue text-[10px]">{result.language}</span>
            )}
          </div>
          <p className="text-xs text-gray-500 truncate">
            <FileCode size={10} className="inline mr-1" />
            {result.file_path}
            {result.start_line != null && `:${result.start_line}`}
          </p>
          {result.code_snippet && (
            <pre className="text-[11px] text-gray-400 font-mono mt-2 bg-surface rounded px-2 py-1 overflow-hidden line-clamp-2">
              {result.code_snippet.slice(0, 200)}
            </pre>
          )}
        </div>
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          <span className="text-[10px] text-gray-600">
            {(result.score * 100).toFixed(0)}%
          </span>
          <ChevronRight size={14} className="text-gray-600 group-hover:text-gray-400" />
        </div>
      </div>
    </button>
  )
}
