import React, { useState, useMemo } from 'react'
import type { HiddenWorkEvidence } from '../types/api'

interface Props {
  evidence: HiddenWorkEvidence[]
  hiddenWorkRatio: number
}

export default function HiddenWorkTable({ evidence, hiddenWorkRatio }: Props) {
  const pct = (hiddenWorkRatio * 100).toFixed(1)
  const color = hiddenWorkRatio >= 0.4 ? 'text-red-600' : hiddenWorkRatio >= 0.2 ? 'text-amber-600' : 'text-green-600'

  // Filter state
  const [selectedType, setSelectedType] = useState<string>('all')
  const [selectedTicket, setSelectedTicket] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [showAll, setShowAll] = useState(false)
  const [expandedRow, setExpandedRow] = useState<string | null>(null)

  // Get unique filter options from evidence
  const types = useMemo(
    () => ['all', ...Array.from(new Set(evidence.map((e) => e.event_type)).values())].sort(),
    [evidence]
  )
  const tickets = useMemo(
    () => ['all', ...Array.from(new Set(evidence.map((e) => e.ticket_id)).values())].sort(),
    [evidence]
  )

  // Apply filters without mutating original data
  const filtered = useMemo(() => {
    let result = evidence

    if (selectedType !== 'all') {
      result = result.filter((e) => e.event_type === selectedType)
    }
    if (selectedTicket !== 'all') {
      result = result.filter((e) => e.ticket_id === selectedTicket)
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase()
      result = result.filter(
        (e) =>
          e.event_id.toLowerCase().includes(q) ||
          e.ticket_id.toLowerCase().includes(q) ||
          e.event_type.toLowerCase().includes(q) ||
          e.notes.toLowerCase().includes(q) ||
          e.description.toLowerCase().includes(q)
      )
    }
    return result
  }, [evidence, selectedType, selectedTicket, searchQuery])

  // Count events per type (from complete evidence, not filtered)
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    evidence.forEach((e) => {
      counts[e.event_type] = (counts[e.event_type] || 0) + 1
    })
    return counts
  }, [evidence])

  const displayed = showAll ? filtered : filtered.slice(0, 10)
  const hasActiveFilters = selectedType !== 'all' || selectedTicket !== 'all' || searchQuery.trim() !== ''

  function clearFilters() {
    setSelectedType('all')
    setSelectedTicket('all')
    setSearchQuery('')
    setShowAll(false)
    setExpandedRow(null)
  }

  function toggleRow(eventId: string) {
    setExpandedRow((prev) => (prev === eventId ? null : eventId))
  }

  return (
    <div>
      {/* Header with ratio */}
      <div className="flex items-baseline gap-3 mb-4">
        <span className={`text-4xl font-bold ${color}`}>{pct}%</span>
        <span className="text-gray-600 text-sm">of total time is hidden work</span>
      </div>

      {/* Filter controls */}
      <div className="space-y-3 mb-4">
        {/* Row 1: Type and Ticket dropdowns */}
        <div className="flex flex-wrap gap-3 md:gap-4">
          <div className="flex-1 min-w-[150px]">
            <label htmlFor="type-filter" className="block text-xs font-medium text-gray-600 mb-1">
              Hidden-work type
            </label>
            <select
              id="type-filter"
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {types.map((t) => (
                <option key={t} value={t}>
                  {t === 'all' ? 'All types' : t}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[150px]">
            <label htmlFor="ticket-filter" className="block text-xs font-medium text-gray-600 mb-1">
              Ticket
            </label>
            <select
              id="ticket-filter"
              value={selectedTicket}
              onChange={(e) => setSelectedTicket(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {tickets.map((t) => (
                <option key={t} value={t}>
                  {t === 'all' ? 'All tickets' : t}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Row 2: Search and Show all toggle */}
        <div className="flex flex-wrap gap-3 md:gap-4 items-end">
          <div className="flex-1 min-w-[180px]">
            <label htmlFor="search-filter" className="block text-xs font-medium text-gray-600 mb-1">
              Search (event ID, ticket, type, notes, description)
            </label>
            <input
              id="search-filter"
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search all fields…"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-700">
              <input
                type="checkbox"
                checked={showAll}
                onChange={(e) => setShowAll(e.target.checked)}
                className="mr-1.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Show all ({filtered.length})
            </label>
            {hasActiveFilters && (
              <button type="button" onClick={clearFilters} className="text-sm text-blue-600 hover:text-blue-800 font-medium">
                Clear filters
              </button>
            )}
          </div>
        </div>

        {/* Type count badges */}
        <div className="flex flex-wrap gap-2">
          {Object.entries(typeCounts)
            .sort(([, a], [, b]) => b - a)
            .map(([type, count]) => (
              <span
                key={type}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                  selectedType === type ? 'bg-amber-100 text-amber-800 border border-amber-300' : 'bg-gray-100 text-gray-700'
                }`}
              >
                {type} <span className="bg-white/50 px-1.5 py-0.5 rounded text-xs">{count}</span>
              </span>
            ))}
        </div>
      </div>

      {/* Results summary */}
      <div className="text-xs text-gray-500 mb-2">
        {filtered.length === evidence.length
          ? `${evidence.length} hidden-work events total`
          : `Showing ${displayed.length} of ${filtered.length} matching events (of ${evidence.length} total)`}
      </div>

      {/* Table or empty state */}
      {filtered.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <svg className="mx-auto h-10 w-10 text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm">No hidden-work events match the current filters.</p>
          {hasActiveFilters && (
            <button type="button" onClick={clearFilters} className="mt-2 text-sm text-blue-600 hover:text-blue-800 underline">
              Clear filters to see all events
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm border border-gray-200 rounded" role="grid">
            <thead className="bg-gray-50">
              <tr>
                {['Event ID', 'Ticket', 'Type', 'Duration (min)', 'Notes', 'Description'].map((h) => (
                  <th key={h} className="px-3 py-2 text-left font-semibold text-gray-700 border-b" scope="col">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayed.map((ev) => {
                const isExpanded = expandedRow === ev.event_id
                return (
                  <React.Fragment key={ev.event_id}>
                    <tr
                      className={`even:bg-amber-50 border-b border-gray-100 hover:bg-gray-50 cursor-pointer ${
                        isExpanded ? 'bg-blue-50' : ''
                      }`}
                      onClick={() => toggleRow(ev.event_id)}
                      style={{ cursor: ev.notes.length > 50 || ev.description.length > 80 ? 'pointer' : 'default' }}
                    >
                      <td className="px-3 py-1.5 font-mono text-xs text-gray-500">{ev.event_id}</td>
                      <td className="px-3 py-1.5 font-mono text-xs">{ev.ticket_id}</td>
                      <td className="px-3 py-1.5">
                        <span className="bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded text-xs font-medium">
                          {ev.event_type}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-center">{ev.duration_minutes}</td>
                      <td className="px-3 py-1.5 text-gray-600">
                        <div className={isExpanded ? 'whitespace-normal' : 'truncate max-w-xs'} title={ev.notes}>
                          {ev.notes}
                        </div>
                      </td>
                      <td className="px-3 py-1.5 text-gray-700">
                        <div className={isExpanded ? 'whitespace-normal' : 'truncate max-w-xs'} title={ev.description}>
                          {ev.description}
                        </div>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="bg-blue-50">
                        <td colSpan={6} className="px-4 py-3 border-t border-blue-200">
                          <div className="space-y-2 text-xs text-gray-700">
                            <div>
                              <span className="font-semibold text-gray-900">Notes: </span>
                              <span className="whitespace-pre-wrap">{ev.notes}</span>
                            </div>
                            <div>
                              <span className="font-semibold text-gray-900">Description: </span>
                              <span className="whitespace-pre-wrap">{ev.description}</span>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {filtered.length > 10 && !showAll && (
        <p className="text-xs text-gray-500 mt-2">
          <button type="button" onClick={() => setShowAll(true)} className="text-blue-600 hover:text-blue-800 underline">
            Show all {filtered.length} events
          </button>
        </p>
      )}
      {showAll && filtered.length > 10 && (
        <p className="text-xs text-gray-500 mt-2">
          <button type="button" onClick={() => setShowAll(false)} className="text-blue-600 hover:text-blue-800 underline">
            Show first 10
          </button>
        </p>
      )}
    </div>
  )
}