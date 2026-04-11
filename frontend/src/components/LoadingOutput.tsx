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
  { id: 2, name: 'Render',    detail: '72 frames · 1920×1080' },
  { id: 3, name: 'Assembly',  detail: 'ffmpeg → mp4' },
]

const STYLING_STAGES = [
  { key: 'upload',   label: 'UPLOAD',   sub: 'Sending to fal.ai' },
  { key: 'process',  label: 'PROCESS',  sub: 'Kling o1 applying style' },
  { key: 'download', label: 'DOWNLOAD', sub: 'Retrieving styled video' },
]

const TOTAL_STYLING_SECS = 180

function computeProgress(jobStatus: JobStatus | null): number {
  // Front-loaded: jumps quickly early, slows later (feels faster)
  if (!jobStatus) return 12
  const p = jobStatus.phases
  if (p[3] === 'done') return 100
  if (p[3] === 'running') return 82
  if (p[2] === 'done') return 72
  if (p[2] === 'running') return 40
  if (p[1] === 'done') return 30
  if (p[1] === 'running') return 18
  return 12
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
      if (elapsed.current < 15) setStage('upload')
      else if (elapsed.current < 160) setStage('process')
      else setStage('download')
    }, 1000)
    return () => clearInterval(tick)
  }, [active])

  return stage
}

function useElapsedSeconds(active: boolean): number {
  const [secs, setSecs] = useState(0)
  useEffect(() => {
    if (!active) return
    const t = setInterval(() => setSecs(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [active])
  return secs
}

function formatTime(secs: number): string {
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

// ─── Styling-specific dramatic loader ────────────────────────────────────────
function StylingLoader() {
  const stage = useStylingStage(true)
  const elapsedSecs = useElapsedSeconds(true)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 45)
    return () => clearInterval(t)
  }, [])

  const stageIdx = STYLING_STAGES.findIndex(s => s.key === stage)
  const currentStage = STYLING_STAGES[stageIdx]

  // Logarithmic progress curve: jumps to ~40% quickly, then crawls.
  // Feels fast early on even though the total wait is ~3 min.
  const t = Math.min(elapsedSecs / TOTAL_STYLING_SECS, 1)
  const progressPct = Math.min(95, t < 0.15
    ? t * 300          // 0-45% in first 27s
    : 45 + (1 - Math.exp(-4 * (t - 0.15))) * 50  // 45-95% logarithmic
  )

  const isOverTime = elapsedSecs > TOTAL_STYLING_SECS

  return (
    <div className="sl-root animate-fade-in">
      {/* Scan-line texture */}
      <div className="sl-scanlines" />

      {/* Top progress bar — full width, prominent */}
      <div className="sl-progress-rail">
        <div className="sl-progress-fill" style={{ width: `${progressPct}%` }}>
          <div className="sl-progress-glow" />
        </div>
      </div>

      {/* Header bar */}
      <div className="sl-header">
        <div className="sl-header-left">
          <span className="sl-dot" />
          <span className="sl-label">KLING O1 &nbsp;·&nbsp; FAL.AI</span>
        </div>
        <div className="sl-header-right">
          <span className={`sl-timer ${isOverTime ? 'sl-timer--over' : ''}`}>
            {formatTime(elapsedSecs)}
          </span>
          <span className="sl-label sl-label--dim">/ ~3:00</span>
        </div>
      </div>

      {/* Central content */}
      <div className="sl-body">
        {/* Phase title */}
        <div className="sl-title">AI&nbsp;STYLING</div>
        <div className="sl-subtitle">{currentStage?.sub}</div>

        {/* Time warning */}
        <div className={`sl-time-warning ${isOverTime ? 'sl-time-warning--over' : ''}`}>
          {isOverTime
            ? 'Running longer than expected — please wait'
            : 'This may take 2–3 minutes · do not close this window'}
        </div>

        {/* Waveform visualiser */}
        <div className="sl-wave">
          {Array.from({ length: 48 }, (_, i) => {
            const a = (i / 48) * Math.PI * 6 + tick * 0.15
            const b = (i / 48) * Math.PI * 3 + tick * 0.09
            const h = Math.abs(Math.sin(a) * 28 + Math.sin(b) * 14) + 3
            return (
              <div
                key={i}
                className="sl-wave-bar"
                style={{ height: `${h}px`, opacity: 0.25 + (h / 42) * 0.75 }}
              />
            )
          })}
        </div>

        {/* Progress percentage readout */}
        <div className="sl-pct-row">
          <span className="sl-pct-value">{Math.round(progressPct)}</span>
          <span className="sl-pct-unit">%</span>
        </div>
      </div>

      {/* Stage tracker */}
      <div className="sl-stages">
        {STYLING_STAGES.map((s, idx) => {
          const isDone = idx < stageIdx
          const isActive = idx === stageIdx
          return (
            <div key={s.key} className="sl-stage-item">
              {idx > 0 && (
                <div className={`sl-stage-line ${isDone ? 'sl-stage-line--done' : isActive ? 'sl-stage-line--active' : ''}`} />
              )}
              <div className={`sl-stage-node ${isActive ? 'sl-stage-node--active' : ''} ${isDone ? 'sl-stage-node--done' : ''}`}>
                {isDone ? '✓' : isActive ? <span className="sl-node-pulse" /> : <span className="sl-node-num">{idx + 1}</span>}
              </div>
              <div className="sl-stage-meta">
                <span className={`sl-stage-name ${isActive ? 'sl-stage-name--active' : ''} ${isDone ? 'sl-stage-name--done' : ''}`}>
                  {s.label}
                </span>
                <span className="sl-stage-sub">{s.sub}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Footer */}
      <div className="sl-footer">
        <span className="sl-footer-dot" />
        FAL credits are being consumed &nbsp;·&nbsp; do not close this window
      </div>
    </div>
  )
}

// ─── Standard pipeline / orientation loader ───────────────────────────────────
function StandardLoader({ phase, jobStatus }: { phase: 'orientation' | 'pipeline', jobStatus: JobStatus | null }) {
  const phrases = phase === 'orientation' ? ORIENTATION_PHRASES : PIPELINE_PHRASES
  const [phraseIndex, setPhraseIndex] = useState(0)
  const [fading, setFading] = useState(false)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setFading(true)
      setTimeout(() => {
        setPhraseIndex(i => (i + 1) % phrases.length)
        setFading(false)
      }, 150)
    }, 1800)
    return () => clearInterval(timer)
  }, [phrases.length])

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 50)
    return () => clearInterval(t)
  }, [])

  const progress = phase === 'orientation' ? 18 : computeProgress(jobStatus)
  const displayName = phase === 'orientation' ? 'ORIENTATION' : getPhaseDisplayName(jobStatus)
  const displayDetail = phase === 'orientation' ? 'Computing 6 face previews' : getPhaseDetail(jobStatus)

  return (
    <div className="pl-root animate-fade-in">
      {/* Top progress bar */}
      <div className="pl-progress-rail">
        <div className="pl-progress-fill" style={{ width: `${progress}%` }}>
          <div className="pl-progress-glow" />
        </div>
        <span className="pl-progress-pct">{progress}%</span>
      </div>

      <div className="pl-body">
        {/* Phase name + detail */}
        <div className="pl-phase-block">
          <div className="pl-phase-name">{displayName}</div>
          {displayDetail && <div className="pl-phase-detail">{displayDetail}</div>}
        </div>

        {/* Animated waveform bars */}
        <div className="pl-wave">
          {Array.from({ length: 24 }, (_, i) => {
            const a = (i / 24) * Math.PI * 4 + tick * 0.14
            const h = Math.abs(Math.sin(a) * 22) + 4
            return (
              <div
                key={i}
                className="pl-wave-bar"
                style={{ height: `${h}px`, opacity: 0.2 + (h / 26) * 0.8 }}
              />
            )
          })}
        </div>

        {/* Cycling phrase */}
        <div className={`pl-phrase ${fading ? 'pl-phrase--fade' : ''}`}>
          {phrases[phraseIndex]}
        </div>

        {/* Phase tracker — only during pipeline */}
        {phase === 'pipeline' && (
          <div className="pl-phases">
            {PIPELINE_PHASES.map((p, idx) => {
              const status = jobStatus?.phases[p.id] ?? 'pending'
              const isActive = status === 'running'
              const isDone = status === 'done'
              return (
                <div key={p.id} className="pl-phase-row">
                  {idx > 0 && (
                    <div className={`pl-connector ${isDone || isActive ? 'pl-connector--lit' : ''}`} />
                  )}
                  <div className={`pl-phase-step ${isActive ? 'pl-phase-step--active' : ''} ${isDone ? 'pl-phase-step--done' : ''}`}>
                    <div className="pl-step-indicator">
                      {isDone
                        ? <span className="pl-step-check">✓</span>
                        : isActive
                          ? <span className="pl-step-pulse" />
                          : <span className="pl-step-num">{p.id}</span>
                      }
                    </div>
                    <div className="pl-step-text">
                      <span className="pl-step-name">{p.name}</span>
                      <span className="pl-step-detail">{p.detail}</span>
                    </div>
                  </div>
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
