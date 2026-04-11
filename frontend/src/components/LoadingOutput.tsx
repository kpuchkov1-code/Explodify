// frontend/src/components/LoadingOutput.tsx
import { useState, useEffect, useRef } from 'react'
import type { JobStatus } from '../api/client'

interface Props {
  phase: 'orientation' | 'pipeline' | 'styling'
  jobStatus: JobStatus | null
}

const ORIENTATION_PHRASES = [
  'Computing orientation views...',
  'Analyzing mesh geometry...',
  'Mapping cube faces...',
  'Casting geometry rays...',
  'Building face previews...',
]

const PIPELINE_PHRASES = [
  'Analyzing mesh geometry...',
  'Computing explosion vectors...',
  'Casting geometry rays...',
  'Tracing optimal view angles...',
  'Composing reference frames...',
  'Rendering keyframes...',
  'Building exploded assembly...',
  'Calibrating camera paths...',
  'Computing part displacements...',
  'Finalizing render pass...',
]

const PIPELINE_PHASES = [
  { id: 1, name: 'Geometry',  detail: 'Explosion vectors' },
  { id: 2, name: 'Render',    detail: '72 frames at 1920×1080' },
  { id: 3, name: 'Assembly',  detail: 'ffmpeg → mp4' },
]

const STYLING_STAGES = [
  { key: 'upload',   label: 'UPLOAD',   sub: 'Sending to fal.ai' },
  { key: 'process',  label: 'PROCESS',  sub: 'Kling o1 applying style' },
  { key: 'download', label: 'DOWNLOAD', sub: 'Retrieving styled video' },
]

function computeProgress(jobStatus: JobStatus | null): number {
  if (!jobStatus) return 5
  const p = jobStatus.phases
  if (p[3] === 'done') return 100
  if (p[3] === 'running') return 78
  if (p[2] === 'done') return 65
  if (p[2] === 'running') return 30
  if (p[1] === 'done') return 22
  if (p[1] === 'running') return 8
  return 5
}

function getPhaseDisplayName(jobStatus: JobStatus | null): string {
  if (!jobStatus) return 'INITIALISING'
  return jobStatus.current_phase_name?.toUpperCase() ?? 'PROCESSING'
}

function getPhaseDetail(jobStatus: JobStatus | null): string {
  if (!jobStatus) return 'Starting pipeline...'
  const phase = PIPELINE_PHASES.find(p => p.id === jobStatus.current_phase)
  return phase?.detail ?? ''
}

function useStylingStage(active: boolean): string {
  const [stage, setStage] = useState('upload')
  const elapsed = useRef(0)

  useEffect(() => {
    if (!active) return
    const tick = setInterval(() => {
      elapsed.current += 1
      // upload finishes ~15s, process runs until ~160s, then download
      if (elapsed.current < 15) setStage('upload')
      else if (elapsed.current < 160) setStage('process')
      else setStage('download')
    }, 1000)
    return () => clearInterval(tick)
  }, [active])

  return stage
}

function useElapsedTime(active: boolean): string {
  const [secs, setSecs] = useState(0)
  useEffect(() => {
    if (!active) return
    const t = setInterval(() => setSecs(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [active])
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

// ─── Styling-specific dramatic loader ────────────────────────────────────────
function StylingLoader() {
  const stage = useStylingStage(true)
  const elapsed = useElapsedTime(true)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 80)
    return () => clearInterval(t)
  }, [])

  const stageIdx = STYLING_STAGES.findIndex(s => s.key === stage)
  const currentStage = STYLING_STAGES[stageIdx]

  return (
    <div className="styling-loader animate-fade-in">
      {/* Ambient dot-grid background */}
      <div className="styling-grid-bg" />

      {/* Top bar */}
      <div className="styling-topbar">
        <div className="styling-topbar-left">
          <span className="styling-topbar-dot" />
          <span className="styling-topbar-label">KLING O1 · FAL.AI</span>
        </div>
        <div className="styling-topbar-right">
          <span className="styling-elapsed">{elapsed}</span>
          <span className="styling-topbar-label">/ ~3:00</span>
        </div>
      </div>

      {/* Central content */}
      <div className="styling-center">
        <div className="styling-phase-name">
          AI&nbsp;STYLING
        </div>
        <div className="styling-current-op">
          {currentStage?.sub}
        </div>

        {/* Oscilloscope-style waveform */}
        <div className="styling-wave">
          {Array.from({ length: 40 }, (_, i) => {
            const phase = (i / 40) * Math.PI * 4 + tick * 0.18
            const h = Math.abs(Math.sin(phase) * 36) + 4
            return (
              <div
                key={i}
                className="styling-wave-bar"
                style={{
                  height: `${h}px`,
                  opacity: 0.3 + (h / 40) * 0.7,
                }}
              />
            )
          })}
        </div>
      </div>

      {/* Stage tracker */}
      <div className="styling-stages">
        {STYLING_STAGES.map((s, idx) => {
          const isDone = idx < stageIdx
          const isActive = idx === stageIdx
          return (
            <div key={s.key} className="styling-stage-item">
              {idx > 0 && (
                <div className={`styling-stage-line ${isDone || isActive ? 'styling-stage-line--lit' : ''}`} />
              )}
              <div className={`styling-stage-node ${isActive ? 'styling-stage-node--active' : ''} ${isDone ? 'styling-stage-node--done' : ''}`}>
                {isDone ? '✓' : isActive ? <span className="styling-node-pulse" /> : idx + 1}
              </div>
              <div className="styling-stage-label-wrap">
                <span className={`styling-stage-label ${isActive ? 'styling-stage-label--active' : ''} ${isDone ? 'styling-stage-label--done' : ''}`}>
                  {s.label}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Bottom warning */}
      <div className="styling-footer">
        Do not close this window &nbsp;·&nbsp; FAL credits are being consumed
      </div>
    </div>
  )
}

// ─── Standard pipeline/orientation loader ─────────────────────────────────
function StandardLoader({ phase, jobStatus }: { phase: 'orientation' | 'pipeline', jobStatus: JobStatus | null }) {
  const phrases = phase === 'orientation' ? ORIENTATION_PHRASES : PIPELINE_PHRASES
  const [phraseIndex, setPhraseIndex] = useState(0)
  const [fading, setFading] = useState(false)

  useEffect(() => {
    const timer = setInterval(() => {
      setFading(true)
      setTimeout(() => {
        setPhraseIndex(i => (i + 1) % phrases.length)
        setFading(false)
      }, 350)
    }, 2600)
    return () => clearInterval(timer)
  }, [phrases.length])

  const progress = phase === 'orientation' ? 20 : computeProgress(jobStatus)
  const displayName = phase === 'orientation' ? 'ORIENTATION' : getPhaseDisplayName(jobStatus)
  const displayDetail = phase === 'orientation' ? 'Computing 6 face previews' : getPhaseDetail(jobStatus)

  return (
    <div className="loading-output animate-fade-in">
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="loading-body">
        <div className="loading-phase-display">
          <div className="loading-phase-name">{displayName}</div>
          {displayDetail && (
            <div className="loading-phase-detail">{displayDetail}</div>
          )}
        </div>

        <div className="loading-bars">
          {Array.from({ length: 15 }, (_, i) => (
            <div
              key={i}
              className="loading-bar"
              style={{ animationDelay: `${i * 0.08}s` }}
            />
          ))}
        </div>

        <div className={['loading-cycling-text', fading ? 'loading-cycling-text--fading' : ''].join(' ')}>
          {phrases[phraseIndex]}
        </div>

        {phase === 'pipeline' && (
          <div className="loading-phases-row">
            {PIPELINE_PHASES.map((p, idx) => {
              const status = jobStatus?.phases[p.id] ?? 'pending'
              const isActive = status === 'running'
              const isDone = status === 'done'
              return (
                <div key={p.id} style={{ display: 'flex', alignItems: 'center' }}>
                  <div className={['phase-step', isActive ? 'phase-step--active' : '', isDone ? 'phase-step--done' : ''].join(' ')}>
                    <div className="phase-step-dot" />
                    <span className="phase-step-label">{p.name}</span>
                  </div>
                  {idx < PIPELINE_PHASES.length - 1 && <div className="phase-connector" />}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export function LoadingOutput({ phase, jobStatus }: Props) {
  if (phase === 'styling') return <StylingLoader />
  return <StandardLoader phase={phase} jobStatus={jobStatus} />
}
