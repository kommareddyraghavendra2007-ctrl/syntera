import { useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Code2, FileCode, ChevronRight, Layers, ArrowLeft } from 'lucide-react'
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python'
import typescript from 'react-syntax-highlighter/dist/esm/languages/hljs/typescript'
import javascript from 'react-syntax-highlighter/dist/esm/languages/hljs/javascript'
import java from 'react-syntax-highlighter/dist/esm/languages/hljs/java'
import go from 'react-syntax-highlighter/dist/esm/languages/hljs/go'
import cpp from 'react-syntax-highlighter/dist/esm/languages/hljs/cpp'
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs'
import { symbolsApi } from '../api/symbols'
import { repoApi } from '../api/repositories'
import Spinner from '../components/ui/Spinner'
import { cn, symbolTypeColor } from '../utils'
import type { Symbol } from '../types'

SyntaxHighlighter.registerLanguage('python', python)
SyntaxHighlighter.registerLanguage('typescript', typescript)
SyntaxHighlighter.registerLanguage('javascript', javascript)
SyntaxHighlighter.registerLanguage('java', java)
SyntaxHighlighter.registerLanguage('go', go)
SyntaxHighlighter.registerLanguage('cpp', cpp)

export default function CodeExplorer() {
  const { repositoryId } = useParams<{ repositoryId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedSymbolId = searchParams.get('symbol') || ''

  const { data: symbols = [], isLoading: loadingSymbols } = useQuery({
    queryKey: ['symbols', repositoryId],
    queryFn: () => symbolsApi.list(repositoryId!, { limit: 200 }),
    enabled: !!repositoryId,
  })

  const { data: symbolDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ['symbol', repositoryId, selectedSymbolId],
    queryFn: () => symbolsApi.get(repositoryId!, selectedSymbolId),
    enabled: !!repositoryId && !!selectedSymbolId,
  })

  const grouped = groupByFile(symbols)

  return (
    <div className="flex h-full overflow-hidden">
      {/* File / Symbol tree */}
      <div className="w-64 flex-shrink-0 border-r border-surface-border bg-surface-secondary overflow-y-auto">
        <div className="px-4 py-3 border-b border-surface-border">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
            Symbols
          </p>
          <p className="text-[10px] text-gray-600 mt-0.5">{symbols.length} total</p>
        </div>

        {loadingSymbols ? (
          <div className="flex justify-center py-8">
            <Spinner className="text-syntera-400" />
          </div>
        ) : (
          <div className="py-2">
            {Object.entries(grouped).map(([file, syms]) => (
              <FileGroup
                key={file}
                file={file}
                symbols={syms}
                selectedId={selectedSymbolId}
                onSelect={(id) => setSearchParams({ symbol: id })}
              />
            ))}
          </div>
        )}
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-y-auto">
        {!selectedSymbolId ? (
          <div className="flex items-center justify-center h-full text-center px-8">
            <div>
              <Code2 size={48} className="text-syntera-700 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">Code Explorer</h3>
              <p className="text-sm text-gray-500">
                Select a symbol from the list to view its source, documentation, and relationships.
              </p>
              <p className="text-xs text-gray-600 mt-2">Explorer is read-only.</p>
            </div>
          </div>
        ) : loadingDetail ? (
          <div className="flex items-center justify-center h-full">
            <Spinner className="h-8 w-8 text-syntera-400" />
          </div>
        ) : symbolDetail ? (
          <SymbolDetailView symbol={symbolDetail} />
        ) : null}
      </div>
    </div>
  )
}

function FileGroup({
  file, symbols, selectedId, onSelect,
}: {
  file: string
  symbols: Symbol[]
  selectedId: string
  onSelect: (id: string) => void
}) {
  const [open, setOpen] = useState(true)
  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-4 py-1.5 text-left hover:bg-surface-tertiary"
      >
        <ChevronRight size={10} className={cn('text-gray-500 transition-transform', open && 'rotate-90')} />
        <FileCode size={11} className="text-gray-500 flex-shrink-0" />
        <span className="text-[11px] text-gray-400 truncate">{file.split('/').pop()}</span>
      </button>
      {open && (
        <div className="pl-8">
          {symbols.map((s) => (
            <button
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={cn(
                'w-full text-left px-3 py-1 text-[11px] truncate rounded transition-colors',
                s.id === selectedId
                  ? 'bg-syntera-900/60 text-syntera-300'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-surface-tertiary',
              )}
            >
              <span className={cn('mr-1 font-mono', symbolTypeColor(s.symbol_type))}>
                {s.symbol_type[0].toUpperCase()}
              </span>
              {s.symbol_name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function SymbolDetailView({ symbol }: { symbol: import('../types').SymbolDetail }) {
  return (
    <div className="p-6 max-w-4xl space-y-5">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className={cn('text-lg font-bold', symbolTypeColor(symbol.symbol_type))}>
            {symbol.qualified_name}
          </span>
          <span className="badge-gray">{symbol.symbol_type}</span>
          {symbol.language && <span className="badge-blue">{symbol.language}</span>}
        </div>
        <p className="text-sm text-gray-500">
          <FileCode size={11} className="inline mr-1" />
          {symbol.file_path}:{symbol.start_line}–{symbol.end_line}
        </p>
      </div>

      {/* Documentation */}
      {symbol.documentation && (
        <div className="card p-4">
          <p className="text-[10px] uppercase tracking-widest text-gray-600 font-semibold mb-2">
            Documentation
          </p>
          <p className="text-sm text-gray-300 whitespace-pre-wrap">{symbol.documentation}</p>
        </div>
      )}

      {/* Source code */}
      {symbol.code && (
        <div className="card overflow-hidden">
          <div className="px-4 py-2 border-b border-surface-border flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-widest text-gray-600 font-semibold">
              Source
            </span>
            <span className="text-[10px] text-gray-600">
              Lines {symbol.start_line}–{symbol.end_line}
            </span>
          </div>
          <SyntaxHighlighter
            language={symbol.language ?? 'text'}
            style={atomOneDark}
            customStyle={{
              margin: 0,
              padding: '1rem',
              background: 'transparent',
              fontSize: '12px',
              lineHeight: '1.6',
            }}
            showLineNumbers
            startingLineNumber={symbol.start_line}
          >
            {symbol.code}
          </SyntaxHighlighter>
        </div>
      )}

      {/* Meta */}
      <div className="card p-4 space-y-2">
        <p className="text-[10px] uppercase tracking-widest text-gray-600 font-semibold mb-3">
          Metadata
        </p>
        {[
          { label: 'Module', value: symbol.module_name },
          { label: 'Class', value: symbol.class_name },
          { label: 'Parent', value: symbol.parent_symbol },
        ]
          .filter((r) => r.value)
          .map(({ label, value }) => (
            <div key={label} className="flex gap-3 text-sm">
              <span className="text-gray-600 w-20 flex-shrink-0">{label}</span>
              <span className="text-gray-400 font-mono text-xs">{value}</span>
            </div>
          ))}
      </div>
    </div>
  )
}

function groupByFile(symbols: Symbol[]): Record<string, Symbol[]> {
  return symbols.reduce<Record<string, Symbol[]>>((acc, s) => {
    const key = s.file_path
    if (!acc[key]) acc[key] = []
    acc[key].push(s)
    return acc
  }, {})
}
