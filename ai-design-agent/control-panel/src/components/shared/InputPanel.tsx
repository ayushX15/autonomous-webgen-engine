'use client'

import { useState, useRef } from 'react'
import { RunRequest, uploadReferenceImage } from '@/lib/api'

interface Props { onSubmit: (r: RunRequest) => void; isRunning: boolean }

interface UploadedImage {
  id: string
  file: File
  previewUrl: string
  path: string | null
  uploading: boolean
  error: string | null
}

export default function InputPanel({ onSubmit, isRunning }: Props) {
  const [req,      setReq]      = useState('')
  const [urlInput, setUrlInput] = useState('')
  const [urls,     setUrls]     = useState<string[]>([])
  const [pages,    setPages]    = useState('index,about,contact')
  const [maxIter,  setMaxIter]  = useState(2)
  const [images,   setImages]   = useState<UploadedImage[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const addUrl = () => {
    const u = urlInput.trim()
    if (u && !urls.includes(u)) { setUrls([...urls, u]); setUrlInput('') }
  }

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    for (const file of Array.from(files)) {
      const id = crypto.randomUUID()
      const previewUrl = URL.createObjectURL(file)
      setImages(prev => [...prev, { id, file, previewUrl, path: null, uploading: true, error: null }])
      try {
        const { path } = await uploadReferenceImage(file)
        setImages(prev => prev.map(img => img.id === id ? { ...img, path, uploading: false } : img))
      } catch (e) {
        const message = e instanceof Error ? e.message : 'Upload failed'
        setImages(prev => prev.map(img => img.id === id ? { ...img, uploading: false, error: message } : img))
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const removeImage = (id: string) => {
    setImages(prev => {
      const target = prev.find(img => img.id === id)
      if (target) URL.revokeObjectURL(target.previewUrl)
      return prev.filter(img => img.id !== id)
    })
  }

  const anyUploading = images.some(img => img.uploading)

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

      {/* Reference images */}
      <div>
        <label className="section-label">Reference Images</label>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          multiple
          onChange={e => handleFiles(e.target.files)}
          disabled={isRunning}
          style={{ display: 'none' }}
          id="ref-image-input"
        />
        <label
          htmlFor="ref-image-input"
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            padding: '12px', borderRadius: 10, fontSize: 12, fontWeight: 600,
            border: '1px dashed rgba(220,20,60,0.35)', color: 'rgba(255,255,255,0.55)',
            cursor: isRunning ? 'not-allowed' : 'pointer', opacity: isRunning ? 0.4 : 1,
          }}
        >
          Click to upload screenshot(s) — PNG/JPEG/WebP, max 8MB
        </label>

        {images.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
            {images.map(img => (
              <div key={img.id} style={{ position: 'relative', width: 64, height: 64 }}>
                <img
                  src={img.previewUrl}
                  alt="reference"
                  style={{
                    width: 64, height: 64, objectFit: 'cover', borderRadius: 8,
                    border: img.error ? '1px solid #DC143C' : '1px solid rgba(255,255,255,0.12)',
                    opacity: img.uploading ? 0.4 : 1,
                  }}
                />
                {img.uploading && (
                  <span style={{
                    position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10, color: '#fff',
                  }}>…</span>
                )}
                <button
                  onClick={() => removeImage(img.id)}
                  title={img.error || 'Remove'}
                  style={{
                    position: 'absolute', top: -6, right: -6, width: 18, height: 18, borderRadius: '50%',
                    background: '#DC143C', color: '#fff', border: 'none', cursor: 'pointer',
                    fontSize: 12, lineHeight: 1, fontWeight: 900,
                  }}
                >×</button>
              </div>
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
          reference_image_paths: images.map(img => img.path).filter((p): p is string => !!p),
          pages_requested:       pages.split(',').map(p => p.trim()).filter(Boolean),
          max_iterations:        maxIter,
        })}
        disabled={isRunning || !req.trim() || anyUploading}
        className={!isRunning && req.trim() && !anyUploading ? 'glow-pulse' : ''}
        style={{
          width: '100%', padding: '13px 0', borderRadius: 12,
          fontWeight: 800, fontSize: 14, color: '#fff', border: 'none', cursor: 'pointer',
          background:
            isRunning || !req.trim() || anyUploading
              ? 'rgba(255,255,255,0.06)'
              : 'linear-gradient(135deg, #DC143C 0%, #a50e2b 100%)',
          opacity: isRunning || !req.trim() || anyUploading ? 0.45 : 1,
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
          : anyUploading ? 'Uploading images...' : 'Generate Website'
        }
        <style suppressHydrationWarning>{`@keyframes spin-q{to{transform:rotate(360deg)}}`}</style>
      </button>
    </div>
  )
}
