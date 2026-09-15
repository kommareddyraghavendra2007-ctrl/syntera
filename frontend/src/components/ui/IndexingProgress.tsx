import { STATUS_STEP, STATUS_LABELS } from '../../utils'
import type { IndexStatus } from '../../types'

const STEPS: IndexStatus[] = [
  'CLONING','SCANNING','PARSING','EXTRACTING_SYMBOLS',
  'BUILDING_GRAPH','GENERATING_EMBEDDINGS','INDEXING','VALIDATING','READY',
]

interface Props {
  status: IndexStatus
  detail?: string | null
}

export default function IndexingProgress({ status, detail }: Props) {
  const currentStep = STATUS_STEP[status]
  const totalSteps = STEPS.length

  if (status === 'READY' || status === 'FAILED' || status === 'QUEUED') return null

  const pct = Math.round((currentStep / (totalSteps - 1)) * 100)

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{STATUS_LABELS[status] ?? status}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full bg-surface-tertiary rounded-full h-1.5">
        <div
          className="bg-syntera-500 h-1.5 rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
      {detail && <p className="text-xs text-gray-500">{detail}</p>}
    </div>
  )
}
