// frontend/src/App.tsx
import { useState, useEffect, useRef } from 'react'
import { UploadZone } from './components/UploadZone'
import { OrientationPicker } from './components/OrientationPicker'
import { StylePanel } from './components/StylePanel'
import { IdleOutput } from './components/IdleOutput'
import { LoadingOutput } from './components/LoadingOutput'
import { VideoOutput } from './components/VideoOutput'
import { getPreviewImages, createJob, getJobStatus, approvePhase4 } from './api/client'
import type { JobStatus, FaceName, PreviewResult } from './api/client'

type AppState = 'idle' | 'uploading' | 'orientation' | 'processing' | 'awaiting_approval' | 'styling' | 'done' | 'error'

export interface StyleOptions {
  studioLighting: boolean
  darkBackdrop: boolean
  whiteBackdrop: boolean
  warmTone: boolean
  coldTone: boolean
  groundShadow: boolean
  materialPrompt: string
  prompt: string
}



const DEFAULT_STYLE: StyleOptions = {
  studioLighting: true,
  darkBackdrop: false,
  whiteBackdrop: false,
  warmTone: false,
  coldTone: false,
  groundShadow: true,
  materialPrompt: '',
  prompt: '',
}

export default function App() {
  const [state, setState] = useState<AppState>('idle')
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [preview, setPreview] = useState<PreviewResult | null>(null)
  const [selectedFace, setSelectedFace] = useState<FaceName>('front')
  const [rotationDeg, setRotationDeg] = useState(0)
  const [orbitRangeDeg, setOrbitRangeDeg] = useState(40)
  const [explodeScalar, setExplodeScalar] = useState(1.5)
  const [styleOptions, setStyleOptions] = useState<StyleOptions>(DEFAULT_STYLE)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function handleUpload(file: File) {
    setErrorMsg(null)
    try {
      setState('uploading')
      const result = await getPreviewImages(file)
      setPreview(result)
      setSelectedFace('front')
      setState('orientation')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Preview failed')
      setState('error')
    }
  }

  async function handleLoadSample() {
    setErrorMsg(null)
    try {
      setState('uploading')
      const resp = await fetch('/preview/sample')
      if (!resp.ok) throw new Error(`Sample load failed: ${resp.statusText}`)
      const result: PreviewResult = await resp.json()
      setPreview(result)
      setSelectedFace('front')
      setState('orientation')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Sample load failed')
      setState('error')
    }
  }

  async function handleGenerate() {
    if (!preview) return
    setErrorMsg(null)
    try {
      setState('processing')
      const id = await createJob({
        previewId: preview.preview_id,
        explodeScalar,
        materialPrompt: styleOptions.materialPrompt,
        stylePrompt: styleOptions.prompt,
        studioLighting: styleOptions.studioLighting,
        darkBackdrop: styleOptions.darkBackdrop,
        whiteBackdrop: styleOptions.whiteBackdrop,
        warmTone: styleOptions.warmTone,
        coldTone: styleOptions.coldTone,
        groundShadow: styleOptions.groundShadow,
        masterAngle: selectedFace,
        rotationOffsetDeg: rotationDeg,
        orbitRangeDeg,
      })
      setJobId(id)
      setJobStatus(null)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Job creation failed')
      setState('error')
    }
  }

  useEffect(() => {
    const shouldPoll = state === 'processing' || state === 'styling'
    if (!shouldPoll || !jobId) return

    pollRef.current = setInterval(async () => {
      try {
        const status = await getJobStatus(jobId)
        setJobStatus(status)
        if (status.status === 'awaiting_approval') {
          setState('awaiting_approval')
          clearInterval(pollRef.current!)
        } else if (status.status === 'done') {
          setState('done')
          clearInterval(pollRef.current!)
        } else if (status.status === 'error') {
          setErrorMsg(status.error ?? 'Pipeline error')
          setState('error')
          clearInterval(pollRef.current!)
        }
      } catch {
        // keep polling on transient network errors
      }
    }, 2000)

    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [state, jobId])

  async function handleApprove() {
    if (!jobId) return
    try {
      await approvePhase4(jobId)
      setState('styling')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Approval failed')
      setState('error')
    }
  }

  function reset() {
    setState('idle')
    setJobId(null)
    setJobStatus(null)
    setPreview(null)
    setSelectedFace('front')
    setRotationDeg(0)
    setOrbitRangeDeg(40)
    setExplodeScalar(1.5)
    setStyleOptions(DEFAULT_STYLE)
    setErrorMsg(null)
  }

  const showControls = state === 'orientation' || state === 'processing' || state === 'awaiting_approval' || state === 'styling' || state === 'done'
  const controlsDisabled = state !== 'orientation'

  return (
    <div className="app-layout">

      {/* ─── Left panel ─── */}
      <aside className="left-panel">
        <header className="brand-header">
          <span className="wordmark">EXPLOD<em>I</em>FY</span>
          <span className="tagline">CAD → Exploded View</span>
        </header>

        <div className="left-scroll">

          {(state === 'idle' || state === 'uploading') && (
            <section className="panel-section animate-fade-in">
              <div className="section-label">Input File</div>
              <UploadZone
                onUpload={handleUpload}
                onLoadSample={handleLoadSample}
                loading={state === 'uploading'}
              />
            </section>
          )}

          {showControls && (
            <>
              <section className="panel-section animate-fade-in" style={{ paddingBottom: 14 }}>
                <button className="reupload-btn" onClick={reset}>
                  ↑&nbsp;&nbsp;Upload different file
                </button>
              </section>

              <section className="panel-section animate-fade-in">
                <div className="section-label">Style &amp; Parameters</div>
                <StylePanel
                  options={styleOptions}
                  onOptionsChange={setStyleOptions}
                  explodeScalar={explodeScalar}
                  onExplodeChange={setExplodeScalar}
                  orbitRangeDeg={orbitRangeDeg}
                  onOrbitRangeChange={setOrbitRangeDeg}
                  disabled={controlsDisabled}
                />
              </section>

              {state === 'orientation' && (
                <section className="panel-section animate-fade-in">
                  <button className="generate-btn" onClick={handleGenerate}>
                    Generate Explosion
                    <span className="generate-arrow">→</span>
                  </button>
                </section>
              )}

              {state === 'processing' && (
                <section className="panel-section animate-fade-in">
                  <div className="processing-indicator">
                    <div className="processing-dot" />
                    Rendering pipeline...
                  </div>
                </section>
              )}

              {state === 'awaiting_approval' && (
                <section className="panel-section animate-fade-in">
                  <div className="done-indicator">
                    <span>✓</span>
                    Base video ready
                  </div>
                </section>
              )}

              {state === 'styling' && (
                <section className="panel-section animate-fade-in">
                  <div className="processing-indicator">
                    <div className="processing-dot" />
                    Kling AI styling...
                  </div>
                </section>
              )}

              {state === 'done' && (
                <section className="panel-section animate-fade-in">
                  <div className="done-indicator">
                    <span>✓</span>
                    Styled video ready
                  </div>
                  <button className="reupload-btn" onClick={reset}>
                    ↺&nbsp;&nbsp;Start over with new file
                  </button>
                </section>
              )}
            </>
          )}

          {state === 'error' && (
            <section className="panel-section animate-fade-in">
              <div className="error-box">
                <span className="error-label">Error</span>
                <p className="error-msg">{errorMsg ?? 'Something went wrong'}</p>
                <button className="error-retry" onClick={reset}>Try again</button>
              </div>
            </section>
          )}

        </div>
      </aside>

      {/* ─── Right panel ─── */}
      <main className="right-panel">
        {state === 'idle' && <IdleOutput />}

        {state === 'uploading' && (
          <LoadingOutput phase="orientation" jobStatus={null} />
        )}

        {state === 'orientation' && preview && (
          <OrientationPreview
            imageSrc={preview.images[selectedFace]}
            faceName={selectedFace}
            selectedFace={selectedFace}
            onFaceChange={(face) => { setSelectedFace(face); setRotationDeg(0) }}
            rotationDeg={rotationDeg}
            onRotationChange={setRotationDeg}
          />
        )}

        {state === 'processing' && (
          <LoadingOutput phase="pipeline" jobStatus={jobStatus} />
        )}

        {state === 'awaiting_approval' && jobId && (
          <ApprovalGate jobId={jobId} onApprove={handleApprove} onSkip={reset} />
        )}

        {state === 'styling' && (
          <LoadingOutput phase="styling" jobStatus={jobStatus} />
        )}

        {state === 'done' && jobId && (
          <VideoOutput jobId={jobId} />
        )}

        {state === 'error' && (
          <div className="output-error-panel animate-fade-in">
            No output — see error on left
          </div>
        )}
      </main>
    </div>
  )
}

/* Inline component — Phase 4 cinematic review gate */
function ApprovalGate({
  jobId,
  onApprove,
  onSkip,
}: {
  jobId: string
  onApprove: () => void
  onSkip: () => void
}) {
  return (
    <div className="review-gate animate-fade-in">

      {/* Film-grade header bar */}
      <div className="review-header">
        <div className="review-header-left">
          <span className="review-tag">REVIEW</span>
          <span className="review-phase">PHASE 3 COMPLETE</span>
        </div>
        <div className="review-header-right">
          <span className="review-meta-item">72 FRAMES</span>
          <span className="review-meta-sep">·</span>
          <span className="review-meta-item">3S @ 24FPS</span>
          <span className="review-meta-sep">·</span>
          <span className="review-meta-item">1920×1080</span>
          <span className="review-meta-sep">·</span>
          <span className="review-meta-item review-meta-unstyled">UNSTYLED RENDER</span>
        </div>
      </div>

      {/* Video — dominant, plain player */}
      <div className="review-video-stage">
        <video
          src={`/jobs/${jobId}/base_video`}
          controls
          autoPlay
          loop
          playsInline
          className="review-video"
        />
      </div>

      {/* Action row */}
      <div className="review-actions">
        <div className="review-actions-left">
          <button className="review-proceed-btn" onClick={onApprove}>
            <span className="review-proceed-label">Proceed to AI Styling</span>
            <span className="review-proceed-arrow">→</span>
          </button>
          <button className="review-redo-btn" onClick={onSkip}>
            ↺ Redo / Change Settings
          </button>
        </div>
        <div className="review-actions-ticker">
          <span className="review-ticker-dot" />
          <span>~3 MIN &nbsp;·&nbsp; KLING O1 EDIT &nbsp;·&nbsp; FAL CREDITS CONSUMED</span>
        </div>
      </div>

    </div>
  )
}

/* Inline component — face preview + orientation/rotation controls on right panel */
function OrientationPreview({
  imageSrc,
  faceName,
  selectedFace,
  onFaceChange,
  rotationDeg,
  onRotationChange,
}: {
  imageSrc: string
  faceName: string
  selectedFace: FaceName
  onFaceChange: (face: FaceName) => void
  rotationDeg: number
  onRotationChange: (deg: number) => void
}) {
  return (
    <div className="orient-preview-panel animate-fade-in">
      <div className="orient-preview-label">{faceName} view</div>
      <div className="orient-preview-frame">
        <img
          src={imageSrc}
          alt={`${faceName} orientation preview`}
          className="orient-preview-img"
          style={{ transform: `rotate(${rotationDeg}deg)` }}
          draggable={false}
        />
      </div>

      <div className="orient-controls">
        <OrientationPicker
          selectedFace={selectedFace}
          onFaceChange={onFaceChange}
        />

        <div className="orient-rotation-slider">
          <div className="slider-header">
            <span className="slider-label">Rotation</span>
            <span className="slider-value">{rotationDeg}°</span>
          </div>
          <input
            type="range"
            min={0}
            max={350}
            step={5}
            value={rotationDeg}
            onChange={(e) => onRotationChange(parseInt(e.target.value))}
          />
        </div>
      </div>
    </div>
  )
}
