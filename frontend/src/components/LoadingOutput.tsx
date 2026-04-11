// frontend/src/components/LoadingOutput.tsx
import { useState, useEffect } from 'react'
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

const STYLING_PHRASES = [
  'Uploading to fal.ai...',
  'Kling AI processing...',
  'Applying studio lighting...',
  'Rendering materials...',
  'Compositing environment...',
  'Finalizing styled output...',
  'AI upscaling video...',
  'Downloading result...',
]

const PIPELINE_PHASES = [
  { id: 1, name: 'Geometry',  detail: 'Ray-casting & explosion vectors' },
  { id: 2, name: 'Keyframes', detail: '5 PNG renders at 0–100% explosion' },
  { id: 3, name: 'AI Style',  detail: 'Gemini Flash photorealistic pass' },
  { id: 4, name: 'Video',     detail: 'fal.ai Kling animation synthesis' },
]

function computeProgress(jobStatus: JobStatus | null): number {
  if (!jobStatus) return 8
  const phases = jobStatus.phases
  if (phases[2] === 'done') return 100
  if (phases[2] === 'running') return 70
  if (phases[1] === 'done') return 45
  if (phases[1] === 'running') return 18
  return 8
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

export function LoadingOutput({ phase, jobStatus }: Props) {
  const phrases = phase === 'orientation'
    ? ORIENTATION_PHRASES
    : phase === 'styling'
      ? STYLING_PHRASES
      : PIPELINE_PHRASES
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

  const progress = phase === 'orientation' ? 20 : phase === 'styling' ? 60 : computeProgress(jobStatus)
  const displayName = phase === 'orientation' ? 'ORIENTATION' : phase === 'styling' ? 'KLING AI STYLING' : getPhaseDisplayName(jobStatus)
  const displayDetail = phase === 'orientation'
    ? 'Computing 6 face previews'
    : phase === 'styling'
      ? 'Applying studio lighting, materials & environment (~3 min)'
      : getPhaseDetail(jobStatus)

  return (
    <div className="loading-output animate-fade-in">
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="loading-body">

        {/* Phase name */}
        <div className="loading-phase-display">
          <div className="loading-phase-name">{displayName}</div>
          {displayDetail && (
            <div className="loading-phase-detail">{displayDetail}</div>
          )}
        </div>

        {/* Animated bars */}
        <div className="loading-bars">
          {Array.from({ length: 15 }, (_, i) => (
            <div
              key={i}
              className="loading-bar"
              style={{ animationDelay: `${i * 0.08}s` }}
            />
          ))}
        </div>

        {/* Cycling text */}
        <div className={[
          'loading-cycling-text',
          fading ? 'loading-cycling-text--fading' : '',
        ].join(' ')}>
          {phrases[phraseIndex]}
        </div>

        {/* Phase steps — only shown during pipeline or styling phase */}
        {(phase === 'pipeline' || phase === 'styling') && (
          <div className="loading-phases-row">
            {PIPELINE_PHASES.map((p, idx) => {
              const status = jobStatus?.phases[p.id] ?? 'pending'
              const isActive = status === 'running'
              const isDone = status === 'done'
              return (
                <div key={p.id} style={{ display: 'flex', alignItems: 'center' }}>
                  <div className={[
                    'phase-step',
                    isActive ? 'phase-step--active' : '',
                    isDone ? 'phase-step--done' : '',
                  ].join(' ')}>
                    <div className="phase-step-dot" />
                    <span className="phase-step-label">{p.name}</span>
                  </div>
                  {idx < PIPELINE_PHASES.length - 1 && (
                    <div className="phase-connector" />
                  )}
                </div>
              )
            })}
          </div>
        )}

      </div>
    </div>
  )
}
