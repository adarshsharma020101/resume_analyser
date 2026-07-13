import { useState, useEffect, useCallback } from 'react'
import { analysisApi } from '../lib/api'

export function useAnalysisPoll(sessionId: string | null) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const poll = useCallback(async () => {
    if (!sessionId) return
    setLoading(true)
    setError(null)
    let attempts = 0
    const maxAttempts = 120
    while (attempts < maxAttempts) {
      try {
        const result = await analysisApi.get(sessionId)
        if (result.status === 'completed' || result.status === 'failed') {
          setData(result)
          setLoading(false)
          return
        }
      } catch (e: any) {
        setError(e.message)
        setLoading(false)
        return
      }
      attempts++
      await new Promise(r => setTimeout(r, 2000))
    }
    setError('Analysis timed out after 4 minutes.')
    setLoading(false)
  }, [sessionId])

  useEffect(() => { poll() }, [poll])
  return { data, loading, error }
}
