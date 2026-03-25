// 'use client'
// import { useEffect, useRef } from 'react'
// import InputPanel from '@/components/shared/InputPanel'
// import IterationViewer from '@/components/shared/IterationViewer'
// import OutputPanel from '@/components/shared/OutputPanel'
// import { RunRequest, RunStatus } from '@/lib/api'

// interface Props { status: RunStatus|null; isRunning: boolean; onSubmit: (r: RunRequest) => void }

// export default function EnhancedLayout({ status, isRunning, onSubmit }: Props) {
//   const canvasRef = useRef<HTMLCanvasElement>(null)

//   // 3D particle field using Canvas API — no external deps needed
//   useEffect(() => {
//     const canvas = canvasRef.current
//     if (!canvas) return
//     const ctx = canvas.getContext('2d')
//     if (!ctx) return

//     const resize = () => {
//       canvas.width  = window.innerWidth
//       canvas.height = window.innerHeight
//     }
//     resize()
//     window.addEventListener('resize', resize)

//     // Particles
//     const particles = Array.from({ length: 80 }, () => ({
//       x: Math.random() * canvas.width,
//       y: Math.random() * canvas.height,
//       z: Math.random() * 1000,
//       vz: -(Math.random() * 2 + 0.5),
//       r: Math.random() * 2 + 0.5,
//     }))

//     let frame: number
//     const draw = () => {
//       ctx.fillStyle = 'rgba(10, 15, 30, 0.15)'
//       ctx.fillRect(0, 0, canvas.width, canvas.height)

//       const cx = canvas.width / 2
//       const cy = canvas.height / 2

//       particles.forEach(p => {
//         p.z += p.vz
//         if (p.z <= 0) p.z = 1000

//         const scale = 600 / p.z
//         const x = (p.x - cx) * scale + cx
//         const y = (p.y - cy) * scale + cy
//         const r = p.r * scale

//         const alpha = Math.min(1, (1000 - p.z) / 600)
//         const hue = 240 + (p.z / 10) % 60

//         ctx.beginPath()
//         ctx.arc(x, y, Math.max(0.1, r), 0, Math.PI * 2)
//         ctx.fillStyle = `hsla(${hue}, 70%, 70%, ${alpha})`
//         ctx.fill()
//       })

//       frame = requestAnimationFrame(draw)
//     }
//     draw()

//     return () => {
//       cancelAnimationFrame(frame)
//       window.removeEventListener('resize', resize)
//     }
//   }, [])

//   return (
//     <div className="min-h-screen relative overflow-hidden" style={{ background: '#0a0f1e' }}>
//       {/* 3D Particle Canvas */}
//       <canvas
//         ref={canvasRef}
//         className="absolute inset-0 pointer-events-none"
//         style={{ zIndex: 0 }}
//       />

//       {/* Gradient overlays */}
//       <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 1 }}>
//         <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl" />
//         <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl" />
//       </div>

//       {/* Content */}
//       <div className="relative p-6" style={{ zIndex: 2 }}>
//         {/* Header */}
//         <div className="text-center mb-8">
//           <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
//             bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs
//             font-semibold uppercase tracking-widest mb-4">
//             <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
//             Enhanced Mode · 3D Active
//           </div>
//           <h1 className="text-4xl font-black mb-2 gradient-text">AI Design Agent</h1>
//           <p className="text-slate-500 text-sm">
//             Agentic generation · Gemini 2.5 Flash · LangGraph · Next.js 14
//           </p>
//           {isRunning && (
//             <div className="mt-4 inline-flex items-center gap-2 px-5 py-2 rounded-full
//               bg-indigo-900/40 border border-indigo-700/50 glow-pulse">
//               <span className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
//               <span className="text-sm text-indigo-300 font-medium">Agent is running...</span>
//             </div>
//           )}
//         </div>

//         {/* Grid */}
//         <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 max-w-7xl mx-auto">
//           <InputPanel onSubmit={onSubmit} isRunning={isRunning} />
//           <IterationViewer status={status} isRunning={isRunning} />
//           <OutputPanel status={status} />
//         </div>

//         {/* Footer */}
//         <p className="text-center text-xs text-slate-700 mt-8">
//           Built with LangGraph · Gemini Vision · Playwright · Next.js 14
//         </p>
//       </div>
//     </div>
//   )
// }