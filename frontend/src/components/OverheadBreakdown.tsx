import type { OverheadAssumption } from '../types/api'

interface Props {
  assumptions: OverheadAssumption[]
  review_overhead: number
  correction_overhead: number
  exception_overhead: number
  maintenance_overhead: number
  failure_recovery_overhead: number
  ai_overhead: number
}

const LABELS: Record<string, string> = {
  expected_review_rate: 'Expected review rate',
  avg_review_minutes: 'Avg review time (min)',
  expected_correction_rate: 'Expected correction rate',
  avg_correction_minutes: 'Avg correction time (min)',
  exception_rate: 'Exception rate',
  avg_exception_handling_minutes: 'Avg exception-handling time (min)',
  weekly_maintenance_minutes: 'Weekly maintenance (min)',
  expected_failure_recovery_minutes: 'Failure-recovery time (min)',
}

const CHART_BARS = [
  { key: 'review_overhead', label: 'Review Overhead', color: 'bg-blue-500' },
  { key: 'correction_overhead', label: 'Correction Overhead', color: 'bg-green-500' },
  { key: 'exception_overhead', label: 'Exception Overhead', color: 'bg-amber-500' },
  { key: 'maintenance_overhead', label: 'Maintenance Overhead', color: 'bg-purple-500' },
  { key: 'failure_recovery_overhead', label: 'Failure Recovery Overhead', color: 'bg-red-500' },
] as const

function OverheadBarChart({
  review_overhead,
  correction_overhead,
  exception_overhead,
  maintenance_overhead,
  failure_recovery_overhead,
}: Pick<Props, 'review_overhead' | 'correction_overhead' | 'exception_overhead' | 'maintenance_overhead' | 'failure_recovery_overhead'>) {
  const values = [
    review_overhead,
    correction_overhead,
    exception_overhead,
    maintenance_overhead,
    failure_recovery_overhead,
  ]
  const maxValue = Math.max(...values, 1) // Avoid division by zero

  return (
    <div className="mb-6" role="img" aria-label={`AI overhead breakdown: review ${review_overhead.toFixed(1)} min, correction ${correction_overhead.toFixed(1)} min, exception ${exception_overhead.toFixed(1)} min, maintenance ${maintenance_overhead.toFixed(1)} min, failure recovery ${failure_recovery_overhead.toFixed(1)} min`}>
      <h4 className="font-semibold text-gray-700 mb-3">AI Overhead Components</h4>
      <div className="space-y-3" style={{ maxWidth: '500px' }}>
        {CHART_BARS.map((bar, idx) => {
          const value = values[idx]
          const percentage = (value / maxValue) * 100
          const showValueInBar = value > 0 && percentage > 15
          return (
            <div key={bar.key} className="group">
              <div className="flex justify-between items-baseline mb-1">
                <span className="text-sm font-medium text-gray-700">{bar.label}</span>
                {!showValueInBar && (
                  <span className="text-sm font-mono font-semibold text-gray-900">{value.toFixed(1)} min</span>
                )}
              </div>
              <div className="relative h-6 bg-gray-100 rounded overflow-hidden">
                <div
                  className={`${bar.color} h-full rounded transition-all duration-500`}
                  style={{ width: `${percentage}%`, minWidth: value > 0 ? '1.5rem' : '0' }}
                  role="progressbar"
                  aria-valuenow={value}
                  aria-valuemin={0}
                  aria-valuemax={maxValue}
                  aria-label={`${bar.label}: ${value.toFixed(1)} minutes`}
                >
                  {showValueInBar && (
                    <span className="absolute inset-0 flex items-center pl-2 text-white text-xs font-medium truncate">
                      {value.toFixed(1)} min
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function OverheadBreakdown({
  assumptions,
  review_overhead,
  correction_overhead,
  exception_overhead,
  maintenance_overhead,
  failure_recovery_overhead,
  ai_overhead,
}: Props) {
  const components = [
    { label: 'Review overhead', value: review_overhead },
    { label: 'Correction overhead', value: correction_overhead },
    { label: 'Exception-handling overhead', value: exception_overhead },
    { label: 'Maintenance overhead', value: maintenance_overhead },
    { label: 'Failure-recovery overhead', value: failure_recovery_overhead },
  ]

  return (
    <div>
      <OverheadBarChart
        review_overhead={review_overhead}
        correction_overhead={correction_overhead}
        exception_overhead={exception_overhead}
        maintenance_overhead={maintenance_overhead}
        failure_recovery_overhead={failure_recovery_overhead}
      />

      {/* Component totals */}
      <div className="space-y-2 mb-4">
        {components.map((c) => (
          <div key={c.label} className="flex justify-between items-center text-sm border-b border-gray-100 pb-1">
            <span className="text-gray-700">{c.label}</span>
            <span className="font-mono font-semibold text-gray-900">{c.value.toFixed(1)} min</span>
          </div>
        ))}
        <div className="flex justify-between items-center text-sm font-bold border-t border-gray-300 pt-1">
          <span>Total AI Overhead</span>
          <span className="font-mono">{ai_overhead.toFixed(1)} min</span>
        </div>
      </div>

      {/* Assumption inputs */}
      <h4 className="font-semibold text-gray-700 mb-2 text-sm">Input Parameters</h4>
      <div className="space-y-1">
        {assumptions.map((a) => (
          <div key={a.field} className="flex justify-between items-center text-xs py-0.5">
            <span className="text-gray-600">{LABELS[a.field] ?? a.field}</span>
            <div className="flex items-center gap-2">
              <span className="font-mono">{a.value}</span>
              {a.source === 'default' ? (
                <span className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded text-xs font-medium">
                  ⚠ Assumption (default: {a.default_value})
                </span>
              ) : (
                <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-xs font-medium">
                  📋 From Proposal
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}