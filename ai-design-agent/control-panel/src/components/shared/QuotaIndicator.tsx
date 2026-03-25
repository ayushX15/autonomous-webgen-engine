// 'use client'
// import { useEffect, useState } from 'react'

// interface QuotaState {
//   status: 'available' | 'exhausted' | 'error' | 'loading'
//   message: string
//   callsUsed: number
//   callsLimit: number
//   percentUsed: number
// }

// const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// export default function QuotaIndicator() {
//   const [quota, setQuota] = useState<QuotaState>({
//     status: 'loading',
//     message: 'Checking...',
//     callsUsed: 0,
//     callsLimit: 20,
//     percentUsed: 0
//   })
//   const [checking, setChecking] = useState(false)

//   const check = async () => {
//     setChecking(true)
//     try {
//       const res = await fetch(`${BASE}/api/quota`)
//       const data = await res.json()

//       if (data.status === 'available') {
//         setQuota({
//           status: 'available',
//           message: 'Gemini Ready',
//           callsUsed: data.calls_used ?? 0,
//           callsLimit: data.calls_limit ?? 20,
//           percentUsed: data.percent_used ?? 5
//         })
//       } else if (data.status === 'exhausted') {
//         setQuota({
//           status: 'exhausted',
//           message: data.message ?? 'Quota Full',
//           callsUsed: data.calls_limit ?? 20,
//           callsLimit: data.calls_limit ?? 20,
//           percentUsed: 100
//         })
//       } else {
//         setQuota({
//           status: 'error',
//           message: 'API Error',
//           callsUsed: 0,
//           callsLimit: 20,
//           percentUsed: 0
//         })
//       }
//     } catch {
//       setQuota(prev => ({ ...prev, status: 'error', message: 'Backend offline' }))
//     } finally {
//       setChecking(false)
//     }
//   }

//   useEffect(() => {
//     check()
//     const iv = setInterval(check, 90000) // refresh every 90s
//     return () => clearInterval(iv)
//   }, [])

//   const colors = {
//     loading:   { dot: 'bg-gray-500',   bar: 'bg-gray-600',   text: 'text-gray-400' },
//     available: { dot: 'bg-green-400',  bar: 'bg-green-500',  text: 'text-green-400' },
//     exhausted: { dot: 'bg-red-400',    bar: 'bg-red-500',    text: 'text-red-400' },
//     error:     { dot: 'bg-yellow-400', bar: 'bg-yellow-500', text: 'text-yellow-400' },
//   }
//   const c = colors[quota.status]
//   const pctFill = 100 - quota.percentUsed  // show REMAINING not used

//   return (
//     <button
//       onClick={check}
//       title={`${quota.message} — Click to refresh`}
//       className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg
//                  bg-white/5 border border-white/10 hover:border-white/20
//                  transition-all duration-200 group"
//     >
//       {/* Status dot */}
//       <span className={`w-2 h-2 rounded-full shrink-0 ${c.dot} ${
//         quota.status === 'available' ? 'animate-pulse' : ''
//       }`} />

//       {/* Label + bar */}
//       <div className="flex flex-col items-start min-w-0">
//         <span className={`text-xs font-bold leading-none mb-1 ${c.text}`}>
//           {quota.status === 'loading' ? 'Checking...' : quota.message}
//         </span>
//         <div className="flex items-center gap-1.5">
//           <div className="w-16 h-1 bg-white/10 rounded-full overflow-hidden">
//             <div
//               className={`h-full rounded-full transition-all duration-500 ${c.bar}`}
//               style={{ width: `${pctFill}%` }}
//             />
//           </div>
//           <span className="text-[10px] font-mono text-gray-500 leading-none">
//             {quota.status === 'loading' ? '...' : `${Math.round(pctFill)}%`}
//           </span>
//         </div>
//       </div>

//       {/* Spinner */}
//       {checking && (
//         <span className="w-3 h-3 border border-white/20 border-t-white/60 rounded-full animate-spin shrink-0" />
//       )}
//     </button>
//   )
// }


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