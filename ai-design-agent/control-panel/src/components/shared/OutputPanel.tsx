// 'use client'
// import { useUI } from '@/context/UIContext'
// import { RunStatus } from '@/lib/api'

// interface Props { status: RunStatus | null }

// interface PageLink {
//   label: string
//   route: string
// }

// const PAGE_LINKS: PageLink[] = [
//   { label: 'Landing', route: '/' },
//   { label: 'About',   route: '/about' },
//   { label: 'Contact', route: '/contact' },
//   { label: 'Products',route: '/products' },
// ]

// export default function OutputPanel({ status }: Props) {
//   const { isEnhanced } = useUI()

//   const card = isEnhanced
//     ? 'bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6'
//     : 'bg-[#111827] border border-[#1f2937] rounded-xl p-5'

//   // ── Empty state ────────────────────────────────────────────────────────────
//   if (!status || status.status !== 'complete') {
//     return (
//       <div className={card}>
//         <div className="flex items-center gap-2 mb-5">
//           <span className="text-lg">📦</span>
//           <h2 className="text-sm font-bold text-white uppercase tracking-widest">
//             Output
//           </h2>
//         </div>
//         <div className="text-center py-10">
//           <div className="text-3xl mb-2">⏳</div>
//           <p className="text-sm text-gray-500">
//             Output appears here when generation completes.
//           </p>
//         </div>
//       </div>
//     )
//   }

//   // ── Compute values ─────────────────────────────────────────────────────────
//   const runId = (status.final_output_path ?? '')
//     .replace(/\\/g, '/')
//     .split('/')
//     .pop() ?? ''

//   const path = (status.final_output_path ?? '').replace(/\\/g, '/')

//   const best = status.iteration_results.length > 0
//     ? status.iteration_results.reduce((a, b) =>
//         a.similarity_score > b.similarity_score ? a : b
//       )
//     : null

//   const score = best ? Math.round(best.similarity_score * 100) : 0

//   const stats = [
//     { key: 'Run ID',      value: runId },
//     { key: 'Iterations',  value: status.current_iteration + ' / ' + status.max_iterations },
//     { key: 'Best Score',  value: score + '%', highlight: score >= 75 },
//   ]

//   const commands = [
//     'cd "' + path + '"',
//     'npm install',
//     'npm run dev',
//   ]

//   // ── Render ─────────────────────────────────────────────────────────────────
//   return (
//     <div className={card}>

//       {/* Header */}
//       <div className="flex items-center gap-2 mb-5">
//         <span className="text-lg">📦</span>
//         <h2 className="text-sm font-bold text-white uppercase tracking-widest">
//           Output
//         </h2>
//       </div>

//       {/* Success banner */}
//       <div className="mb-5 p-4 rounded-xl bg-green-950/30 border border-green-800/40">
//         <div className="flex items-center gap-2 mb-1">
//           <span className="text-green-400">✅</span>
//           <span className="font-bold text-green-400 text-sm">
//             Generation Complete!
//           </span>
//         </div>
//         <p className="text-xs text-gray-500">
//           {status.current_iteration} iteration(s) · Best score: {score}%
//         </p>
//       </div>

//       {/* Stats rows */}
//       <div className="space-y-0 mb-5">
//         {stats.map((s) => (
//           <div
//             key={s.key}
//             className="flex justify-between items-center py-2 border-b border-white/5"
//           >
//             <span className="text-xs text-gray-500 font-medium">{s.key}</span>
//             <span
//               className={
//                 'text-xs font-bold ' +
//                 (s.highlight ? 'text-green-400' : 'text-white')
//               }
//             >
//               {s.value}
//             </span>
//           </div>
//         ))}
//       </div>

//       {/* Preview instructions */}
//       <div className="mb-5">
//         <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-2">
//           Preview Generated Site
//         </p>
//         <div className="bg-[#0d1117] rounded-xl p-4 border border-[#1f2937]">
//           <p className="text-xs text-yellow-400 font-bold mb-3 flex items-center gap-1.5">
//             <span>⚠️</span>
//             Run these commands first:
//           </p>

//           {/* Commands */}
//           <div className="space-y-1 mb-3">
//             {commands.map((cmd) => (
//               <p key={cmd} className="font-mono text-xs text-green-400">
//                 {cmd}
//               </p>
//             ))}
//           </div>

//           {/* Link */}
//           <div className="pt-3 border-t border-[#1f2937]">
//             <p className="text-xs text-gray-600 mb-1">Then open in browser:</p>
//             <a
//               href="http://localhost:3000"
//               target="_blank"
//               rel="noopener noreferrer"
//               className="text-xs text-indigo-400 hover:text-indigo-300 hover:underline font-mono transition-colors"
//             >
//               http://localhost:3000 ↗
//             </a>
//           </div>
//         </div>
//       </div>

//       {/* Generated page links */}
//       <div>
//         <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-2">
//           Generated Pages
//         </p>
//         <div className="grid grid-cols-2 gap-2">
//           {PAGE_LINKS.map(({ label, route }) => {
//             const href = 'http://localhost:3000' + route
//             const cls = isEnhanced
//               ? 'bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 hover:bg-indigo-500/20 hover:text-white'
//               : 'bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10 hover:text-white'
//             return (
//               <a
//                 key={label}
//                 href={href}
//                 target="_blank"
//                 rel="noopener noreferrer"
//                 className={
//                   'text-center py-2.5 px-3 rounded-xl text-xs font-bold ' +
//                   'transition-all duration-200 hover:scale-[1.02] ' +
//                   cls
//                 }
//               >
//                 {label} ↗
//               </a>
//             )
//           })}
//         </div>
//         <p className="text-xs text-gray-700 mt-2 text-center">
//           Links work only after npm run dev is running
//         </p>
//       </div>

//     </div>
//   )
// }

'use client'

import { RunStatus } from '@/lib/api'

interface Props { status: RunStatus | null }

const SectionLabel = ({ children }: { children: string }) => (
  <p style={{ fontSize:10, fontWeight:700, letterSpacing:'0.12em', textTransform:'uppercase', color:'rgba(255,255,255,0.28)', marginBottom:8 }}>
    {children}
  </p>
)

export default function OutputPanel({ status }: Props) {
  const cardStyle = {
    borderRadius: 18, padding: 24, display: 'flex', flexDirection: 'column' as const, gap: 18,
  }

  if (!status || status.status !== 'complete') {
    return (
      <div className="glass-card" style={cardStyle}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ width:3, height:16, borderRadius:99, background:'linear-gradient(180deg,#DC143C,#ff4d6d)', display:'inline-block' }}/>
          <h2 style={{ fontSize:11, fontWeight:700, letterSpacing:'0.12em', color:'rgba(255,255,255,0.55)', textTransform:'uppercase' }}>Output</h2>
        </div>
        <div style={{ textAlign:'center', padding:'32px 0' }}>
          <div style={{
            width:44, height:44, borderRadius:12, margin:'0 auto 14px',
            border:'1px solid rgba(220,20,60,0.18)',
            display:'flex', alignItems:'center', justifyContent:'center',
          }}>
            <div style={{ width:18, height:18, borderRadius:'50%', border:'2px solid rgba(220,20,60,0.3)', borderTopColor:'rgba(220,20,60,0.08)' }}/>
          </div>
          <p style={{ fontSize:13, color:'rgba(255,255,255,0.22)' }}>
            Output appears here when generation completes.
          </p>
        </div>
      </div>
    )
  }

  const runId = (status.final_output_path ?? '').replace(/\\/g,'/').split('/').pop() ?? ''
  const path  = (status.final_output_path ?? '').replace(/\\/g,'/')

  const best  = status.iteration_results.length > 0
    ? status.iteration_results.reduce((a,b) => a.similarity_score > b.similarity_score ? a : b)
    : null
  const score = best ? Math.round(best.similarity_score * 100) : 0

  const rows: [string, string][] = [
    ['Run ID',     runId],
    ['Iterations', `${status.current_iteration} / ${status.max_iterations}`],
    ['Best Score', `${score}%`],
  ]

  const pages: [string, string][] = [
    ['Landing', '/'], ['About', '/about'], ['Contact', '/contact'], ['Products', '/products'],
  ]

  const cmds = [`cd "${path}"`, 'npm install', 'npm run dev']

  return (
    <div className="glass-card" style={cardStyle}>

      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
        <span style={{ width:3, height:16, borderRadius:99, background:'linear-gradient(180deg,#DC143C,#ff4d6d)', display:'inline-block' }}/>
        <h2 style={{ fontSize:11, fontWeight:700, letterSpacing:'0.12em', color:'rgba(255,255,255,0.55)', textTransform:'uppercase' }}>Output</h2>
      </div>

      {/* Success */}
      <div style={{ padding:'12px 14px', borderRadius:12, background:'rgba(34,197,94,0.05)', border:'1px solid rgba(34,197,94,0.18)' }}>
        <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
          <div style={{ width:8, height:8, borderRadius:'50%', background:'#4ade80', boxShadow:'0 0 6px #4ade80', flexShrink:0 }}/>
          <span style={{ fontWeight:700, fontSize:13, color:'#4ade80' }}>Generation Complete</span>
        </div>
        <p style={{ fontSize:11, color:'rgba(255,255,255,0.32)' }}>
          {status.current_iteration} iteration(s) · Best score: {score}%
        </p>
      </div>

      {/* Stats */}
      <div>
        {rows.map(([k,v]) => (
          <div key={k} style={{
            display:'flex', justifyContent:'space-between', alignItems:'center',
            padding:'9px 0', borderBottom:'1px solid rgba(255,255,255,0.04)',
          }}>
            <span style={{ fontSize:12, color:'rgba(255,255,255,0.32)', fontWeight:500 }}>{k}</span>
            <span style={{
              fontSize:12, fontWeight:700,
              color: k==='Best Score' && score>=75 ? '#4ade80' : '#fff',
            }}>{v}</span>
          </div>
        ))}
      </div>

      {/* Preview instructions */}
      <div>
        <SectionLabel>Preview Generated Site</SectionLabel>
        <div style={{ padding:'14px 16px', borderRadius:12, background:'rgba(0,0,0,0.4)', border:'1px solid rgba(255,255,255,0.06)' }}>
          <p style={{ fontSize:11, fontWeight:700, color:'#f59e0b', marginBottom:10 }}>
            Run these commands first:
          </p>
          <div style={{ display:'flex', flexDirection:'column', gap:4, marginBottom:12 }}>
            {cmds.map(c => (
              <code key={c} style={{ fontSize:11, color:'#4ade80', fontFamily:'monospace' }}>{c}</code>
            ))}
          </div>
          <div style={{ borderTop:'1px solid rgba(255,255,255,0.06)', paddingTop:10 }}>
            <p style={{ fontSize:11, color:'rgba(255,255,255,0.2)', marginBottom:4 }}>Then open:</p>
            <a href="http://localhost:3000" target="_blank" rel="noopener noreferrer"
              style={{ fontSize:12, fontFamily:'monospace', color:'rgba(220,20,60,0.75)', textDecoration:'none', fontWeight:600 }}>
              http://localhost:3000 ↗
            </a>
          </div>
        </div>
      </div>

      {/* Page links */}
      <div>
        <SectionLabel>Generated Pages</SectionLabel>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8 }}>
          {pages.map(([label, route]) => (
            <a key={label}
              href={`http://localhost:3000${route}`}
              target="_blank" rel="noopener noreferrer"
              style={{
                textAlign:'center', padding:'10px 12px', borderRadius:10,
                fontSize:12, fontWeight:700, textDecoration:'none',
                background:'rgba(220,20,60,0.07)',
                border:'1px solid rgba(220,20,60,0.18)',
                color:'rgba(255,100,100,0.85)',
                transition:'all 0.2s',
              }}
            >
              {label} ↗
            </a>
          ))}
        </div>
        <p style={{ fontSize:10, color:'rgba(255,255,255,0.15)', marginTop:8, textAlign:'center' }}>
          Links work only after npm run dev is running
        </p>
      </div>
    </div>
  )
}