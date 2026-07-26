import { useNavigate } from 'react-router-dom'
import { useAnalysis } from '../context/AnalysisContext'
import OverheadBreakdown from '../components/OverheadBreakdown'
import MetricsCard from '../components/MetricsCard'

export default function StageAIImpact() {
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
  const taxColor =
    metrics.ai_tax < 0.3 ? 'text-green-600' : metrics.ai_tax < 0.6 ? 'text-amber-600' : 'text-red-600'

  const cols = [
    { label: 'Official', minutes: metrics.official_total_minutes, color: 'bg-blue-50 border-blue-200' },
    { label: 'Actual', minutes: metrics.actual_total_minutes, color: 'bg-orange-50 border-orange-200' },
    { label: 'AI-Automated', minutes: metrics.ai_automated_total_minutes, color: 'bg-green-50 border-green-200' },
    { label: 'Hybrid', minutes: metrics.hybrid_total_minutes, color: 'bg-purple-50 border-purple-200' },
  ]

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-10">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Stage 3 — AI Impact</h2>
        <p className="text-sm text-gray-500">Scenario: {result.scenario_id}</p>
      </div>

      {/* Section A — Time comparison */}
      <section className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h3 className="font-semibold text-gray-800 mb-4 text-lg">Workflow Time Comparison</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          {cols.map((c) => (
            <div key={c.label} className={`border rounded-lg p-4 ${c.color}`}>
              <p className="text-xs font-semibold text-gray-600 uppercase mb-1">{c.label}</p>
              <p className="text-2xl font-bold text-gray-900">{c.minutes.toFixed(0)}</p>
              <p className="text-xs text-gray-500">minutes</p>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-50 border rounded p-3">
            <p className="text-xs text-gray-500 uppercase font-semibold">Gross Time Saved</p>
            <p className={`text-xl font-bold ${metrics.gross_time_saved >= 0 ? 'text-green-700' : 'text-red-700'}`}>
              {metrics.gross_time_saved.toFixed(1)} min
            </p>
          </div>
          <div className="bg-gray-50 border rounded p-3">
            <p className="text-xs text-gray-500 uppercase font-semibold">Net Time Saved</p>
            <p className={`text-xl font-bold ${metrics.net_time_saved >= 0 ? 'text-green-700' : 'text-red-700'}`}>
              {metrics.net_time_saved.toFixed(1)} min
            </p>
          </div>
        </div>
      </section>

      {/* Section B — Overhead breakdown */}
      <section className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <OverheadBreakdown
          assumptions={metrics.overhead_assumptions}
          review_overhead={metrics.review_overhead}
          correction_overhead={metrics.correction_overhead}
          exception_overhead={metrics.exception_overhead}
          maintenance_overhead={metrics.maintenance_overhead}
          failure_recovery_overhead={metrics.failure_recovery_overhead}
          ai_overhead={metrics.ai_overhead}
        />
      </section>

      {/* Section C — AI Tax card */}
      <section>
        <h3 className="font-semibold text-gray-800 mb-3 text-lg">AI Tax</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <MetricsCard
            label="AI Tax"
            value={`${(metrics.ai_tax * 100).toFixed(1)}%`}
            sub="AI overhead ÷ gross time saved"
            colorClass={taxColor}
          />
          <MetricsCard
            label="AI Overhead"
            value={`${metrics.ai_overhead.toFixed(1)} min`}
            sub="review + correction + exception + maintenance + recovery"
          />
          <MetricsCard
            label="Net Time Saved"
            value={`${metrics.net_time_saved.toFixed(1)} min`}
            sub={metrics.net_time_saved < 0 ? '⚠ Net negative — AI costs exceed savings' : 'After all AI overhead deducted'}
            colorClass={metrics.net_time_saved < 0 ? 'text-red-600' : 'text-green-700'}
          />
        </div>
      </section>

      <div className="flex justify-between">
        <button onClick={() => navigate('/reality')} className="border border-gray-300 text-gray-700 font-semibold px-5 py-2 rounded-lg hover:bg-gray-50">
          ← Back
        </button>
        <button onClick={() => navigate('/redesign')} className="bg-blue-700 hover:bg-blue-800 text-white font-semibold px-6 py-2 rounded-lg">
          Next: Safer Redesign →
        </button>
      </div>
    </div>
  )
}
