import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { GitBranch, RefreshCw, Search } from 'lucide-react'
import { symbolsApi } from '../api/symbols'
import Spinner from '../components/ui/Spinner'
import { symbolTypeColor, LANGUAGE_COLORS } from '../utils'
import type { GraphData } from '../types'

const NODE_COLORS: Record<string, string> = {
  class:         '#4f46e5',
  function:      '#2563eb',
  method:        '#0891b2',
  interface:     '#16a34a',
  endpoint:      '#ea580c',
  file:          '#64748b',
  configuration: '#ca8a04',
  module:        '#7c3aed',
  default:       '#374151',
}

function graphToFlow(data: GraphData): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = data.nodes.map((n, i) => ({
    id: n.id,
    position: {
      x: (i % 8) * 200,
      y: Math.floor(i / 8) * 120,
    },
    data: {
      label: n.label.length > 30 ? n.label.slice(0, 27) + '…' : n.label,
      type: n.symbol_type,
      file: n.file_path,
      line: n.start_line,
    },
    style: {
      background: NODE_COLORS[n.symbol_type] ?? NODE_COLORS.default,
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 6,
      color: '#fff',
      fontSize: 11,
      padding: '6px 10px',
      minWidth: 120,
    },
  }))

  const edges: Edge[] = data.edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: e.relation_type,
    style: { stroke: 'rgba(255,255,255,0.15)', strokeWidth: 1 },
    labelStyle: { fill: '#6b7280', fontSize: 9 },
    markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(255,255,255,0.2)' },
  }))

  return { nodes, edges }
}

export default function Architecture() {
  const { repositoryId } = useParams<{ repositoryId: string }>()
  const [rootSymbol, setRootSymbol] = useState('')
  const [depth, setDepth] = useState(2)
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['graph', repositoryId, rootSymbol, depth],
    queryFn: () => symbolsApi.graph(repositoryId!, rootSymbol || undefined, depth),
    enabled: !!repositoryId,
  })

  useEffect(() => {
    if (!data) return
    const { nodes: n, edges: e } = graphToFlow(data)
    setNodes(n)
    setEdges(e)
  }, [data])

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-surface-border bg-surface-secondary">
        <GitBranch size={15} className="text-syntera-400" />
        <h2 className="text-sm font-semibold text-white mr-2">Architecture Graph</h2>

        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-8 h-8 text-xs w-52"
            placeholder="Root symbol (optional)…"
            value={rootSymbol}
            onChange={(e) => setRootSymbol(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && refetch()}
          />
        </div>

        <label className="flex items-center gap-2 text-xs text-gray-400">
          Depth
          <select
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="input h-8 text-xs w-16 py-0"
          >
            {[1, 2, 3, 4].map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </label>

        <button className="btn-ghost text-xs" onClick={() => refetch()}>
          <RefreshCw size={12} />
          Refresh
        </button>

        {data && (
          <span className="ml-auto text-xs text-gray-500">
            {data.nodes.length} nodes · {data.edges.length} edges
          </span>
        )}
      </div>

      {/* Graph */}
      <div className="flex-1 relative">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Spinner className="h-8 w-8 text-syntera-400" />
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            style={{ background: '#0f1117' }}
          >
            <Background color="#1e2432" gap={24} />
            <Controls
              style={{ background: '#161b25', border: '1px solid #2a3142' }}
            />
            <MiniMap
              style={{ background: '#161b25', border: '1px solid #2a3142' }}
              nodeColor={(n) => NODE_COLORS[n.data?.type] ?? NODE_COLORS.default}
            />
          </ReactFlow>
        )}

        {data?.nodes.length === 0 && !isLoading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <GitBranch size={48} className="text-syntera-700 mx-auto mb-4" />
              <p className="text-gray-500">No graph data found.</p>
              <p className="text-xs text-gray-600 mt-1">Try a different root symbol or depth.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
