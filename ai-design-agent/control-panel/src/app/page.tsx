// 'use client'
// import { useState, useCallback } from 'react'
// import { UIProvider, useUI } from '@/context/UIContext'
// import UIToggle from '@/components/shared/UIToggle'
// import QuotaIndicator from '@/components/shared/QuotaIndicator'
// import BasicLayout from '@/components/basic/BasicLayout'
// import EnhancedLayout from '@/components/enhanced/EnhancedLayout'
// import { RunRequest, RunStatus, startRun, pollUntilComplete } from '@/lib/api'

// function AppContent() {
//   const { isEnhanced } = useUI()
//   const [status, setStatus]     = useState<RunStatus | null>(null)
//   const [isRunning, setRunning] = useState(false)
//   const [error, setError]       = useState<string | null>(null)

//   const handleSubmit = useCallback(async (request: RunRequest) => {
//     setRunning(true)
//     setError(null)
//     setStatus(null)
//     try {
//       const { run_id } = await startRun(request)
//       await pollUntilComplete(run_id, setStatus, 5000)
//     } catch (e) {
//       setError(e instanceof Error ? e.message : 'Unknown error')
//     } finally {
//       setRunning(false)
//     }
//   }, [])

//   return (
//     <div className="relative min-h-screen">
//       {/* Fixed top bar */}
//       <div className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between
//         px-5 py-2.5 bg-[#0a0f1e]/90 backdrop-blur-md border-b border-[#1e293b]/80">
//         <div className="flex items-center gap-2">
//           <span className="text-indigo-400 font-black text-sm tracking-wider">AI ZONED</span>
//           <span className="text-slate-700 text-xs">·</span>
//           <span className="text-slate-500 text-xs">Design Agent</span>
//         </div>
//         <div className="flex items-center gap-4">
//           <QuotaIndicator />
//           <UIToggle />
//         </div>
//       </div>

//       {/* Content offset for fixed bar */}
//       <div className="pt-12">
//         {error && (
//           <div className="mx-5 mt-4 p-3 bg-red-950/40 border border-red-800/50 rounded-xl
//             text-red-400 text-xs flex items-center justify-between">
//             <span>❌ {error}</span>
//             <button onClick={() => setError(null)} className="text-red-400 hover:text-white ml-3">×</button>
//           </div>
//         )}
//         {isEnhanced
//           ? <EnhancedLayout status={status} isRunning={isRunning} onSubmit={handleSubmit} />
//           : <BasicLayout    status={status} isRunning={isRunning} onSubmit={handleSubmit} />
//         }
//       </div>
//     </div>
//   )
// }

// export default function Home() {
//   return <UIProvider><AppContent /></UIProvider>
// }


'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { Component, ReactNode } from 'react'
import InputPanel        from '@/components/shared/InputPanel'
import IterationViewer   from '@/components/shared/IterationViewer'
import OutputPanel       from '@/components/shared/OutputPanel'
import QuotaIndicator    from '@/components/shared/QuotaIndicator'
import { RunRequest, RunStatus, startRun, pollUntilComplete } from '@/lib/api'

// ─────────────────────────────────────────────────────────────────────────────
// Particle canvas — animated crimson dots flying through space
// ─────────────────────────────────────────────────────────────────────────────
function ParticleCanvas() {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    // Floating dots
    const dots = Array.from({ length: 70 }, () => ({
      x:  Math.random() * window.innerWidth,
      y:  Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.22,
      vy: (Math.random() - 0.5) * 0.22,
      r:  Math.random() * 1.6 + 0.2,
      o:  Math.random() * 0.30 + 0.06,
    }))

    // Connection lines between nearby dots
    let raf: number
    const tick = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Draw connections
      for (let i = 0; i < dots.length; i++) {
        for (let j = i + 1; j < dots.length; j++) {
          const dx = dots[i].x - dots[j].x
          const dy = dots[i].y - dots[j].y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 120) {
            ctx.beginPath()
            ctx.moveTo(dots[i].x, dots[i].y)
            ctx.lineTo(dots[j].x, dots[j].y)
            ctx.strokeStyle = `rgba(220,20,60,${0.06 * (1 - dist / 120)})`
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        }
      }

      // Draw dots
      dots.forEach(p => {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0)             p.x = canvas.width
        if (p.x > canvas.width)  p.x = 0
        if (p.y < 0)             p.y = canvas.height
        if (p.y > canvas.height) p.y = 0
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(220,20,60,${p.o})`
        ctx.fill()
      })

      raf = requestAnimationFrame(tick)
    }
    tick()

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={ref}
      style={{
        position: 'fixed', inset: 0,
        zIndex: 0, pointerEvents: 'none', opacity: 0.75,
      }}
    />
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main app
// ─────────────────────────────────────────────────────────────────────────────
export default function Home() {
  const [status,    setStatus]    = useState<RunStatus | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error,     setError]     = useState<string | null>(null)

  const handleSubmit = useCallback(async (request: RunRequest) => {
    setIsRunning(true)
    setError(null)
    setStatus(null)
    try {
      const { run_id } = await startRun(request)
      await pollUntilComplete(run_id, setStatus, 5000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error occurred')
    } finally {
      setIsRunning(false)
    }
  }, [])

  return (
    <div style={{ minHeight: '100vh', background: '#060608', position: 'relative' }}>

      {/* ── Layer 0: Animated particle canvas ── */}
      <ParticleCanvas />

      {/* ── Layer 1: Radial glow overlays ── */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 2, pointerEvents: 'none',
        background:
          'radial-gradient(ellipse 80% 50% at 50% -5%, rgba(220,20,60,0.10) 0%, transparent 65%),' +
          'radial-gradient(ellipse 40% 30% at 95% 95%, rgba(220,20,60,0.05) 0%, transparent 60%)',
      }} />

      {/* ── Layer 2: Fixed top navbar ── */}
      <header style={{
        position:             'fixed',
        top: 0, left: 0, right: 0,
        zIndex:               50,
        height:               52,
        display:              'flex',
        alignItems:           'center',
        justifyContent:       'space-between',
        padding:              '0 24px',
        background:           'rgba(6,6,8,0.88)',
        backdropFilter:       'blur(22px)',
        WebkitBackdropFilter: 'blur(22px)',
        borderBottom:         '1px solid rgba(220,20,60,0.14)',
      }}>

        {/* Left — brand */}
        <div style={{
          display: 'flex', alignItems: 'center',
          gap: 10, flexShrink: 0,
        }}>
          {/* Logo */}
          <div style={{
            width: 28, height: 28, borderRadius: 8, flexShrink: 0,
            background: '#DC143C',
            boxShadow:  '0 0 14px rgba(220,20,60,0.65)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 900, color: '#fff',
          }}>A</div>

          <span style={{
            fontSize: 14, fontWeight: 800, color: '#fff',
            letterSpacing: '0.06em', whiteSpace: 'nowrap',
          }}>
            AI ZONED
          </span>

          <span style={{
            fontSize: 12, color: 'rgba(255,255,255,0.22)',
            whiteSpace: 'nowrap',
          }}>
            / Design Agent
          </span>

          {/* Running pill */}
          {isRunning && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '3px 10px', borderRadius: 99,
              background: 'rgba(220,20,60,0.12)',
              border:     '1px solid rgba(220,20,60,0.28)',
              fontSize: 11, fontWeight: 700, color: '#DC143C',
              whiteSpace: 'nowrap',
            }}>
              {[0, 120, 240].map(d => (
                <span key={d} style={{
                  width: 4, height: 4, borderRadius: '50%',
                  background: '#DC143C', display: 'inline-block',
                  animation: `blink-dot 1s ease ${d}ms infinite`,
                }} />
              ))}
              Generating
            </div>
          )}
        </div>

        {/* Right — quota */}
        <QuotaIndicator />
      </header>

      {/* ── Layer 3: Page content ── */}
      <main style={{ position: 'relative', zIndex: 10, paddingTop: 52 }}>

        {/* Hero */}
        <div style={{ textAlign: 'center', padding: '44px 20px 32px' }}>
          <h1 style={{
            fontSize: 'clamp(30px, 5vw, 52px)',
            fontWeight: 900,
            letterSpacing: '-0.03em',
            lineHeight: 1.05,
            marginBottom: 10,
            background: 'linear-gradient(135deg, #ffffff 0%, #DC143C 55%, #ff7070 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>
            AI Design Agent
          </h1>
          <p style={{
            fontSize: 13,
            color: 'rgba(255,255,255,0.30)',
            letterSpacing: '0.025em',
          }}>
            Agentic generation · Gemini 2.5 Flash · LangGraph · Next.js 14
          </p>
        </div>

        {/* Error banner */}
        {error && (
          <div style={{
            maxWidth: 1280, margin: '0 auto 16px', padding: '10px 16px',
            borderRadius: 10, display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', fontSize: 13,
            background: 'rgba(239,68,68,0.08)',
            border:     '1px solid rgba(239,68,68,0.25)',
            color:      '#f87171',
          }}>
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              style={{
                background: 'none', border: 'none', color: '#f87171',
                cursor: 'pointer', fontSize: 18, lineHeight: 1, marginLeft: 12,
              }}
            >×</button>
          </div>
        )}

        {/* 3-column grid */}
        <div style={{
          maxWidth: 1280,
          margin:   '0 auto',
          padding:  '0 20px 48px',
          display:  'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: 16,
        }}>
          <InputPanel      onSubmit={handleSubmit} isRunning={isRunning} />
          <IterationViewer status={status}          isRunning={isRunning} />
          <OutputPanel     status={status} />
        </div>

        {/* Footer */}
        <p style={{
          textAlign: 'center', paddingBottom: 32,
          fontSize: 11, color: 'rgba(255,255,255,0.09)',
          letterSpacing: '0.08em',
        }}>
          LANGRAPH · GEMINI VISION · PLAYWRIGHT · NEXT.JS 14
        </p>
      </main>

      {/* Global keyframes */}
      <style suppressHydrationWarning>{`
        @keyframes blink-dot {
          0%,100% { opacity: 1;    }
          50%      { opacity: 0.15; }
        }
      `}</style>
    </div>
  )
}