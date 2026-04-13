// frontend/src/components/StylePanel.tsx
import { useState } from 'react'
import type { StyleOptions } from '../App'

const MAX_MATERIAL_CHARS = 400
const MAX_STYLE_CHARS = 400
const MAX_PER_COMPONENT_CHARS = 120

interface Props {
  options: StyleOptions
  onOptionsChange: (opts: StyleOptions) => void
  explodeScalar: number
  onExplodeChange: (v: number) => void
  orbitRangeDeg: number
  onOrbitRangeChange: (v: number) => void
  componentNames?: string[]
  disabled?: boolean
}

const CHECKBOX_ITEMS: Array<{ key: keyof Omit<StyleOptions, 'prompt' | 'componentMaterials'>; label: string }> = [
  { key: 'studioLighting', label: 'Studio lighting' },
  { key: 'darkBackdrop',   label: 'Dark backdrop' },
  { key: 'whiteBackdrop',  label: 'White backdrop' },
  { key: 'warmTone',       label: 'Warm tone' },
  { key: 'coldTone',       label: 'Cold tone' },
  { key: 'groundShadow',   label: 'Ground shadow' },
]

export function StylePanel({
  options,
  onOptionsChange,
  explodeScalar,
  onExplodeChange,
  orbitRangeDeg,
  onOrbitRangeChange,
  componentNames = [],
  disabled,
}: Props) {
  const [perComponentOpen, setPerComponentOpen] = useState(false)

  function toggleOption(key: keyof Omit<StyleOptions, 'prompt' | 'componentMaterials'>) {
    onOptionsChange({ ...options, [key]: !options[key] })
  }

  function setComponentMaterial(name: string, value: string) {
    onOptionsChange({
      ...options,
      componentMaterials: { ...options.componentMaterials, [name]: value },
    })
  }

  const hasComponents = componentNames.length > 0

  return (
    <div className="style-panel">

      {/* Style checkboxes */}
      <div className="checkbox-grid">
        {CHECKBOX_ITEMS.map(({ key, label }) => {
          const checked = options[key] as boolean
          return (
            <div
              key={key}
              className={[
                'checkbox-option',
                checked ? 'checkbox-option--checked' : '',
                disabled ? 'checkbox-option--disabled' : '',
              ].join(' ')}
              onClick={() => !disabled && toggleOption(key)}
            >
              <div className={['checkbox-box', checked ? 'checkbox-box--checked' : ''].join(' ')}>
                {checked && <span className="checkbox-check-mark">✓</span>}
              </div>
              <span className="checkbox-label">{label}</span>
            </div>
          )
        })}
      </div>

      {/* Material description */}
      <div className="prompt-section">
        <span className="prompt-section-label">Materials</span>
        <textarea
          className="style-prompt"
          rows={2}
          maxLength={MAX_MATERIAL_CHARS}
          placeholder="e.g. brushed aluminium body, matte black cap, frosted glass lens..."
          value={options.materialPrompt}
          onChange={(e) => onOptionsChange({ ...options, materialPrompt: e.target.value })}
          disabled={disabled}
        />
        <span className="char-counter">{options.materialPrompt.length}/{MAX_MATERIAL_CHARS}</span>
      </div>

      {/* Per-component materials */}
      {hasComponents && (
        <div className="per-component-section">
          <button
            className="per-component-toggle"
            onClick={() => setPerComponentOpen(v => !v)}
            disabled={disabled}
            type="button"
          >
            <span className="prompt-section-label">Per-component materials</span>
            <span className="per-component-chevron">{perComponentOpen ? '▲' : '▼'}</span>
          </button>

          {perComponentOpen && (
            <div className="per-component-list">
              {componentNames.map(name => (
                <div key={name} className="per-component-row">
                  <span className="per-component-name">{name}</span>
                  <input
                    className="per-component-input"
                    type="text"
                    maxLength={MAX_PER_COMPONENT_CHARS}
                    placeholder="e.g. brushed steel"
                    value={options.componentMaterials[name] ?? ''}
                    onChange={(e) => setComponentMaterial(name, e.target.value)}
                    disabled={disabled}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Style prompt */}
      <div className="prompt-section">
        <span className="prompt-section-label">Style notes</span>
        <textarea
          className="style-prompt"
          rows={2}
          maxLength={MAX_STYLE_CHARS}
          placeholder="Additional style notes... (mood, lighting, colour)"
          value={options.prompt}
          onChange={(e) => onOptionsChange({ ...options, prompt: e.target.value })}
          disabled={disabled}
        />
        <span className="char-counter">{options.prompt.length}/{MAX_STYLE_CHARS}</span>
      </div>

      {/* Explosion level slider */}
      <div className="slider-row">
        <div className="slider-header">
          <span className="slider-label">Explosion Level</span>
        </div>
        <div className="slider-value-row">
          <input
            type="range"
            min={0.5}
            max={4.0}
            step={0.1}
            value={explodeScalar}
            onChange={(e) => onExplodeChange(parseFloat(e.target.value))}
            disabled={disabled}
          />
          <span className="slider-value">{explodeScalar.toFixed(1)}×</span>
          <InfoIcon text="Auto-zoom adjusts camera distance to keep all components in frame at any scalar value." />
        </div>
      </div>

      {/* Camera orbit range slider */}
      <div className="slider-row">
        <div className="slider-header">
          <span className="slider-label">Camera Orbit</span>
        </div>
        <div className="slider-value-row">
          <input
            type="range"
            min={0}
            max={60}
            step={5}
            value={orbitRangeDeg}
            onChange={(e) => onOrbitRangeChange(parseInt(e.target.value))}
            disabled={disabled}
          />
          <span className="slider-value">{orbitRangeDeg}°</span>
          <InfoIcon text="Total orbit from frame 1 to frame 5. Capped at 60° for Kling interpolation safety." />
        </div>
      </div>

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
