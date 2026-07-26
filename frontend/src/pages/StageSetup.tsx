import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { useAnalysis } from '../context/AnalysisContext'
import type { ScenarioMeta, AnalysisResult } from '../types/api'

export default function StageSetup() {
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { setResult } = useAnalysis()
  const navigate = useNavigate()

  useEffect(() => {
    apiFetch<ScenarioMeta[]>('/scenarios')
      .then((s) => {
        setScenarios(s)
        if (s.length > 0) setSelected(s[0].scenario_id)
      })
      .catch((e) => setError(String(e)))
  }, [])

  async function runAnalysis() {
    if (!selected) return
    setLoading(true)
    setError(null)
    try {
      const result = await apiFetch<AnalysisResult>('/analysis/run', {
        method: 'POST',
        body: JSON.stringify({ scenario_id: selected }),
      })
      setResult(result)
      navigate('/reality')
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">ShadowOps</h1>
      <p className="text-gray-600 mb-8">AI Deployment Preflight Platform — IBM July Wildcard Hackathon</p>

      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm mb-6">
        <h2 className="font-semibold text-lg text-gray-800 mb-4">Select Scenario</h2>
        {scenarios.map((s) => (
          <label key={s.scenario_id} className="flex items-start gap-3 cursor-pointer mb-3">
            <input
              type="radio"
              name="scenario"
              value={s.scenario_id}
              checked={selected === s.scenario_id}
              onChange={() => setSelected(s.scenario_id)}
              className="mt-1"
            />
            <div>
              <p className="font-medium text-gray-900">{s.name}</p>
              <p className="text-sm text-gray-600">{s.description}</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {s.event_count} events · {s.ticket_count} tickets
              </p>
            </div>
          </label>
        ))}
      </div>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      <button
        onClick={runAnalysis}
        disabled={!selected || loading}
        className="w-full bg-blue-700 hover:bg-blue-800 disabled:bg-gray-400 text-white font-semibold py-3 rounded-lg transition-colors"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Running Preflight Analysis…
          </span>
        ) : (
          '▶ Run Preflight Analysis'
        )}
      </button>
    </div>
  )
}
