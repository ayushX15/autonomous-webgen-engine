const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface RunRequest {
  user_requirement: string
  reference_urls: string[]
  reference_image_paths: string[]
  pages_requested: string[]
  max_iterations: number
}

export interface IterationResult {
  iteration: number
  similarity_score: number
  visual_diff_notes: string
  suggestions: string[]
  passed: boolean
  screenshot_path: string | null
}

export interface RunStatus {
  run_id: string
  status: 'running' | 'complete' | 'error'
  current_iteration: number
  max_iterations: number
  is_complete: boolean
  final_output_path: string | null
  error_message: string | null
  iteration_results: IterationResult[]
  progress_messages: string[]
}

export interface QuotaStatus {
  status: 'available' | 'exhausted' | 'error'
  model: string
  message: string
  percentage: number
}

export async function startRun(req: RunRequest): Promise<{ run_id: string }> {
  const res = await fetch(`${BASE}/api/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  })
  if (!res.ok) throw new Error(`Failed: ${res.statusText}`)
  return res.json()
}

export async function getStatus(runId: string): Promise<RunStatus> {
  const res = await fetch(`${BASE}/api/status/${runId}`)
  if (!res.ok) throw new Error(`Failed: ${res.statusText}`)
  return res.json()
}

export async function getQuota(): Promise<QuotaStatus> {
  try {
    const res = await fetch(`${BASE}/api/quota`)
    return res.json()
  } catch {
    return { status: 'error', model: '', message: 'Backend offline', percentage: 0 }
  }
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/api/health`)
    return res.ok
  } catch { return false }
}

export async function pollUntilComplete(
  runId: string,
  onUpdate: (s: RunStatus) => void,
  intervalMs = 5000
): Promise<RunStatus> {
  return new Promise((resolve, reject) => {
    const iv = setInterval(async () => {
      try {
        const s = await getStatus(runId)
        onUpdate(s)
        if (s.status === 'complete' || s.status === 'error') {
          clearInterval(iv)
          resolve(s)
        }
      } catch (e) { clearInterval(iv); reject(e) }
    }, intervalMs)
  })
}