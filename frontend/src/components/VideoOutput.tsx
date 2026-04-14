// frontend/src/components/VideoOutput.tsx
import { useState } from 'react'
import type { VariantName } from '../api/client'
import type { StyleOptions, RestyleEntry } from '../App'
import { StylePanel } from './StylePanel'

interface Props {
  jobId: string
  aiStyled: boolean
  selectedVariants: VariantName[]
  styleOptions: StyleOptions
  restyleStack: RestyleEntry[]
  onRestyle: (opts: StyleOptions, variants: VariantName[]) => void
}

const VARIANT_LABELS: Record<VariantName, string> = {
  longest: 'LONGEST AXIS',
  shortest: 'SHORTEST AXIS',
}

// ─── Shared video player ──────────────────────────────────────────────────────

function VideoPlayer({
  jobId,
  variant,
  downloadName,
}: {
  jobId: string
  variant: VariantName
  downloadName: string
}) {
  const [showLoop, setShowLoop] = useState(false)
  const videoUrl = `/jobs/${jobId}/video/${variant}`
  const loopUrl = `/jobs/${jobId}/loop_video/${variant}`
  const src = showLoop ? loopUrl : videoUrl

  return (
    <div className="video-variant-card">
      <div className="video-variant-header">
        <span className="video-variant-label">{VARIANT_LABELS[variant]}</span>
        <div className="video-variant-controls">
          <button className="video-loop-toggle" onClick={() => setShowLoop(v => !v)}>
            {showLoop ? 'One-shot' : 'Loop'}
          </button>
          <a className="video-dl-btn" href={src} download={downloadName}>
            ↓ Download
          </a>
        </div>
      </div>
      <div className="video-hero-stage">
        <video
          src={src}
          controls
          autoPlay
          loop
          muted
          playsInline
          className="video-hero-player"
        />
      </div>
    </div>
  )
}

// ─── Skeleton card (generating) ───────────────────────────────────────────────

function SkeletonCard({ entry, generation }: { entry: RestyleEntry; generation: number }) {
  return (
    <div className="video-stack-card video-stack-card--generating">
      <div className="stack-card-header">
        <div className="stack-card-header-left">
          <span className="stack-gen-badge">GEN {generation}</span>
          <span className="stack-gen-status">
            <span className="stack-gen-dot" />
            GENERATING
          </span>
        </div>
      </div>
      <div className={entry.variants.length === 1 ? 'video-single-layout' : 'video-dual-layout'}>
        {entry.variants.map(v => (
          <div key={v} className="video-variant-card">
            <div className="video-variant-header">
              <span className="video-variant-label">{VARIANT_LABELS[v]}</span>
            </div>
            <div className="video-skeleton-stage">
              <div className="video-skeleton" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Restyle done card ────────────────────────────────────────────────────────

function RestyleCard({ entry, generation }: { entry: RestyleEntry; generation: number }) {
  if (entry.status === 'generating') {
    return <SkeletonCard entry={entry} generation={generation} />
  }

  if (entry.status === 'error') {
    return (
      <div className="video-stack-card video-stack-card--error">
        <div className="stack-card-header">
          <div className="stack-card-header-left">
            <span className="stack-gen-badge">GEN {generation}</span>
            <span className="stack-error-label">FAILED</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="video-stack-card video-stack-card--done animate-fade-in">
      <div className="stack-card-header">
        <div className="stack-card-header-left">
          <span className="stack-gen-badge">GEN {generation}</span>
          <span className="stack-done-badge">RE-STYLED</span>
        </div>
      </div>
      <div className={entry.variants.length === 1 ? 'video-single-layout' : 'video-dual-layout'}>
        {entry.variants.map(v => (
          <VideoPlayer
            key={v}
            jobId={entry.jobId}
            variant={v}
            downloadName={`explodify_gen${generation}_${v}_${entry.jobId}.mp4`}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Restyle drawer ───────────────────────────────────────────────────────────

function RestyleDrawer({
  styleOptions,
  selectedVariants,
  onSubmit,
  onCancel,
}: {
  styleOptions: StyleOptions
  selectedVariants: VariantName[]
  onSubmit: (opts: StyleOptions, variants: VariantName[]) => void
  onCancel: () => void
}) {
  const [localOpts, setLocalOpts] = useState<StyleOptions>(styleOptions)
  const [chosenVariants, setChosenVariants] = useState<Set<VariantName>>(new Set(selectedVariants))

  function toggleVariant(v: VariantName) {
    setChosenVariants(prev => {
      const next = new Set(prev)
      if (next.has(v)) {
        if (next.size > 1) next.delete(v)
      } else {
        next.add(v)
      }
      return next
    })
  }

  return (
    <div className="restyle-drawer animate-fade-in">
      <div className="restyle-drawer-inner">
        <StylePanel
          options={localOpts}
          onOptionsChange={setLocalOpts}
          disabled={false}
        />

        {selectedVariants.length > 1 && (
          <div className="restyle-variant-row">
            <span className="restyle-variant-label">Variants</span>
            <div className="restyle-variant-toggles">
              {selectedVariants.map(v => (
                <button
                  key={v}
                  className={[
                    'restyle-variant-btn',
                    chosenVariants.has(v) ? 'restyle-variant-btn--active' : '',
                  ].filter(Boolean).join(' ')}
                  onClick={() => toggleVariant(v)}
                >
                  {v === 'longest' ? 'Longest' : 'Shortest'}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="restyle-drawer-footer">
          <button className="restyle-cancel-btn" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="restyle-submit-btn"
            onClick={() => onSubmit(localOpts, [...chosenVariants])}
          >
            Generate Re-style
            <span className="restyle-submit-arrow">→</span>
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Root export ─────────────────────────────────────────────────────────────

export function VideoOutput({
  jobId,
  aiStyled,
  selectedVariants,
  styleOptions,
  restyleStack,
  onRestyle,
}: Props) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const hasGenerating = restyleStack.some(e => e.status === 'generating')
  const totalGens = restyleStack.length + 1

  function handleSubmit(opts: StyleOptions, variants: VariantName[]) {
    setDrawerOpen(false)
    onRestyle(opts, variants)
  }

  const originalBadge = aiStyled ? 'FINAL OUTPUT' : 'UNSTYLED OUTPUT'
  const originalLabel = aiStyled ? 'AI STYLED VIDEO' : 'BASE RENDER'
  const hasRestyles = restyleStack.length > 0

  return (
    <div className="video-output-section animate-fade-in">

      {/* Generation stack — newest first */}
      {restyleStack.map((entry, idx) => (
        <RestyleCard
          key={entry.jobId}
          entry={entry}
          generation={totalGens - idx}
        />
      ))}

      {/* Original / GEN 1 */}
      <div className={`video-stack-card ${hasRestyles ? 'video-stack-card--original' : 'video-stack-card--solo'}`}>
        <div className={hasRestyles ? 'stack-card-header' : 'video-hero-header'}>
          <div className={hasRestyles ? 'stack-card-header-left' : 'video-hero-title-row'}>
            {hasRestyles
              ? <span className="stack-gen-badge">GEN 1</span>
              : null}
            <span className={hasRestyles ? 'stack-original-badge' : 'video-hero-badge'}>
              {originalBadge}
            </span>
            {!hasRestyles && (
              <span className="video-hero-title">{originalLabel}</span>
            )}
          </div>
        </div>
        <div className={selectedVariants.length === 1 ? 'video-single-layout' : 'video-dual-layout'}>
          {selectedVariants.map(v => (
            <VideoPlayer
              key={v}
              jobId={jobId}
              variant={v}
              downloadName={`explodify_${v}_${aiStyled ? 'styled' : 'base'}_${jobId}.mp4`}
            />
          ))}
        </div>
      </div>

      {/* Re-style controls */}
      <div className="restyle-controls">
        {!drawerOpen ? (
          <button
            className="restyle-toggle-btn"
            onClick={() => setDrawerOpen(true)}
            disabled={hasGenerating}
          >
            <span className="restyle-toggle-icon">↻</span>
            {hasGenerating ? 'Generating...' : 'Re-style'}
          </button>
        ) : (
          <RestyleDrawer
            styleOptions={styleOptions}
            selectedVariants={selectedVariants}
            onSubmit={handleSubmit}
            onCancel={() => setDrawerOpen(false)}
          />
        )}
      </div>

    </div>
  )
}
