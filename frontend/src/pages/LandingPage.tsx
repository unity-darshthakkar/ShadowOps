import { useState } from 'react'
import { Link } from 'react-router-dom'

const VALUE_CARDS = [
  {
    icon: '🔍',
    title: 'Reveal Hidden Work',
    description: 'Compare documented workflows with what employees actually do.',
  },
  {
    icon: '📊',
    title: 'Measure AI Tax',
    description:
      'Quantify review, correction, exception, maintenance, and recovery overhead.',
  },
  {
    icon: '🛡️',
    title: 'Design Safer Workflows',
    description:
      'Generate approvals, guardrails, confidence thresholds, and manual fallbacks.',
  },
] as const

const PROOF_STRIP = '5 official steps → 14 actual step types → 20.1% hidden work → 20.5% AI Tax'

const ARCHITECTURE_CONTENT = `ShadowOps Architecture

┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                  │
├─────────────────────────────────────────────────────────────────┤
│  Landing Page → Stage 1: Setup → Stage 2: Workflow Reality      │
│                        ↓                    ↓                   │
│             Stage 3: AI Impact ← Stage 4: Safer Redesign        │
│              AI Impact       ↓                      ↓           │
│                              ↓                      ↓            │
│                    Granite Analysis          Preflight          │
│                    (IBM Granite)               Report (JSON)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓ REST API
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│  • Scenario seed data (seeds.json)                             │
│  • Workflow reconstruction (deterministic metrics)             │
│  • AI Tax calculation (deterministic formulas)                 │
│  • Granite API integration (IBM Granite via Vertex AI / watsonx)│
│  • Deterministic metrics + LLM redesign (Granite)              │
│  • Preflight report JSON export                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    IBM Granite (IBM watsonx / Vertex AI)        │
├─────────────────────────────────────────────────────────────────┤
│  • Generates safer workflow redesign                            │
│  • Produces guardrails: approvals, guardrails, thresholds,     │
│    fallbacks, skill preservation, audit trail                  │
│  • Generates workflow gap narrative & hidden work narrative    │
└─────────────────────────────────────────────────────────────────┘

Data Flow:
1. Stage 1 (Setup)  →  Select scenario from seeds.json
2. Stage 2 (Reality) → Reconstruct actual workflow from event logs
3. Stage 3 (AI Impact) → Calculate deterministic metrics:
   • Hidden work % = (shadow steps / total steps) × 100
   • AI Tax % = (review + correction + exception + maintenance + recovery) / total
4. Stage 4 (Redesign) → IBM Granite generates:
   • Safer workflow steps with executor, approvals, thresholds, fallbacks
   • 6 guardrail categories with specific implementations
   • Redesign recommendations, gap narrative, hidden work narrative
5. Export → Complete JSON preflight report for downstream use`

export default function LandingPage() {
  const [showArchitecture, setShowArchitecture] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <section className="bg-gray-900 text-white py-16 md:py-24 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-blue-400 mb-4">
            ShadowOps
          </h1>
          <h2 className="text-xl md:text-2xl text-gray-300 mb-6 font-medium">
            See the real cost of AI automation before deployment.
          </h2>
          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            ShadowOps reconstructs actual workflows, reveals hidden work, calculates the AI Tax, and
            generates a safer human-AI redesign using IBM Granite.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/setup"
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors text-lg"
            >
              Run Preflight
            </Link>
            <button
              onClick={() => setShowArchitecture(true)}
              className="border-2 border-gray-600 hover:border-gray-400 hover:bg-gray-800 text-white font-semibold px-8 py-3 rounded-lg transition-colors text-lg"
              aria-label="View ShadowOps architecture overview"
            >
              View Architecture
            </button>
          </div>
        </div>
      </section>

      {/* Proof Strip */}
      <section className="bg-gray-100 border-y border-gray-200 py-6 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm md:text-base text-gray-600 font-mono tracking-wide">
            {PROOF_STRIP}
          </p>
        </div>
      </section>

      {/* Value Cards */}
      <section className="py-16 md:py-24 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-3">
              Why ShadowOps
            </h3>
            <p className="text-gray-600 max-w-2xl mx-auto text-lg">
              Three pillars to de-risk AI automation before it reaches production.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 md:gap-8">
            {VALUE_CARDS.map((card) => (
              <article
                key={card.title}
                className="bg-white border border-gray-200 rounded-xl p-6 md:p-8 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="text-4xl mb-4" aria-hidden="true">
                  {card.icon}
                </div>
                <h4 className="text-lg font-semibold text-gray-900 mb-2">{card.title}</h4>
                <p className="text-gray-600 leading-relaxed">{card.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section
        id="architecture"
        className={`bg-gray-900 text-white py-12 px-4 ${showArchitecture ? '' : 'hidden'}`}
        aria-hidden={!showArchitecture}
      >
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-blue-400">Architecture Overview</h3>
            <button
              onClick={() => setShowArchitecture(false)}
              className="text-gray-400 hover:text-white text-sm font-medium"
              aria-label="Close architecture overview"
            >
              Close ↑
            </button>
          </div>
          <pre
            className="bg-gray-800 border border-gray-700 rounded-lg p-6 overflow-x-auto text-sm font-mono text-gray-300 leading-relaxed"
            aria-label="ShadowOps architecture diagram and data flow"
          >
            {ARCHITECTURE_CONTENT}
          </pre>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-8 px-4">
        <div className="max-w-5xl mx-auto text-center text-sm">
          <p className="font-semibold text-white mb-1">ShadowOps</p>
          <p>IBM July Wildcard Hackathon — AI Deployment Preflight Platform</p>
        </div>
      </footer>
    </div>
  )
}