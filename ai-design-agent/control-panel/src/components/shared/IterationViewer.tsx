// 'use client'
// import { useUI } from '@/context/UIContext'
// import { IterationResult, RunStatus } from '@/lib/api'

// interface Props { status: RunStatus | null; isRunning: boolean }

// export default function IterationViewer({ status, isRunning }: Props) {
//   const { isEnhanced } = useUI()

//   const card = isEnhanced
//     ? 'bg-[#1a2236]/80 backdrop-blur-xl border border-indigo-500/20 rounded-2xl p-6 shadow-2xl'
//     : 'bg-[#1a2236] border border-[#1e293b] rounded-xl p-5'

//   const messages = status?.progress_messages ?? []
//   const results  = status?.iteration_results  ?? []

//   return (
//     <div className={card}>
//       <div className="flex items-center gap-2 mb-5">
//         <span className="text-lg">🔄</span>
//         <h2 className="text-base font-bold text-white">Iteration Progress</h2>
//         {isRunning && (
//           <span className="ml-auto flex items-center gap-1.5 text-xs text-indigo-400">
//             <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
//             Live
//           </span>
//         )}
//       </div>

//       {/* Running bar */}
//       {isRunning && (
//         <div className="mb-4 p-3 rounded-xl bg-indigo-950/50 border border-indigo-800/50">
//           <div className="flex justify-between text-xs text-indigo-400 mb-2">
//             <span>Iteration {status?.current_iteration ?? 0} of {status?.max_iterations ?? '?'}</span>
//             <span>{Math.round(((status?.current_iteration ?? 0) / (status?.max_iterations ?? 1)) * 100)}%</span>
//           </div>
//           <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
//             <div
//               className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-700"
//               style={{ width: `${((status?.current_iteration ?? 0) / (status?.max_iterations ?? 1)) * 100}%` }}
//             />
//           </div>
//         </div>
//       )}

//       {/* Log */}
//       {messages.length > 0 && (
//         <div className="mb-4">
//           <p className="text-xs text-slate-600 uppercase tracking-widest mb-2">Progress Log</p>
//           <div className="space-y-1">
//             {messages.map((m, i) => (
//               <div key={i} className="flex items-start gap-2 text-xs text-slate-400">
//                 <span className="text-slate-600 mt-0.5 shrink-0">›</span>
//                 <span>{m}</span>
//               </div>
//             ))}
//           </div>
//         </div>
//       )}

//       {/* Results */}
//       {results.length > 0 && (
//         <div>
//           <p className="text-xs text-slate-600 uppercase tracking-widest mb-3">Results</p>
//           <div className="space-y-3">
//             {results.map(r => (
//               <IterationCard key={r.iteration} result={r} isEnhanced={isEnhanced} />
//             ))}
//           </div>
//         </div>
//       )}

//       {/* Empty */}
//       {!isRunning && results.length === 0 && (
//         <div className="text-center py-10 text-slate-700">
//           <div className="text-3xl mb-2">🤖</div>
//           <p className="text-sm">No runs yet. Submit a request to start.</p>
//         </div>
//       )}
//     </div>
//   )
// }

// function IterationCard({ result, isEnhanced }: { result: IterationResult; isEnhanced: boolean }) {
//   const pct  = Math.round(result.similarity_score * 100)
//   const bar  = pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-500' : 'bg-red-500'
//   const text = pct >= 80 ? 'text-green-400' : pct >= 60 ? 'text-yellow-400' : 'text-red-400'

//   // Convert Windows path to file:// URL for opening in browser
//   const screenshotUrl = result.screenshot_path
//     ? `file:///${result.screenshot_path.replace(/\\/g, '/')}`
//     : null

//   return (
//     <div className={`p-4 rounded-xl border transition-all ${
//       result.passed
//         ? 'border-green-800/50 bg-green-950/20'
//         : 'border-slate-800/50 bg-slate-900/20'
//     } ${isEnhanced ? 'fade-up' : ''}`}>

//       {/* Header */}
//       <div className="flex items-center justify-between mb-2">
//         <div className="flex items-center gap-2">
//           <span className="text-sm font-bold text-white">Iteration {result.iteration}</span>
//           {result.passed && (
//             <span className="px-2 py-0.5 bg-green-500/15 text-green-400 text-xs rounded-full border border-green-500/25">
//               ✅ PASSED
//             </span>
//           )}
//         </div>
//         <span className={`text-base font-black ${text}`}>{pct}%</span>
//       </div>

//       {/* Score bar */}
//       <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden mb-3">
//         <div className={`${bar} h-full rounded-full transition-all duration-700`}
//              style={{ width: `${pct}%` }} />
//       </div>

//       {/* Notes */}
//       {result.visual_diff_notes && !result.visual_diff_notes.includes('could not') && (
//         <p className="text-xs text-slate-400 mb-2 leading-relaxed">{result.visual_diff_notes}</p>
//       )}

//       {/* Suggestions */}
//       {result.suggestions.length > 0 && !result.passed && (
//         <div className="mb-2">
//           <p className="text-xs text-slate-600 mb-1">Next iteration will fix:</p>
//           <ul className="space-y-0.5">
//             {result.suggestions.map((s, i) => (
//               <li key={i} className="flex items-start gap-1.5 text-xs text-slate-500">
//                 <span className="text-indigo-500 mt-0.5 shrink-0">•</span>{s}
//               </li>
//             ))}
//           </ul>
//         </div>
//       )}

//       {/* Screenshot link — opens in new tab */}
//       {screenshotUrl && (
//         <a
//           href={screenshotUrl}
//           target="_blank"
//           rel="noopener noreferrer"
//           className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 hover:underline transition-colors mt-1"
//         >
//           <span>📸</span>
//           <span>View Screenshot → (opens in new tab)</span>
//         </a>
//       )}
//     </div>
//   )
// }


'use client'

import { IterationResult, RunStatus } from '@/lib/api'

interface Props { status: RunStatus | null; isRunning: boolean }

export default function IterationViewer({ status, isRunning }: Props) {
  const messages = status?.progress_messages ?? []
  const results  = status?.iteration_results  ?? []

  return (
    <div className="glass-card" style={{ borderRadius: 18, padding: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 3, height: 16, borderRadius: 99,
            background: 'linear-gradient(180deg,#DC143C,#ff4d6d)',
            display: 'inline-block', flexShrink: 0,
          }} />
          <h2 style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.55)', textTransform: 'uppercase' }}>
            Iteration Progress
          </h2>
        </div>
        {isRunning && (
          <div style={{
            display:'flex', alignItems:'center', gap:5,
            padding:'3px 10px', borderRadius:99,
            background:'rgba(220,20,60,0.1)', border:'1px solid rgba(220,20,60,0.28)',
            fontSize:11, fontWeight:700, color:'#DC143C',
          }}>
            {[0,130,260].map(d=>(
              <span key={d} style={{
                width:4,height:4,borderRadius:'50%',background:'#DC143C',
                animation:`blink-i 1s ease ${d}ms infinite`,
              }}/>
            ))}
            Live
          </div>
        )}
      </div>

      {/* Progress bar */}
      {isRunning && (
        <div style={{
          padding: '12px 14px', borderRadius: 12,
          background: 'rgba(220,20,60,0.05)',
          border:     '1px solid rgba(220,20,60,0.18)',
        }}>
          <div style={{ display:'flex', justifyContent:'space-between', fontSize:11, fontWeight:600, color:'rgba(220,20,60,0.8)', marginBottom:8 }}>
            <span>Iteration {status?.current_iteration ?? 0} of {status?.max_iterations ?? '?'}</span>
            <span>{Math.round(((status?.current_iteration ?? 0)/(status?.max_iterations ?? 1))*100)}%</span>
          </div>
          <div style={{ height:3, borderRadius:99, background:'rgba(255,255,255,0.06)', overflow:'hidden' }}>
            <div style={{
              height:'100%', borderRadius:99,
              width:`${((status?.current_iteration ?? 0)/(status?.max_iterations ?? 1))*100}%`,
              background:'linear-gradient(90deg,#DC143C,#ff4d6d)',
              boxShadow:'0 0 8px rgba(220,20,60,0.5)',
              transition:'width 0.7s ease',
            }}/>
          </div>
        </div>
      )}

      {/* Log */}
      {messages.length > 0 && (
        <div>
          <p style={{ fontSize:10, fontWeight:700, letterSpacing:'0.1em', color:'rgba(255,255,255,0.22)', textTransform:'uppercase', marginBottom:8 }}>
            Progress Log
          </p>
          <div style={{ display:'flex', flexDirection:'column', gap:4, maxHeight:80, overflowY:'auto' }}>
            {messages.map((m,i)=>(
              <div key={i} style={{ display:'flex', gap:6, fontSize:12, color:'rgba(255,255,255,0.4)' }}>
                <span style={{ color:'rgba(220,20,60,0.45)', flexShrink:0 }}>›</span>
                <span>{m}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div>
          <p style={{ fontSize:10, fontWeight:700, letterSpacing:'0.1em', color:'rgba(255,255,255,0.22)', textTransform:'uppercase', marginBottom:10 }}>
            Results
          </p>
          <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
            {results.map(r => <IterCard key={r.iteration} result={r} />)}
          </div>
        </div>
      )}

      {/* Empty */}
      {!isRunning && results.length === 0 && (
        <div style={{ textAlign:'center', padding:'32px 0' }}>
          <div style={{ width:36, height:36, borderRadius:10, border:'1px solid rgba(220,20,60,0.2)', margin:'0 auto 12px', display:'flex', alignItems:'center', justifyContent:'center' }}>
            <div style={{ width:12, height:12, borderRadius:'50%', border:'2px solid rgba(220,20,60,0.4)', borderTopColor:'rgba(220,20,60,0.1)' }}/>
          </div>
          <p style={{ fontSize:13, color:'rgba(255,255,255,0.2)' }}>No runs yet. Submit a request to begin.</p>
        </div>
      )}

      <style suppressHydrationWarning>{`@keyframes blink-i{0%,100%{opacity:1}50%{opacity:0.15}}`}</style>
    </div>
  )
}

function IterCard({ result }: { result: IterationResult }) {
  const pct  = Math.round(result.similarity_score * 100)
  const good = pct >= 80
  const mid  = pct >= 60

  const barBg    = good ? 'linear-gradient(90deg,#22c55e,#4ade80)' : mid ? 'linear-gradient(90deg,#f59e0b,#fbbf24)' : 'linear-gradient(90deg,#DC143C,#ff4d6d)'
  const scoreClr = good ? '#4ade80' : mid ? '#fbbf24' : '#DC143C'

  const shotUrl = result.screenshot_path
    ? `file:///${result.screenshot_path.replace(/\\/g,'/')}`
    : null

  return (
    <div style={{
      padding:'14px 16px', borderRadius:12, transition:'all 0.3s',
      background: result.passed ? 'rgba(34,197,94,0.04)' : 'rgba(255,255,255,0.02)',
      border:     result.passed ? '1px solid rgba(34,197,94,0.18)' : '1px solid rgba(255,255,255,0.05)',
    }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:13, fontWeight:700, color:'#fff' }}>Iteration {result.iteration}</span>
          {result.passed && (
            <span style={{
              padding:'2px 8px', borderRadius:99, fontSize:10, fontWeight:700,
              background:'rgba(34,197,94,0.1)', border:'1px solid rgba(34,197,94,0.25)', color:'#4ade80',
            }}>PASSED</span>
          )}
        </div>
        <span style={{ fontSize:18, fontWeight:900, color:scoreClr, textShadow:`0 0 10px ${scoreClr}55` }}>{pct}%</span>
      </div>

      {/* Bar */}
      <div style={{ height:3, borderRadius:99, background:'rgba(255,255,255,0.06)', overflow:'hidden', marginBottom:10 }}>
        <div style={{ height:'100%', width:`${pct}%`, borderRadius:99, background:barBg, transition:'width 0.7s ease' }}/>
      </div>

      {result.visual_diff_notes && !result.visual_diff_notes.includes('could not') && (
        <p style={{ fontSize:12, color:'rgba(255,255,255,0.38)', lineHeight:1.55, marginBottom:8 }}>
          {result.visual_diff_notes}
        </p>
      )}

      {result.suggestions.length > 0 && !result.passed && (
        <ul style={{ display:'flex', flexDirection:'column', gap:4, marginBottom:8 }}>
          {result.suggestions.map((s,i)=>(
            <li key={i} style={{ display:'flex', gap:6, fontSize:11, color:'rgba(255,255,255,0.32)' }}>
              <span style={{ color:'rgba(220,20,60,0.5)', flexShrink:0 }}>·</span>{s}
            </li>
          ))}
        </ul>
      )}

      {shotUrl && (
        <a href={shotUrl} target="_blank" rel="noopener noreferrer"
          style={{ fontSize:11, fontWeight:600, color:'rgba(220,20,60,0.65)', textDecoration:'none', display:'inline-block' }}>
          View Screenshot ↗
        </a>
      )}
    </div>
  )
}