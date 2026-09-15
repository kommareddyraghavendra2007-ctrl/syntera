import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  MessageSquare, GitBranch, Search, BookOpen,
  Code2, RefreshCw, FileCode2, Layers, GitCommit, Globe,
} from 'lucide-react'
import { repoApi } from '../api/repositories'
import StatusBadge from '../components/ui/StatusBadge'
import IndexingProgress from '../components/ui/IndexingProgress'
import Spinner from '../components/ui/Spinner'
import { formatNumber, LANGUAGE_COLORS } from '../utils'

export default function RepositoryOverview() {
  const { repositoryId } = useParams<{ repositoryId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: repo, isLoading } = useQuery({
    queryKey: ['repository', repositoryId],
    queryFn: () => repoApi.status(repositoryId!),
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s && !['READY', 'FAILED'].includes(s) ? 2000 : false
    },
    enabled: !!repositoryId,
  })

  const reindexMut = useMutation({
    mutationFn: () => repoApi.reindex(repositoryId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['repository', repositoryId] }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner className="h-8 w-8 text-syntera-400" />
      </div>
    )
  }
  if (!repo) return null

  const langs = Object.entries(repo.languages ?? {}).sort(([, a], [, b]) => b - a)
  const isReady = repo.status === 'READY'

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{repo.name}</h1>
          {repo.source_url && (
            <a
              href={repo.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-syntera-400 hover:underline flex items-center gap-1 mt-1"
            >
              <Globe size={12} />
              {repo.source_url}
            </a>
          )}
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={repo.status} />
          {isReady && (
            <button
              className="btn-ghost text-xs"
              onClick={() => reindexMut.mutate()}
              disabled={reindexMut.isPending}
            >
              <RefreshCw size={12} />
              Re-index
            </button>
          )}
        </div>
      </div>

      {/* Progress bar while indexing */}
      {!isReady && repo.status !== 'FAILED' && (
        <div className="card p-4">
          <IndexingProgress status={repo.status} detail={repo.status_detail} />
        </div>
      )}

      {repo.status === 'FAILED' && (
        <div className="card p-4 border-red-900/50 bg-red-900/10">
          <p className="text-red-400 text-sm font-medium mb-1">Indexing failed</p>
          <p className="text-red-500 text-xs">{repo.error_message}</p>
        </div>
      )}

      {/* Stats */}
      {isReady && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Files', value: formatNumber(repo.file_count), icon: FileCode2 },
            { label: 'Symbols', value: formatNumber(repo.symbol_count), icon: Layers },
            { label: 'Relationships', value: formatNumber(repo.relationship_count), icon: GitBranch },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="card p-4 text-center">
              <Icon size={20} className="text-syntera-400 mx-auto mb-2" />
              <p className="text-2xl font-bold text-white">{value}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Metadata */}
      <div className="card p-5 space-y-3">
        <h3 className="text-sm font-semibold text-white">Repository Info</h3>
        {[
          { label: 'Branch', value: repo.branch, icon: GitBranch },
          { label: 'Commit', value: repo.commit_sha?.slice(0, 10), icon: GitCommit },
          { label: 'Source', value: repo.source_type.toUpperCase(), icon: Globe },
        ]
          .filter((r) => r.value)
          .map(({ label, value, icon: Icon }) => (
            <div key={label} className="flex items-center gap-3 text-sm">
              <Icon size={13} className="text-gray-500" />
              <span className="text-gray-500 w-20">{label}</span>
              <span className="text-gray-300 font-mono text-xs">{value}</span>
            </div>
          ))}

        {langs.length > 0 && (
          <div className="flex items-center gap-3 text-sm">
            <Code2 size={13} className="text-gray-500" />
            <span className="text-gray-500 w-20">Languages</span>
            <div className="flex gap-1.5 flex-wrap">
              {langs.map(([lang, count]) => (
                <span
                  key={lang}
                  className="text-[10px] px-2 py-0.5 rounded-full font-medium text-white"
                  style={{ backgroundColor: LANGUAGE_COLORS[lang] ?? '#555', opacity: 0.85 }}
                  title={`${count} files`}
                >
                  {lang}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      {isReady && (
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: 'Ask a Question', desc: 'Natural language queries about your code', icon: MessageSquare, to: 'chat' },
            { label: 'Architecture Graph', desc: 'Visual map of modules and relationships', icon: GitBranch, to: 'architecture' },
            { label: 'Code Explorer', desc: 'Browse symbols with full context', icon: Code2, to: 'explorer' },
            { label: 'Search Code', desc: 'Semantic and lexical symbol search', icon: Search, to: 'search' },
          ].map(({ label, desc, icon: Icon, to }) => (
            <button
              key={to}
              onClick={() => navigate(`/repo/${repositoryId}/${to}`)}
              className="card p-5 text-left hover:border-syntera-800/60 transition-colors group"
            >
              <Icon size={18} className="text-syntera-400 mb-2" />
              <p className="text-sm font-semibold text-white group-hover:text-syntera-300 transition-colors">
                {label}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
