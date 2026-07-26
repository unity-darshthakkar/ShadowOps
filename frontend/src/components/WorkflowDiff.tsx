import type { WorkflowStep } from '../types/api'

interface Props {
  official: WorkflowStep[]
  actual: WorkflowStep[]
}

function StepBadge({ step }: { step: WorkflowStep }) {
  const base = 'inline-block px-2 py-1 rounded text-xs font-medium mb-1 mr-1'
  const color = step.is_hidden_work
    ? 'bg-amber-100 text-amber-800 border border-amber-300'
    : 'bg-blue-100 text-blue-800 border border-blue-300'
  return (
    <span className={`${base} ${color}`} title={`avg ${step.avg_duration_minutes} min × ${step.occurrence_count}`}>
      {step.label}
    </span>
  )
}

export default function WorkflowDiff({ official, actual }: Props) {
  const officialTotal = official.reduce((s, x) => s + x.avg_duration_minutes * x.occurrence_count, 0)
  const actualTotal = actual.reduce((s, x) => s + x.avg_duration_minutes * x.occurrence_count, 0)

  return (
    <div className="grid grid-cols-2 gap-6">
      <div>
        <h3 className="font-semibold text-gray-700 mb-2">Official Workflow ({official.length} steps)</h3>
        <div className="flex flex-wrap">{official.map((s) => <StepBadge key={s.step_id} step={s} />)}</div>
        <p className="text-xs text-gray-500 mt-2">Total: ~{officialTotal.toFixed(0)} min</p>
      </div>
      <div>
        <h3 className="font-semibold text-gray-700 mb-2">Actual Workflow ({actual.length} step types)</h3>
        <div className="flex flex-wrap">{actual.map((s) => <StepBadge key={s.step_id} step={s} />)}</div>
        <p className="text-xs text-gray-500 mt-2">
          Total: ~{actualTotal.toFixed(0)} min
          <span className="ml-2 text-amber-700">● = hidden work</span>
        </p>
      </div>
    </div>
  )
}
