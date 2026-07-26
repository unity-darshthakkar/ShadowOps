import type { AnalysisResult } from '../types/api'

interface Props {
  result: AnalysisResult
}

export default function ReportExport({ result }: Props) {
  function download() {
    const json = JSON.stringify(result, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `shadowops-preflight-${result.analysis_id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <button
      onClick={download}
      className="bg-blue-700 hover:bg-blue-800 text-white font-semibold px-5 py-2 rounded shadow transition-colors"
    >
      ⬇ Download Preflight Report (JSON)
    </button>
  )
}
