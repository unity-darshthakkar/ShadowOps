import { createContext, useContext, useState, ReactNode } from 'react'
import type { AnalysisResult } from '../types/api'

interface AnalysisCtx {
  result: AnalysisResult | null
  setResult: (r: AnalysisResult) => void
}

const AnalysisContext = createContext<AnalysisCtx>({
  result: null,
  setResult: () => undefined,
})

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  return (
    <AnalysisContext.Provider value={{ result, setResult }}>
      {children}
    </AnalysisContext.Provider>
  )
}

export function useAnalysis() {
  return useContext(AnalysisContext)
}
