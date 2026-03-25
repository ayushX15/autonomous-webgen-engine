// 'use client'
// import { useState } from 'react'
// import { useUI } from '@/context/UIContext'
// import { RunRequest } from '@/lib/api'

// interface Props {
//   onSubmit: (r: RunRequest) => void
//   isRunning: boolean
// }

// export default function InputPanel({ onSubmit, isRunning }: Props) {
//   const { isEnhanced } = useUI()
//   const [req, setReq]           = useState('')
//   const [urlInput, setUrlInput] = useState('')
//   const [urls, setUrls]         = useState<string[]>([])
//   const [pages, setPages]       = useState('index,about,contact')
//   const [maxIter, setMaxIter]   = useState(2)

//   const addUrl = () => {
//     const u = urlInput.trim()
//     if (u && !urls.includes(u)) { setUrls([...urls, u]); setUrlInput('') }
//   }

//   const card = isEnhanced
//     ? 'bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6'
//     : 'bg-[#111827] border border-[#1f2937] rounded-xl p-5'

//   const input = [
//     'w-full rounded-xl px-4 py-3 text-sm font-medium',
//     'bg-[#0d1117] border border-[#1f2937]',
//     'text-white placeholder-gray-600',
//     'focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40',
//     'transition-all duration-200'
//   ].join(' ')

//   const label = 'block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2'

//   return (
//     <div className={card}>
//       {/* Header */}
//       <div className="flex items-center gap-2 mb-5">
//         <span className="text-lg">🎨</span>
//         <h2 className="text-sm font-bold text-white uppercase tracking-widest">
//           Design Requirements
//         </h2>
//       </div>

//       {/* Requirement textarea */}
//       <div className="mb-4">
//         <label className={label}>What to build? *</label>
//         <textarea
//           className={`${input} h-28 resize-none leading-relaxed`}
//           placeholder="e.g. A modern SaaS landing page for a project management tool with dark theme, hero banner, and feature sections..."
//           value={req}
//           onChange={e => setReq(e.target.value)}
//           disabled={isRunning}
//           style={{ color: '#ffffff' }}
//         />
//       </div>

//       {/* Reference URLs */}
//       <div className="mb-4">
//         <label className={label}>Reference Sites (optional)</label>
//         <div className="flex gap-2 mb-2">
//           <input
//             className={`${input} flex-1`}
//             placeholder="https://stripe.com"
//             value={urlInput}
//             onChange={e => setUrlInput(e.target.value)}
//             onKeyDown={e => e.key === 'Enter' && addUrl()}
//             disabled={isRunning}
//           />
//           <button
//             onClick={addUrl}
//             disabled={isRunning || !urlInput.trim()}
//             className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40
//                        text-white text-sm font-bold rounded-xl transition-colors"
//           >
//             Add
//           </button>
//         </div>
//         {/* URL tags */}
//         {urls.length > 0 && (
//           <div className="flex flex-wrap gap-1.5 mt-2">
//             {urls.map(u => (
//               <span key={u}
//                 className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium
//                            bg-indigo-500/15 border border-indigo-500/30 text-indigo-300">
//                 🔗 {u.replace(/^https?:\/\//, '').slice(0, 30)}
//                 <button
//                   onClick={() => setUrls(urls.filter(x => x !== u))}
//                   className="text-indigo-400 hover:text-white transition-colors ml-0.5 font-bold"
//                 >×</button>
//               </span>
//             ))}
//           </div>
//         )}
//       </div>

//       {/* Pages */}
//       <div className="mb-4">
//         <label className={label}>Pages to Generate</label>
//         <input
//           className={input}
//           placeholder="index,about,contact,products"
//           value={pages}
//           onChange={e => setPages(e.target.value)}
//           disabled={isRunning}
//         />
//         <p className="text-xs text-gray-600 mt-1.5 font-medium">
//           Comma separated · First = landing page
//         </p>
//       </div>

//       {/* Iterations — MAX 3 */}
//       <div className="mb-6">
//         <div className="flex justify-between items-center mb-2">
//           <label className={label} style={{ marginBottom: 0 }}>Max Iterations</label>
//           <span className="text-indigo-400 font-black text-lg">{maxIter}</span>
//         </div>
//         <input
//           type="range"
//           min={1}
//           max={3}
//           step={1}
//           value={maxIter}
//           onChange={e => setMaxIter(Number(e.target.value))}
//           disabled={isRunning}
//           className="w-full accent-indigo-500"
//           style={{ height: '4px' }}
//         />
//         <div className="flex justify-between text-xs text-gray-600 mt-1 font-medium">
//           <span>1 — Fastest</span>
//           <span>2 — Balanced</span>
//           <span>3 — Best Quality</span>
//         </div>
//       </div>

//       {/* Submit */}
//       <button
//         onClick={() => onSubmit({
//           user_requirement: req,
//           reference_urls: urls,
//           reference_image_paths: [],
//           pages_requested: pages.split(',').map(p => p.trim()).filter(Boolean),
//           max_iterations: maxIter
//         })}
//         disabled={isRunning || !req.trim()}
//         className={[
//           'w-full py-3.5 rounded-xl font-bold text-sm text-white transition-all duration-300',
//           isRunning || !req.trim()
//             ? 'bg-gray-700 opacity-50 cursor-not-allowed'
//             : isEnhanced
//               ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 hover:shadow-lg hover:shadow-indigo-500/25 hover:scale-[1.02]'
//               : 'bg-indigo-600 hover:bg-indigo-500 hover:shadow-lg hover:shadow-indigo-500/20'
//         ].join(' ')}
//       >
//         {isRunning
//           ? <span className="flex items-center justify-center gap-2">
//               <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
//               Generating...
//             </span>
//           : '🚀 Generate Website'
//         }
//       </button>
//     </div>
//   )
// }


'use client'

import { useState } from 'react'
import { RunRequest } from '@/lib/api'

interface Props { onSubmit: (r: RunRequest) => void; isRunning: boolean }

export default function InputPanel({ onSubmit, isRunning }: Props) {
  const [req,      setReq]      = useState('')
  const [urlInput, setUrlInput] = useState('')
  const [urls,     setUrls]     = useState<string[]>([])
  const [pages,    setPages]    = useState('index,about,contact')
  const [maxIter,  setMaxIter]  = useState(2)

  const addUrl = () => {
    const u = urlInput.trim()
    if (u && !urls.includes(u)) { setUrls([...urls, u]); setUrlInput('') }
  }

  return (
    <div className="glass-card" style={{ borderRadius: 18, padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
          <span style={{
            width: 3, height: 16, borderRadius: 99,
            background: 'linear-gradient(180deg,#DC143C,#ff4d6d)',
            display: 'inline-block', flexShrink: 0,
          }} />
          <h2 style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.55)', textTransform: 'uppercase' }}>
            Design Requirements
          </h2>
        </div>
      </div>

      {/* Requirement */}
      <div>
        <label className="section-label">What to build *</label>
        <textarea
          className="ctrl-input"
          style={{ height: 108, resize: 'none', lineHeight: 1.65 }}
          placeholder="e.g. A modern SaaS landing page with dark theme, hero section, feature cards and pricing..."
          value={req}
          onChange={e => setReq(e.target.value)}
          disabled={isRunning}
        />
      </div>

      {/* Reference URLs */}
      <div>
        <label className="section-label">Reference Sites</label>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <input
            className="ctrl-input"
            style={{ flex: 1 }}
            placeholder="https://stripe.com"
            value={urlInput}
            onChange={e => setUrlInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addUrl()}
            disabled={isRunning}
          />
          <button
            onClick={addUrl}
            disabled={isRunning || !urlInput.trim()}
            style={{
              padding: '0 18px', borderRadius: 10, fontWeight: 700, fontSize: 13,
              color: '#fff', border: 'none', cursor: 'pointer', flexShrink: 0,
              background: '#DC143C',
              boxShadow: '0 0 14px rgba(220,20,60,0.45)',
              opacity: (isRunning || !urlInput.trim()) ? 0.35 : 1,
              transition: 'opacity 0.2s',
            }}
          >Add</button>
        </div>

        {urls.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {urls.map(u => (
              <span key={u} style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '4px 10px', borderRadius: 99, fontSize: 11, fontWeight: 600,
                background: 'rgba(220,20,60,0.1)',
                border:     '1px solid rgba(220,20,60,0.22)',
                color:      'rgba(255,110,110,0.9)',
              }}>
                {u.replace(/^https?:\/\//, '').slice(0, 30)}
                <button
                  onClick={() => setUrls(urls.filter(x => x !== u))}
                  style={{ background:'none', border:'none', cursor:'pointer', color:'rgba(220,20,60,0.7)', fontWeight:900, fontSize:14, lineHeight:1 }}
                >×</button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Pages */}
      <div>
        <label className="section-label">Pages to Generate</label>
        <input
          className="ctrl-input"
          placeholder="index,about,contact,products"
          value={pages}
          onChange={e => setPages(e.target.value)}
          disabled={isRunning}
        />
        <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.2)', marginTop: 5 }}>
          Comma separated · First = landing page
        </p>
      </div>

      {/* Max iterations — slider max 3 */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <label className="section-label" style={{ marginBottom: 0 }}>Max Iterations</label>
          <span style={{ fontSize: 22, fontWeight: 900, color: '#DC143C', textShadow: '0 0 10px rgba(220,20,60,0.5)' }}>
            {maxIter}
          </span>
        </div>
        <input
          type="range" min={1} max={3} step={1} value={maxIter}
          onChange={e => setMaxIter(Number(e.target.value))}
          disabled={isRunning}
          style={{ width: '100%', accentColor: '#DC143C', height: 4 }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'rgba(255,255,255,0.2)', marginTop: 4, fontWeight: 600 }}>
          <span>1 — Fastest</span>
          <span>2 — Balanced</span>
          <span>3 — Best Quality</span>
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={() => onSubmit({
          user_requirement:      req,
          reference_urls:        urls,
          reference_image_paths: [],
          pages_requested:       pages.split(',').map(p => p.trim()).filter(Boolean),
          max_iterations:        maxIter,
        })}
        disabled={isRunning || !req.trim()}
        className={!isRunning && req.trim() ? 'glow-pulse' : ''}
        style={{
          width: '100%', padding: '13px 0', borderRadius: 12,
          fontWeight: 800, fontSize: 14, color: '#fff', border: 'none', cursor: 'pointer',
          background:
            isRunning || !req.trim()
              ? 'rgba(255,255,255,0.06)'
              : 'linear-gradient(135deg, #DC143C 0%, #a50e2b 100%)',
          opacity: isRunning || !req.trim() ? 0.45 : 1,
          transition: 'opacity 0.2s',
        }}
      >
        {isRunning
          ? (
            <span style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:8 }}>
              <span style={{
                width:16, height:16, borderRadius:'50%',
                border:'2.5px solid rgba(255,255,255,0.25)',
                borderTopColor:'#fff', animation:'spin-q 1s linear infinite',
              }} />
              Generating...
            </span>
          )
          : 'Generate Website'
        }
        <style suppressHydrationWarning>{`@keyframes spin-q{to{transform:rotate(360deg)}}`}</style>
      </button>
    </div>
  )
}