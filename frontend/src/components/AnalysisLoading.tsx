import { useEffect, useState, useRef } from 'react'

const LOADING_STEPS = [
  'Reconstructing workflow',
  'Detecting hidden work',
  'Calculating AI overhead',
  'Generating safer redesign with IBM Granite',
  'Validating output',
] as const

export default function AnalysisLoading({ isLoading }: { isLoading: boolean }) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [announcement, setAnnouncement] = useState('')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!isLoading) {
      setCurrentStepIndex(0)
      setAnnouncement('')
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
      return
    }

    // Announce first step immediately
    setAnnouncement(LOADING_STEPS[0])

    function advanceStep() {
      const nextIndex = currentStepIndex + 1
      if (nextIndex < LOADING_STEPS.length) {
        setCurrentStepIndex(nextIndex)
        setAnnouncement(LOADING_STEPS[nextIndex])
        timerRef.current = setTimeout(advanceStep, 1500)
      }
    }

    timerRef.current = setTimeout(advanceStep, 1500)

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [isLoading, currentStepIndex])

  if (!isLoading) return null

  return (
    <div className="max-w-md mx-auto py-8 px-4" role="status" aria-live="polite" aria-atomic="true">
      <div className="sr-only" aria-live="assertive" aria-atomic="true">
        {announcement}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6 sm:p-8 shadow-sm text-center space-y-5">
        <svg
          className="mx-auto h-10 w-10 text-blue-600 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>

        <div className="space-y-1">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Preparing your preflight analysis</h2>
          <p className="text-sm text-gray-500">Progress shown is a visual sequence, not real backend status.</p>
        </div>

        <div className="space-y-2.5 max-w-xs mx-auto text-left" role="list" aria-label="Analysis steps">
          {LOADING_STEPS.map((step, index) => (
            <div
              key={step}
              className={`flex items-center gap-3 transition-all duration-300 ${
                index < currentStepIndex
                  ? 'text-gray-700'
                  : index === currentStepIndex
                  ? 'text-gray-900 font-medium'
                  : 'text-gray-400'
              }`}
              role="listitem"
            >
              <div
                className={`flex-shrink-0 w-7 h-7 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                  index < currentStepIndex
                    ? 'border-green-500 bg-green-500'
                    : index === currentStepIndex
                    ? 'border-blue-500 bg-blue-500 animate-pulse'
                    : 'border-gray-300'
                }`}
                aria-hidden="true"
              >
                {index < currentStepIndex && (
                  <svg className="w-4 h-4 text-white flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <span className="text-sm sm:text-base">{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}