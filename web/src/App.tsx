import { useState } from 'react'

interface HealthResponse {
  status: string
  version?: string
}

interface ImportResponse {
  task_id: string
  status: string
}

export default function App() {
  const [health, setHealth] = useState('未检测')
  const [importResult, setImportResult] = useState<ImportResponse | null>(null)
  const [error, setError] = useState('')

  async function checkHealth() {
    setError('')
    try {
      const res = await fetch('/api/health')
      const data = (await res.json()) as HealthResponse
      setHealth(data.status ?? 'ok')
    } catch (e) {
      setError(`后端未连接: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  async function handleFile(file: File | undefined) {
    if (!file) return
    setError('')
    setImportResult(null)
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await fetch('/api/import', { method: 'POST', body: form })
      const data = (await res.json()) as ImportResponse
      setImportResult(data)
    } catch (e) {
      setError(`上传失败: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  return (
    <main>
      <h1>Shop Assistant</h1>

      <section>
        <h2>后端健康检查</h2>
        <button onClick={checkHealth}>检测</button>
        <span>状态: {health}</span>
      </section>

      <section>
        <h2>文档导入</h2>
        <input type="file" onChange={(e) => handleFile(e.target.files?.[0])} />
        {importResult && <pre>{JSON.stringify(importResult, null, 2)}</pre>}
      </section>

      {error && <p className="error">{error}</p>}
    </main>
  )
}
