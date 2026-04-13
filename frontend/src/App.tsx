// frontend/src/App.tsx
import { useState, useEffect, useRef } from 'react'
import { UploadZone } from './components/UploadZone'
import { OrientationPicker } from './components/OrientationPicker'
import { StylePanel } from './components/StylePanel'
import { IdleOutput } from './components/IdleOutput'
import { LoadingOutput } from './components/LoadingOutput'
import { VideoOutput } from './components/VideoOutput'
import { getPreviewImages, createJob, getJobStatus, approvePhase4 } from './api/client'
import type { JobStatus, FaceName, PreviewResult, VariantName } from './api/client'

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
  componentMaterials: Record<string, string>
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
  componentMaterials: {},
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
  const [cameraZoom, setCameraZoom] = useState(1.0)
  const [styleOptions, setStyleOptions] = useState<StyleOptions>(DEFAULT_STYLE)
  const [componentNames, setComponentNames] = useState<string[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [selectedVariants, setSelectedVariants] = useState<Set<VariantName>>(new Set(['longest', 'shortest']))
  const [approvalSelected, setApprovalSelected] = useState<Set<VariantName>>(new Set(['longest', 'shortest']))
  const [renderedSettings, setRenderedSettings] = useState<{ explodeScalar: number; orbitRangeDeg: number; cameraZoom: number } | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const settingsChanged = renderedSettings !== null && (
    renderedSettings.explodeScalar !== explodeScalar ||
    renderedSettings.orbitRangeDeg !== orbitRangeDeg ||
    renderedSettings.cameraZoom !== cameraZoom
  )

  async function handleUpload(file: File) {
    setErrorMsg(null)
    try {
      setState('uploading')
      const result = await getPreviewImages(file)
      setPreview(result)
      setSelectedFace('front')
      setComponentNames(result.component_names ?? [])
      setState('orientation')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Preview failed')
      setState('error')
    }
  }

  async function handleGenerate(variantsToRender?: VariantName[]) {
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
        cameraZoom,
        variantsToRender,
        componentMaterials: styleOptions.componentMaterials,
      })
      setJobId(id)
      setJobStatus(null)
      setRenderedSettings({ explodeScalar, orbitRangeDeg, cameraZoom })
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

  async function handleApprove(variants: VariantName[]) {
    if (!jobId) return
    try {
      await approvePhase4(jobId, variants, {
        materialPrompt: styleOptions.materialPrompt,
        stylePrompt: styleOptions.prompt,
        studioLighting: styleOptions.studioLighting,
        darkBackdrop: styleOptions.darkBackdrop,
        whiteBackdrop: styleOptions.whiteBackdrop,
        warmTone: styleOptions.warmTone,
        coldTone: styleOptions.coldTone,
        groundShadow: styleOptions.groundShadow,
      })
      setSelectedVariants(new Set(variants))
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
    setCameraZoom(1.0)
    setStyleOptions(DEFAULT_STYLE)
    setComponentNames([])
    setSelectedVariants(new Set(['longest', 'shortest']))
    setApprovalSelected(new Set(['longest', 'shortest']))
    setRenderedSettings(null)
    setErrorMsg(null)
  }

  const showControls = state === 'orientation' || state === 'processing' || state === 'awaiting_approval' || state === 'styling' || state === 'done'
  const controlsDisabled = state !== 'orientation' && state !== 'awaiting_approval'

  return (
    <div className="app-layout">

      {/* Left panel */}
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
                  componentNames={componentNames}
                  disabled={controlsDisabled}
                />
              </section>

              {state === 'orientation' && (
                <section className="panel-section animate-fade-in">
                  <button className="generate-btn" onClick={() => handleGenerate()}>
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
                  {settingsChanged ? (
                    <>
                      <div className="settings-changed-indicator">
                        Settings changed
                      </div>
                      <button className="generate-btn" onClick={() => handleGenerate([...approvalSelected])}>
                        Re-render {approvalSelected.size === 1 ? '1 video' : 'both'}
                        <span className="generate-arrow">→</span>
                      </button>
                    </>
                  ) : (
                    <div className="done-indicator">
                      <span>✓</span>
                      {approvalSelected.size === 1 ? '1 variant ready' : 'Both variants ready'}
                    </div>
                  )}
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
                    {jobStatus?.ai_styled ? 'Styled video ready' : 'Base render ready'}
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

      {/* Right panel */}
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
            cameraZoom={cameraZoom}
            onZoomChange={setCameraZoom}
          />
        )}

        {state === 'processing' && (
          <LoadingOutput phase="pipeline" jobStatus={jobStatus} />
        )}

        {state === 'awaiting_approval' && jobId && (
          <DualApprovalGate
            jobId={jobId}
            onApprove={handleApprove}
            onSkip={reset}
            selected={approvalSelected}
            onSelectionChange={setApprovalSelected}
          />
        )}

        {state === 'styling' && (
          <LoadingOutput phase="styling" jobStatus={jobStatus} />
        )}

        {state === 'done' && jobId && (
          <VideoOutput
            jobId={jobId}
            aiStyled={jobStatus?.ai_styled ?? false}
            selectedVariants={[...selectedVariants]}
          />
        )}

        {state === 'error' && (
          <div className="output-error-panel animate-fade-in">
            No output -- see error on left
          </div>
        )}
      </main>
    </div>
  )
}


/* Side-by-side dual variant approval gate */
function DualApprovalGate({
  jobId,
  onApprove,
  onSkip,
  selected,
  onSelectionChange,
}: {
  jobId: string
  onApprove: (variants: VariantName[]) => void
  onSkip: () => void
  selected: Set<VariantName>
  onSelectionChange: (s: Set<VariantName>) => void
}) {
  function toggleVariant(v: VariantName) {
    const next = new Set(selected)
    if (next.has(v)) {
      if (next.size > 1) next.delete(v)
    } else {
      next.add(v)
    }
    onSelectionChange(next)
  }

  const count = selected.size
  const isSingle = count === 1

  return (
    <div className="review-gate animate-fade-in">

      <div className="review-header">
        <div className="review-header-left">
          <span className="review-tag">REVIEW</span>
          <span className="review-phase">EXPLOSION VARIANTS</span>
        </div>
        <div className="review-header-right">
          <span className="review-meta-item">72 FRAMES EACH</span>
          <span className="review-meta-sep">·</span>
          <span className="review-meta-item">3S @ 24FPS</span>
          <span className="review-meta-sep">·</span>
          <span className="review-meta-item review-meta-unstyled">UNSTYLED RENDER</span>
        </div>
      </div>

      <div className={`variant-compare${isSingle ? ' variant-compare--single' : ''}`}>
        <VariantCard
          jobId={jobId}
          variant="longest"
          label="LONGEST AXIS"
          description="Explodes along the tallest dimension"
          selected={selected.has('longest')}
          collapsed={isSingle && !selected.has('longest')}
          onToggle={() => toggleVariant('longest')}
        />
        <VariantCard
          jobId={jobId}
          variant="shortest"
          label="SHORTEST AXIS"
          description="Explodes along the narrowest dimension"
          selected={selected.has('shortest')}
          collapsed={isSingle && !selected.has('shortest')}
          onToggle={() => toggleVariant('shortest')}
        />
      </div>

      <div className="review-actions">
        <div className="review-actions-left">
          <button
            className="review-proceed-btn"
            onClick={() => onApprove([...selected])}
          >
            <span className="review-proceed-label">
              Style {count === 2 ? 'Both' : '1'} Variant{count === 2 ? 's' : ''}
            </span>
            <span className="review-proceed-arrow">→</span>
          </button>
          <button className="review-redo-btn" onClick={onSkip}>
            ↺ Start Over
          </button>
        </div>
      </div>

    </div>
  )
}


function VariantCard({
  jobId,
  variant,
  label,
  description,
  selected,
  collapsed,
  onToggle,
}: {
  jobId: string
  variant: VariantName
  label: string
  description: string
  selected: boolean
  collapsed: boolean
  onToggle: () => void
}) {
  const classes = [
    'variant-card',
    selected ? 'variant-card--selected' : '',
    collapsed ? 'variant-card--collapsed' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={classes} onClick={onToggle}>
      <div className="variant-card-header">
        <div className="variant-checkbox">
          {selected && <span className="variant-check">✓</span>}
        </div>
        <div className="variant-label-group">
          <span className="variant-label">{label}</span>
          <span className="variant-desc">{description}</span>
        </div>
      </div>
      {!collapsed && (
        <div className="variant-video-stage">
          <video
            src={`/jobs/${jobId}/base_video/${variant}`}
            controls
            autoPlay
            loop
            muted
            playsInline
            className="variant-video"
          />
        </div>
      )}
    </div>
  )
}


/* Orientation preview with rotation slider */
function OrientationPreview({
  imageSrc,
  faceName,
  selectedFace,
  onFaceChange,
  rotationDeg,
  onRotationChange,
  cameraZoom,
  onZoomChange,
}: {
  imageSrc: string
  faceName: string
  selectedFace: FaceName
  onFaceChange: (face: FaceName) => void
  rotationDeg: number
  onRotationChange: (deg: number) => void
  cameraZoom: number
  onZoomChange: (z: number) => void
}) {
  return (
    <div className="orient-preview-panel animate-fade-in">
      <div className="orient-preview-frame">
        <div className="orient-face-badge">{faceName} view</div>
        <img
          src={imageSrc}
          alt={`${faceName} orientation preview`}
          className="orient-preview-img"
          style={{ transform: `rotate(${rotationDeg}deg) scale(${cameraZoom})` }}
          draggable={false}
        />

        <div className="orient-overlay-picker">
          <OrientationPicker
            selectedFace={selectedFace}
            onFaceChange={onFaceChange}
          />
        </div>

        <div className="orient-overlay-sliders">
          <div className="orient-slider-row">
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

          <div className="orient-slider-row">
            <div className="slider-header">
              <span className="slider-label">Zoom</span>
              <span className="slider-value">{cameraZoom.toFixed(1)}×</span>
            </div>
            <input
              type="range"
              min={0.5}
              max={2.0}
              step={0.1}
              value={cameraZoom}
              onChange={(e) => onZoomChange(parseFloat(e.target.value))}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
