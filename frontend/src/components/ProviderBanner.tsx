import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client'
import type { ProviderStatusResponse } from '../types/api'

export default function ProviderBanner() {
  const [provider, setProvider] = useState<'live_granite' | 'cached_demo' | null>(null)

  useEffect(() => {
    apiFetch<ProviderStatusResponse>('/demo/provider-status')
      .then((r) => setProvider(r.provider))
      .catch(() => setProvider('cached_demo'))
  }, [])

  if (!provider) return null

  const isLive = provider === 'live_granite'
  return (
    <div
      className={`w-full text-center text-sm font-semibold py-1.5 px-4 ${
        isLive ? 'bg-green-600 text-white' : 'bg-amber-400 text-gray-900'
      }`}
    >
      {isLive ? '🟢 Live IBM Granite' : '🟡 Cached Demo Data — no watsonx credentials configured'}
    </div>
  )
}
