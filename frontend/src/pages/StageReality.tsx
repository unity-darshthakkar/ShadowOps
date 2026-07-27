import { useNavigate } from 'react-router-dom'
import { useAnalysis } from '../context/AnalysisContext'
import WorkflowDiff from '../components/WorkflowDiff'
import HiddenWorkTable from '../components/HiddenWorkTable'
import MetricsCard from '../components/MetricsCard'
import ExecutiveSummaryStrip from '../components/ExecutiveSummaryStrip'

export default function StageReality() {
  const { result } = useAnalysis()
  const navigate = useNavigate()

  if (!result) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4 text-center">
        <p className="text-gray-500">No analysis loaded. <button onClick={() => navigate('/')} className="text-blue-600 underline">Go to Setup</button></p>
      </div>
    )
  }

  const { metrics } = result

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-10">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Stage 2 — Workflow Reality</h2>
        <p className="text-sm text-gray-500">Scenario: {result.scenario_id}</p>
      </div>

      <ExecutiveSummaryStrip />

      {/* Section A — Workflow diff */}
      <section className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h3 className="font-semibold text-gray-800 mb-4 text-lg">Official vs Actual Workflow</h3>
        <WorkflowDiff official={result.official_workflow} actual={result.actual_workflow} />
      </section>

      {/* Section B — Hidden work evidence */}
      <section className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h3 className="font-semibold text-gray-800 mb-4 text-lg">Hidden Work Evidence</h3>
        <HiddenWorkTable
          evidence={result.hidden_work.evidence}
          hiddenWorkRatio={result.hidden_work.hidden_work_ratio}
        />
      </section>

      {/* Section C — Metrics grid */}
      <section>
        <h3 className="font-semibold text-gray-800 mb-3 text-lg">Key Metrics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricsCard
            label="Hidden Work Ratio"
            value={`${(metrics.hidden_work_ratio * 100).toFixed(1)}%`}
            sub="of total time is invisible to management"
            colorClass={metrics.hidden_work_ratio >= 0.4 ? 'text-red-600' : metrics.hidden_work_ratio >= 0.2 ? 'text-amber-600' : 'text-green-600'}
          />
          <MetricsCard
            label="Burden Concentration"
            value={`${(metrics.burden_concentration * 100).toFixed(0)}%`}
            sub="hidden work on most-loaded role"
          />
          <MetricsCard
            label="Automation Readiness"
            value={metrics.automation_readiness_label}
            sub={`Score: ${(metrics.automation_readiness * 100).toFixed(0)}% — scenario-based heuristic`}
            colorClass={metrics.automation_readiness_label === 'High' ? 'text-green-700' : metrics.automation_readiness_label === 'Medium' ? 'text-amber-700' : 'text-red-700'}
          />
          <MetricsCard
            label="Skill-Loss Risk"
            value={metrics.skill_loss_risk}
            sub="scenario-based heuristic, not validated"
            colorClass={metrics.skill_loss_risk === 'High' ? 'text-red-700' : metrics.skill_loss_risk === 'Medium' ? 'text-amber-700' : 'text-green-700'}
          />
        </div>
        <p className="text-xs text-gray-400 mt-2 italic">
          Automation Readiness and Skill-Loss Risk are scenario-based heuristics, not validated assessments.
        </p>
      </section>

      <div className="flex justify-end">
        <button
          onClick={() => navigate('/ai-impact')}
          className="bg-blue-700 hover:bg-blue-800 text-white font-semibold px-6 py-2 rounded-lg"
        >
          Next: AI Impact →
        </button>
      </div>
    </div>
  )
}
