// frontend/src/components/EasingEditor.tsx
import { useRef, useCallback, useEffect, useState } from 'react'

const T_STEPS = [0, 0.25, 0.5, 0.75, 1.0]

// ─── Presets ──────────────────────────────────────────────────────────────────
// Samples represent velocity (speed multiplier) at t=[0, 0.25, 0.5, 0.75, 1.0].
// Backend integrates these to derive actual position — preventing reversal.

interface Preset {
  id: string
  label: string
  samples: number[]
}

const PRESETS: Preset[] = [
  { id: 'linear',    label: 'Linear',    samples: [1.0,  1.0,  1.0,  1.0,  1.0]  },
  { id: 'cinematic', label: 'Cinematic', samples: [1.8,  1.4,  0.9,  0.4,  0.1]  },
  { id: 'snap',      label: 'Snap',      samples: [3.5,  1.8,  0.4,  0.05, 0.0]  },
  { id: 'ease-in',   label: 'Ease In',   samples: [0.1,  0.5,  1.0,  1.6,  2.2]  },
  { id: 'surge',     label: 'Surge',     samples: [0.8,  2.2,  1.8,  0.6,  0.05] },
]

export const DEFAULT_EQ_SAMPLES: number[] = [...PRESETS[0].samples]

// ─── SVG coordinate system ────────────────────────────────────────────────────

const VW    = 280
const VH    = 175
const PX    = 28    // left padding (y-label area)
const PY    = 10    // top padding
const PR    = 6     // right padding
const PW    = VW - PX - PR
const PH    = 120   // plot height
const XLY   = PY + PH + 16  // x-label y-position

// Y axis represents velocity (speed multiplier). Clamped to [0, Y_HI].
const Y_LO = 0
const Y_HI  = 4.0

function tToSX(t: number)  { return PX + t * PW }
function yToSY(y: number)  { return PY + (1 - (y - Y_LO) / (Y_HI - Y_LO)) * PH }
function sYToY(sy: number) { return Y_LO + (1 - (sy - PY) / PH) * (Y_HI - Y_LO) }

// ─── Catmull-Rom spline ───────────────────────────────────────────────────────

function catmullRomPath(pts: [number, number][]): string {
  if (pts.length < 2) return ''
  const segs = [`M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`]
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[Math.min(pts.length - 1, i + 2)]
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6
    segs.push(
      `C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`
    )
  }
  return segs.join(' ')
}

// ─── Preset matching ──────────────────────────────────────────────────────────

function matchPreset(samples: number[]): string | null {
  if (samples.length !== 5) return null
  return PRESETS.find(p =>
    p.samples.every((v, i) => Math.abs((samples[i] ?? 0) - v) < 0.005)
  )?.id ?? null
}

// ─── Constants ────────────────────────────────────────────────────────────────

const Y_REFS = [
  { y: 3.0, label: '3×' },
  { y: 1.5, label: '1.5×' },
  { y: 0,   label: '0'    },
]

const X_LABELS = ['Start', '25%', 'Mid', '75%', 'End']

// ─── Props ────────────────────────────────────────────────────────────────────

interface Props {
  value: number[]
  onChange: (samples: number[]) => void
  disabled?: boolean
}

// ─── Component ────────────────────────────────────────────────────────────────

export function EasingEditor({ value, onChange, disabled }: Props) {
  const samples       = value.length === 5 ? value : DEFAULT_EQ_SAMPLES
  const svgRef        = useRef<SVGSVGElement>(null)
  const dragIdx       = useRef<number | null>(null)
  const dropdownRef   = useRef<HTMLDivElement>(null)
  const [dropOpen, setDropOpen] = useState(false)

  const activePreset = matchPreset(samples)

  // Close dropdown on outside click
  useEffect(() => {
    if (!dropOpen) return
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropOpen(false)
      }
    }
    window.addEventListener('mousedown', handler)
    return () => window.removeEventListener('mousedown', handler)
  }, [dropOpen])

  const screenPts: [number, number][] = T_STEPS.map((t, i) => [tToSX(t), yToSY(samples[i])])
  const curvePath = catmullRomPath(screenPts)
  const bottomSY  = PY + PH
  const fillPath  = curvePath + ` L ${tToSX(1)} ${bottomSY} L ${tToSX(0)} ${bottomSY} Z`

  const vGridXs = T_STEPS.slice(1, -1).map(t => tToSX(t))

  function startDrag(idx: number) {
    if (disabled) return
    dragIdx.current = idx
  }

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (dragIdx.current === null || !svgRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    const svgY = ((e.clientY - rect.top) / rect.height) * VH
    const y    = Math.max(0, Math.min(Y_HI, sYToY(svgY)))
    const next = [...samples]
    next[dragIdx.current] = Math.round(y * 1000) / 1000
    onChange(next)
  }, [samples, onChange])

  const onMouseUp = useCallback(() => { dragIdx.current = null }, [])

  useEffect(() => {
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup',   onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup',   onMouseUp)
    }
  }, [onMouseMove, onMouseUp])

  return (
    <div className={`eq-editor${disabled ? ' eq-editor--disabled' : ''}`}>

      {/* Preset row — custom dropdown matching material preset style */}
      <div className="eq-header">
        <span className="eq-header-label">Preset</span>
        <div className="eq-select-wrap" ref={dropdownRef}>
          <button
            type="button"
            className={`eq-select${dropOpen ? ' eq-select--open' : ''}`}
            disabled={disabled}
            onClick={() => !disabled && setDropOpen(o => !o)}
          >
            <span>{activePreset ? PRESETS.find(p => p.id === activePreset)?.label : 'Custom'}</span>
            <svg className="eq-chevron" viewBox="0 0 10 6" fill="none" aria-hidden="true">
              <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          {dropOpen && (
            <div className="eq-dropdown">
              {!activePreset && (
                <button
                  type="button"
                  className="eq-dropdown-item eq-dropdown-item--active"
                  onMouseDown={e => { e.preventDefault(); setDropOpen(false) }}
                >
                  Custom
                </button>
              )}
              {PRESETS.map(p => (
                <button
                  key={p.id}
                  type="button"
                  className={`eq-dropdown-item${activePreset === p.id ? ' eq-dropdown-item--active' : ''}`}
                  onMouseDown={e => {
                    e.preventDefault()
                    onChange([...p.samples])
                    setDropOpen(false)
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main EQ chart */}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${VW} ${VH}`}
        className="eq-svg"
        style={{ display: 'block', width: '100%', userSelect: 'none' }}
      >
        <defs>
          {/* Gradient fill: amber top → transparent bottom */}
          <linearGradient id="eq-fill-grad" x1="0" y1={PY} x2="0" y2={PY + PH} gradientUnits="userSpaceOnUse">
            <stop offset="0%"   stopColor="#d4a843" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#d4a843" stopOpacity="0.02" />
          </linearGradient>
          {/* Clip to plot rect */}
          <clipPath id="eq-clip">
            <rect x={PX} y={PY} width={PW} height={PH} />
          </clipPath>
        </defs>

        {/* Plot background */}
        <rect x={PX} y={PY} width={PW} height={PH} className="eq-bg" />

        {/* Vertical column dividers */}
        {vGridXs.map((sx, i) => (
          <line key={`v${i}`} x1={sx} y1={PY} x2={sx} y2={PY + PH} className="eq-grid-v" />
        ))}

        {/* Horizontal reference lines + y-axis labels */}
        {Y_REFS.map(({ y, label }) => {
          const sy      = yToSY(y)
          const isEdge  = y === 0
          return (
            <g key={y}>
              <line
                x1={PX} y1={sy} x2={PX + PW} y2={sy}
                className={isEdge ? 'eq-ref-h' : 'eq-grid-h'}
              />
              <text x={PX - 5} y={sy} className="eq-y-label" textAnchor="end" dominantBaseline="middle">
                {label}
              </text>
            </g>
          )
        })}

        {/* Area fill (clipped) */}
        <path d={fillPath} fill="url(#eq-fill-grad)" clipPath="url(#eq-clip)" />

        {/* Curve line (clipped) */}
        <path d={curvePath} className="eq-curve" clipPath="url(#eq-clip)" />

        {/* Dot handles */}
        {screenPts.map(([x, y], i) => (
          <g
            key={i}
            style={{ cursor: 'ns-resize' }}
            onMouseDown={() => startDrag(i)}
          >
            <circle cx={x} cy={y} r={13} fill="transparent" />
            <circle cx={x} cy={y} r={4.5} className="eq-dot" />
          </g>
        ))}

        {/* X-axis time labels */}
        {T_STEPS.map((t, i) => (
          <text key={t} x={tToSX(t)} y={XLY} className="eq-x-label" textAnchor="middle">
            {X_LABELS[i]}
          </text>
        ))}
      </svg>

    </div>
  )
}
