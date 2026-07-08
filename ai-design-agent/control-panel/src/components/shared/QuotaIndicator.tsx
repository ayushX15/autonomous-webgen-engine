'use client'

import { useEffect, useState } from 'react'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Q { status: 'available'|'exhausted'|'error'|'loading'; msg: string; pct: number }

export default function QuotaIndicator() {
  const [q, setQ] = useState<Q>({ status: 'loading', msg: 'Checking', pct: 0 })
  const [busy, setBusy] = useState(false)

  const check = async () => {
    setBusy(true)
    try {
      const res  = await fetch(`${BASE}/api/quota`)
      const data = await res.json()
      if (data.status === 'available') {
        setQ({ status: 'available', msg: 'Gemini Ready', pct: data.percent_used ?? 5 })
      } else if (data.status === 'exhausted') {
        setQ({ status: 'exhausted', msg: 'Quota Full', pct: 100 })
      } else {
        setQ({ status: 'error', msg: 'API Error', pct: 0 })
      }
    } catch {
      setQ({ status: 'error', msg: 'Offline', pct: 0 })
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    check()
    const iv = setInterval(check, 90_000)
    return () => clearInterval(iv)
  }, [])

  const remaining = 100 - q.pct

  const dotColor =
    q.status === 'available' ? '#4ade80' :
    q.status === 'exhausted' ? '#DC143C' : '#f59e0b'

  const barGradient =
    q.status === 'available' ? 'linear-gradient(90deg,#22c55e,#4ade80)' :
    q.status === 'exhausted' ? 'linear-gradient(90deg,#DC143C,#ff4d6d)' :
                               'linear-gradient(90deg,#f59e0b,#fbbf24)'

  return (
    <button
      onClick={check}
      title={`${q.msg} — click to refresh`}
      style={{
        display:     'flex',
        alignItems:  'center',
        gap:         8,
        padding:     '6px 12px',
        borderRadius: 10,
        background:  'rgba(255,255,255,0.04)',
        border:      '1px solid rgba(220,20,60,0.14)',
        cursor:      'pointer',
        flexShrink:  0,
      }}
    >
      {/* Dot */}
      <span style={{
        width: 7, height: 7, borderRadius: '50%',
        background: dotColor,
        boxShadow:  `0 0 6px ${dotColor}`,
        flexShrink: 0,
        animation:  q.status === 'available' ? 'blink 2s ease infinite' : undefined,
      }} />

      {/* Text + bar — fixed width so it never overflows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
        <span style={{
          fontSize: 11, fontWeight: 700, color: dotColor,
          whiteSpace: 'nowrap', lineHeight: 1,
        }}>
          {q.msg}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{
            width: 56, height: 3, borderRadius: 99,
            background: 'rgba(255,255,255,0.08)',
            overflow: 'hidden', flexShrink: 0,
          }}>
            <div style={{
              width:      `${remaining}%`,
              height:     '100%',
              borderRadius: 99,
              background: barGradient,
              transition: 'width 0.5s ease',
            }} />
          </div>
          <span style={{
            fontSize: 10, fontWeight: 700, fontFamily: 'monospace',
            color: 'rgba(255,255,255,0.28)', whiteSpace: 'nowrap',
          }}>
            {q.status === 'loading' ? '…' : `${Math.round(remaining)}%`}
          </span>
        </div>
      </div>

      {/* Spinner */}
      {busy && (
        <span style={{
          width: 12, height: 12, borderRadius: '50%', flexShrink: 0,
          border: '2px solid rgba(220,20,60,0.25)',
          borderTopColor: '#DC143C',
          animation: 'spin-q 1s linear infinite',
        }} />
      )}

      <style suppressHydrationWarning>{`
        @keyframes spin-q { to { transform: rotate(360deg); } }
      `}</style>
    </button>
  )
}