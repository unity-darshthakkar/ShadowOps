import type { HiddenWorkEvidence } from '../types/api'

interface Props {
  evidence: HiddenWorkEvidence[]
  hiddenWorkRatio: number
}

export default function HiddenWorkTable({ evidence, hiddenWorkRatio }: Props) {
  const pct = (hiddenWorkRatio * 100).toFixed(1)
  const color =
    hiddenWorkRatio >= 0.4 ? 'text-red-600' : hiddenWorkRatio >= 0.2 ? 'text-amber-600' : 'text-green-600'

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-4">
        <span className={`text-4xl font-bold ${color}`}>{pct}%</span>
        <span className="text-gray-600 text-sm">of total time is hidden work</span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border border-gray-200 rounded">
          <thead className="bg-gray-50">
            <tr>
              {['Event ID', 'Ticket', 'Type', 'Duration (min)', 'Description'].map((h) => (
                <th key={h} className="px-3 py-2 text-left font-semibold text-gray-700 border-b">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {evidence.map((ev) => (
              <tr key={ev.event_id} className="even:bg-amber-50 border-b border-gray-100">
                <td className="px-3 py-1.5 font-mono text-xs text-gray-500">{ev.event_id}</td>
                <td className="px-3 py-1.5 font-mono text-xs">{ev.ticket_id}</td>
                <td className="px-3 py-1.5">
                  <span className="bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded text-xs font-medium">
                    {ev.event_type}
                  </span>
                </td>
                <td className="px-3 py-1.5 text-center">{ev.duration_minutes}</td>
                <td className="px-3 py-1.5 text-gray-700">{ev.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500 mt-2">{evidence.length} hidden-work events total</p>
    </div>
  )
}
