// frontend/src/components/StylePanel.tsx
import { useState } from 'react'
import type { StyleOptions, Row } from '../App'

const MAX_SHARED_CHARS = 800
const MAX_ROWS = 20

const MATERIAL_PRESETS = [
  'brushed aluminium',
  'matte plastic',
  'frosted glass',
  'carbon fibre weave',
  'textured rubber',
  'polished chrome',
  'stainless steel',
  'natural wood',
  'anodized aluminium',
  'ABS plastic',
]

const STYLE_TAGS = [
  { label: 'Black void',  phrase: 'pure black infinite void background' },
  { label: 'Grey void',   phrase: 'neutral mid-grey infinite void background' },
  { label: 'White void',  phrase: 'pure white infinite void background' },
  { label: 'Warm light',  phrase: 'warm 3800K three-point area lighting, soft amber fill' },
  { label: 'Cool light',  phrase: 'cool 6500K neutral area lighting, clinical precision' },
  { label: 'Rim light',   phrase: 'sharp rim light separating components from background' },
]

function countChars(rows: Row[], prompt: string): number {
  return rows.reduce((s, r) => s + r.part.length + r.material.length, 0) + prompt.length
}

function addPhrase(current: string, phrase: string): string {
  if (current.includes(phrase)) return current
  const t = current.trimEnd()
  return t ? `${t}, ${phrase}` : phrase
}

function removePhrase(current: string, phrase: string): string {
  const esc = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return current
    .replace(new RegExp(`,?\\s*${esc}`, 'g'), '')
    .replace(new RegExp(`${esc}\\s*,?\\s*`, 'g'), '')
    .trim()
    .replace(/^,\s*/, '')
    .replace(/,\s*$/, '')
}

interface Props {
  options: StyleOptions
  onOptionsChange: (opts: StyleOptions) => void
  explodeScalar?: number
  onExplodeChange?: (v: number) => void
  orbitRangeDeg?: number
  onOrbitRangeChange?: (v: number) => void
  disabled?: boolean
}

export function StylePanel({
  options,
  onOptionsChange,
  explodeScalar,
  onExplodeChange,
  orbitRangeDeg,
  onOrbitRangeChange,
  disabled,
}: Props) {
  const [focusedRow, setFocusedRow] = useState<number | null>(null)

  const used = countChars(options.rows, options.prompt)
  const overLimit = used > MAX_SHARED_CHARS
  const canAddRow = !disabled && options.rows.length < MAX_ROWS && !overLimit

  function updateRow(idx: number, field: keyof Row, value: string) {
    const next = options.rows.map((r, i) => i === idx ? { ...r, [field]: value } : r)
    onOptionsChange({ ...options, rows: next })
  }

  function addRow() {
    onOptionsChange({ ...options, rows: [...options.rows, { part: '', material: '' }] })
  }

  function removeRow(idx: number) {
    onOptionsChange({ ...options, rows: options.rows.filter((_, i) => i !== idx) })
  }

  function setMaterialPreset(idx: number, preset: string) {
    updateRow(idx, 'material', preset)
  }

  function updatePrompt(value: string) {
    onOptionsChange({ ...options, prompt: value })
  }

  return (
    <div className="style-panel">

      {/* Component / material table */}
      <div className="prompt-section">
        <span className="prompt-section-label">Components &amp; Materials</span>

        <div className="cmt">
          {/* Header */}
          <div className="cmt-head">
            <span className="cmt-head-part">Part</span>
            <span className="cmt-head-material">Material</span>
            <span className="cmt-head-action" />
          </div>

          {/* Rows */}
          <div className="cmt-body">
            {options.rows.map((row, idx) => (
              <div key={idx} className="cmt-row-wrap">
                <div className="cmt-row">
                  <input
                    className="cmt-input cmt-input--part"
                    type="text"
                    placeholder={`Part ${idx + 1}`}
                    value={row.part}
                    onChange={e => updateRow(idx, 'part', e.target.value)}
                    disabled={disabled}
                    spellCheck={false}
                  />
                  <div className="cmt-material-cell">
                    <input
                      className="cmt-input cmt-input--material"
                      type="text"
                      placeholder="material..."
                      value={row.material}
                      onFocus={() => setFocusedRow(idx)}
                      onBlur={() => setTimeout(() => setFocusedRow(f => f === idx ? null : f), 120)}
                      onChange={e => updateRow(idx, 'material', e.target.value)}
                      disabled={disabled}
                      spellCheck={false}
                    />
                    {focusedRow === idx && (
                      <div
                        className="cmt-presets"
                        onMouseDown={e => e.preventDefault()}
                      >
                        {MATERIAL_PRESETS.map(preset => (
                          <button
                            key={preset}
                            className={['cmt-preset', row.material === preset ? 'cmt-preset--active' : ''].filter(Boolean).join(' ')}
                            type="button"
                            onMouseDown={e => {
                              e.preventDefault()
                              setMaterialPreset(idx, preset)
                            }}
                          >
                            {preset}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <button
                    className="cmt-row-remove"
                    type="button"
                    onClick={() => removeRow(idx)}
                    disabled={disabled}
                    tabIndex={-1}
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="cmt-footer">
            <button
              className="cmt-add-btn"
              type="button"
              onClick={addRow}
              disabled={!canAddRow}
            >
              + Add component
            </button>
            <span className={['cmt-counter', overLimit ? 'cmt-counter--over' : ''].filter(Boolean).join(' ')}>
              {used} / {MAX_SHARED_CHARS}
            </span>
          </div>
        </div>
      </div>

      {/* Style notes */}
      <div className="prompt-section">
        <span className="prompt-section-label">Style notes</span>
        <textarea
          className="style-prompt"
          rows={2}
          placeholder="Lighting, backdrop, mood, colour..."
          value={options.prompt}
          onChange={e => updatePrompt(e.target.value)}
          disabled={disabled}
        />
        <div className="tag-bar">
          {STYLE_TAGS.map(({ label, phrase }) => {
            const active = options.prompt.includes(phrase)
            return (
              <button
                key={phrase}
                type="button"
                disabled={disabled}
                className={['tag', active ? 'tag--active' : ''].filter(Boolean).join(' ')}
                onClick={() => {
                  if (disabled) return
                  updatePrompt(active ? removePhrase(options.prompt, phrase) : addPhrase(options.prompt, phrase))
                }}
              >
                <span className="tag-icon">{active ? '×' : '+'}</span>
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Explosion level — hidden in compact/restyle mode */}
      {explodeScalar !== undefined && onExplodeChange && (
        <div className="slider-row">
          <div className="slider-header">
            <span className="slider-label">Explosion Level</span>
          </div>
          <div className="slider-value-row">
            <input
              type="range" min={0.5} max={4.0} step={0.1}
              value={explodeScalar}
              onChange={e => onExplodeChange(parseFloat(e.target.value))}
              disabled={disabled}
            />
            <span className="slider-value">{explodeScalar.toFixed(1)}×</span>
            <InfoIcon text="Auto-zoom adjusts camera distance to keep all components in frame." />
          </div>
        </div>
      )}

      {/* Camera orbit — hidden in compact/restyle mode */}
      {orbitRangeDeg !== undefined && onOrbitRangeChange && (
        <div className="slider-row">
          <div className="slider-header">
            <span className="slider-label">Camera Orbit</span>
          </div>
          <div className="slider-value-row">
            <input
              type="range" min={0} max={60} step={5}
              value={orbitRangeDeg}
              onChange={e => onOrbitRangeChange(parseInt(e.target.value))}
              disabled={disabled}
            />
            <span className="slider-value">{orbitRangeDeg}°</span>
            <InfoIcon text="Total camera orbit range during rendering." />
          </div>
        </div>
      )}

    </div>
  )
}

function InfoIcon({ text }: { text: string }) {
  return (
    <span className="info-icon">
      i
      <span className="info-tooltip">{text}</span>
    </span>
  )
}
