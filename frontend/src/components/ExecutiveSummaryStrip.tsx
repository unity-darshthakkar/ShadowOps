import { useState, useRef, useEffect } from 'react'
import { useAnalysis } from '../context/AnalysisContext'

const METRIC_DEFINITIONS: Record<string, { title: string; description: string }> = {
  aiTax: {
    title: 'AI Tax',
    description:
      'The share of gross time savings consumed by review, correction, exception handling, maintenance, and failure recovery.',
  },
  burdenConcentration: {
    title: 'Burden Concentration',
    description:
      'The share of hidden-work time carried by the most burdened role.',
  },
  automationReadiness: {
    title: 'Automation Readiness',
    description:
      'A scenario-based heuristic estimating how suitable the workflow is for structured automation.',
  },
  skillLossRisk: {
    title: 'Skill-Loss Risk',
    description:
      'A scenario-based heuristic estimating whether automation may weaken important human expertise.',
  },
}

function InfoIcon({
  metricKey,
}: {
  metricKey: string
}) {
  const definition = METRIC_DEFINITIONS[metricKey]
  if (!definition) return null

  const [isOpen, setIsOpen] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setIsOpen(false)
        buttonRef.current?.focus()
      }
    }

    function handleClickOutside(e: MouseEvent) {
      if (
        contentRef.current &&
        !contentRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  return (
    <span className="relative inline-flex">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onBlur={() => setIsOpen(false)}
        className="ml-1 p-1 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded transition-colors"
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        aria-label={`About ${definition.title}`}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </button>
      {isOpen && (
        <div
          ref={contentRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={`metric-def-${metricKey}`}
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg z-20"
        >
          <h4 id={`metric-def-${metricKey}`} className="font-semibold mb-1">
            {definition.title}
          </h4>
          <p className="leading-relaxed opacity-90">{definition.description}</p>
        </div>
      )}
    </span>
  )
}

function MetricChip({
  label,
  value,
  sub,
  colorClass = 'text-gray-800',
  metricKey,
}: {
  label: string
  value: string
  sub?: string
  colorClass?: string
  metricKey?: string
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm flex-1 min-w-[140px]">
      <div className="flex items-baseline gap-1.5 mb-1">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
        {metricKey && <InfoIcon metricKey={metricKey} />}
      </div>
      <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  )
}

export default function ExecutiveSummaryStrip() {
  const { result } = useAnalysis()

  if (!result) return null

  const { metrics, official_workflow, actual_workflow } = result

  const officialStepCount = official_workflow?.length ?? 0
  const actualStepTypeCount = actual_workflow
    ? new Set(actual_workflow.map((s) => s.event_type)).size
    : 0

  const hiddenWorkRatio = metrics.hidden_work_ratio ?? 0
  const aiTax = metrics.ai_tax ?? 0
  const netTimeSaved = metrics.net_time_saved ?? 0

  const hiddenWorkColor = hiddenWorkRatio >= 0.4 ? 'text-red-600' : hiddenWorkRatio >= 0.2 ? 'text-amber-600' : 'text-green-600'
  const aiTaxColor = aiTax >= 0.6 ? 'text-red-600' : aiTax >= 0.3 ? 'text-amber-600' : 'text-green-600'
  const netTimeColor = netTimeSaved < 0 ? 'text-red-600' : 'text-green-700'

  return (
    <section className="bg-white border border-gray-200 rounded-lg p-4 md:p-6 shadow-sm mb-6" aria-labelledby="exec-summary-heading">
      <div className="mb-4 md:mb-6">
        <h2 id="exec-summary-heading" className="text-lg sm:text-xl font-semibold text-gray-900 mb-1">
          Preflight Summary
        </h2>
        <p className="text-sm text-gray-600">
          A consolidated view of the workflow reality, AI overhead, and estimated deployment impact.
        </p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-4">
        <MetricChip
          label="Official Steps"
          value={String(officialStepCount)}
          sub="documented workflow"
          colorClass="text-blue-700"
        />
        <MetricChip
          label="Actual Step Types"
          value={String(actualStepTypeCount)}
          sub="observed in events"
          colorClass="text-orange-700"
        />
        <MetricChip
          label="Hidden Work"
          value={`${(hiddenWorkRatio * 100).toFixed(1)}%`}
          sub="of total time"
          colorClass={hiddenWorkColor}
          metricKey="burdenConcentration"
        />
        <MetricChip
          label="AI Tax"
          value={`${(aiTax * 100).toFixed(1)}%`}
          sub="overhead ÷ gross savings"
          colorClass={aiTaxColor}
          metricKey="aiTax"
        />
        <MetricChip
          label="Net Time Saved"
          value={`${netTimeSaved.toFixed(1)} min`}
          sub={netTimeSaved < 0 ? '⚠ Net negative' : 'after AI overhead'}
          colorClass={netTimeColor}
        />
      </div>
    </section>
  )
}