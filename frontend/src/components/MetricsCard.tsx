interface Props {
  label: string
  value: string
  sub?: string
  colorClass?: string
}

export default function MetricsCard({ label, value, sub, colorClass }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colorClass ?? 'text-gray-800'}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  )
}
