import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Upload, FolderGit2, FileCode2, Layers, RefreshCw, Trash2 } from 'lucide-react'
import { repoApi } from '../api/repositories'
import StatusBadge from '../components/ui/StatusBadge'
import Spinner from '../components/ui/Spinner'
import { formatNumber, relativeTime, LANGUAGE_COLORS } from '../utils'
import type { Repository } from '../types'

export default function Dashboard() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showAddModal, setShowAddModal] = useState(false)

  const { data: repos = [], isLoading } = useQuery({
    queryKey: ['repositories'],
    queryFn: repoApi.list,
    refetchInterval: (query) => {
      const data = query.state.data as Repository[] | undefined
      const hasActive = data?.some(
        (r) => !['READY', 'FAILED'].includes(r.status),
      )
      return hasActive ? 3000 : false
    },
  })

  const deleteMut = useMutation({
    mutationFn: repoApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['repositories'] }),
  })

  const topLanguages = (r: Repository) =>
    Object.entries(r.languages)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3)

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Repositories</h1>
          <p className="text-sm text-gray-500 mt-1">
            {repos.length} repository{repos.length !== 1 ? 'ies' : ''} indexed
          </p>
        </div>
        <div className="flex gap-3">
          <button className="btn-secondary" onClick={() => setShowAddModal(true)}>
            <Upload size={14} />
            Upload ZIP
          </button>
          <button className="btn-primary" onClick={() => setShowAddModal(true)}>
            <Plus size={14} />
            Add Repository
          </button>
        </div>
      </div>

      {/* Repository grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Spinner className="h-8 w-8 text-syntera-400" />
        </div>
      ) : repos.length === 0 ? (
        <EmptyState onAdd={() => setShowAddModal(true)} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {repos.map((repo) => (
            <RepoCard
              key={repo.id}
              repo={repo}
              onOpen={() => navigate(`/repo/${repo.id}`)}
              onDelete={() => {
                if (confirm(`Delete "${repo.name}"?`)) deleteMut.mutate(repo.id)
              }}
              topLanguages={topLanguages(repo)}
            />
          ))}
        </div>
      )}

      {showAddModal && (
        <AddRepoModal
          onClose={() => setShowAddModal(false)}
          onCreated={() => {
            setShowAddModal(false)
            qc.invalidateQueries({ queryKey: ['repositories'] })
          }}
        />
      )}
    </div>
  )
}

function RepoCard({
  repo, onOpen, onDelete, topLanguages,
}: {
  repo: Repository
  onOpen: () => void
  onDelete: () => void
  topLanguages: [string, number][]
}) {
  return (
    <div className="card p-5 hover:border-surface-border/80 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <FolderGit2 size={16} className="text-syntera-400 flex-shrink-0" />
          <h3 className="font-semibold text-white text-sm">{repo.name}</h3>
        </div>
        <StatusBadge status={repo.status} />
      </div>

      {repo.source_url && (
        <p className="text-xs text-gray-500 mb-3 truncate">{repo.source_url}</p>
      )}

      <div className="flex gap-4 text-xs text-gray-500 mb-4">
        <span className="flex items-center gap-1"><FileCode2 size={11} />{formatNumber(repo.file_count)} files</span>
        <span className="flex items-center gap-1"><Layers size={11} />{formatNumber(repo.symbol_count)} symbols</span>
        <span className="ml-auto">{relativeTime(repo.created_at)}</span>
      </div>

      {topLanguages.length > 0 && (
        <div className="flex gap-1.5 mb-4">
          {topLanguages.map(([lang]) => (
            <span
              key={lang}
              className="text-[10px] px-2 py-0.5 rounded-full font-medium text-white"
              style={{ backgroundColor: LANGUAGE_COLORS[lang] ?? '#555', opacity: 0.85 }}
            >
              {lang}
            </span>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={onOpen}
          disabled={repo.status !== 'READY'}
          className="btn-primary text-xs py-1.5 flex-1 justify-center"
        >
          Open Repository
        </button>
        <button
          onClick={onDelete}
          className="btn-ghost text-xs py-1.5 text-red-400 hover:text-red-300 hover:bg-red-900/20"
          title="Delete"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  )
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="card p-16 text-center">
      <FolderGit2 size={48} className="text-syntera-700 mx-auto mb-4" />
      <h3 className="text-lg font-semibold text-white mb-2">No repositories yet</h3>
      <p className="text-sm text-gray-500 mb-6 max-w-sm mx-auto">
        Add a public Git repository or upload a ZIP to start asking questions about your codebase.
      </p>
      <button className="btn-primary mx-auto" onClick={onAdd}>
        <Plus size={14} />
        Add your first repository
      </button>
    </div>
  )
}

function AddRepoModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [tab, setTab] = useState<'url' | 'zip'>('url')
  const [url, setUrl] = useState('')
  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')

  const createMut = useMutation({
    mutationFn: () =>
      tab === 'url' ? repoApi.create(url, undefined, name || undefined) : repoApi.uploadZip(file!, name),
    onSuccess: onCreated,
    onError: (e: Error) => setError(e.message),
  })

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Add Repository</h2>

        <div className="flex gap-2 mb-5">
          {(['url', 'zip'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={tab === t ? 'btn-primary py-1.5 text-xs' : 'btn-secondary py-1.5 text-xs'}
            >
              {t === 'url' ? 'Git URL' : 'Upload ZIP'}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          {tab === 'url' ? (
            <input
              className="input"
              placeholder="https://github.com/owner/repository"
              value={url}
              onChange={(e) => { setUrl(e.target.value); setError('') }}
            />
          ) : (
            <input
              type="file"
              accept=".zip"
              className="input py-1.5"
              onChange={(e) => { setFile(e.target.files?.[0] ?? null); setError('') }}
            />
          )}
          <input
            className="input"
            placeholder="Display name (optional)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        {error && <p className="text-red-400 text-sm mt-3">{error}</p>}

        <div className="flex justify-end gap-3 mt-6">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn-primary"
            disabled={createMut.isPending || (tab === 'url' ? !url : !file)}
            onClick={() => createMut.mutate()}
          >
            {createMut.isPending ? <Spinner className="h-3.5 w-3.5" /> : null}
            {createMut.isPending ? 'Adding…' : 'Add Repository'}
          </button>
        </div>
      </div>
    </div>
  )
}
