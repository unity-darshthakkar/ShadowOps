import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { AnalysisProvider } from './context/AnalysisContext'
import ProviderBanner from './components/ProviderBanner'
import StageSetup from './pages/StageSetup'
import StageReality from './pages/StageReality'
import StageAIImpact from './pages/StageAIImpact'
import StageRedesign from './pages/StageRedesign'

const NAV_ITEMS = [
  { path: '/', label: '1 · Setup' },
  { path: '/reality', label: '2 · Workflow Reality' },
  { path: '/ai-impact', label: '3 · AI Impact' },
  { path: '/redesign', label: '4 · Safer Redesign' },
]

function NavBar() {
  const { pathname } = useLocation()
  return (
    <nav className="bg-gray-900 text-white px-4 py-2 flex items-center gap-6 text-sm">
      <span className="font-bold tracking-tight text-blue-400">ShadowOps</span>
      {NAV_ITEMS.map((item) => (
        <Link
          key={item.path}
          to={item.path}
          className={`hover:text-blue-300 transition-colors ${pathname === item.path ? 'text-white font-semibold underline underline-offset-4' : 'text-gray-400'}`}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AnalysisProvider>
        <div className="min-h-screen bg-gray-50">
          <ProviderBanner />
          <NavBar />
          <main className="pb-16">
            <Routes>
              <Route path="/" element={<StageSetup />} />
              <Route path="/reality" element={<StageReality />} />
              <Route path="/ai-impact" element={<StageAIImpact />} />
              <Route path="/redesign" element={<StageRedesign />} />
            </Routes>
          </main>
        </div>
      </AnalysisProvider>
    </BrowserRouter>
  )
}
