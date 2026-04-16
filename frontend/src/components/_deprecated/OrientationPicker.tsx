// DEPRECATED — replaced by MeshViewer (Three.js orbit for 3D, static preview for other formats).
// Kept for reference only. Do not import.
// frontend/src/components/OrientationPicker.tsx
import type { FaceName } from '../api/client'

interface Props {
  selectedFace: FaceName
  onFaceChange: (face: FaceName) => void
  disabled?: boolean
}

interface FaceEntry {
  name: FaceName
  label: string
  gridArea: string
}

const FACES: FaceEntry[] = [
  { name: 'top',    label: 'Top',    gridArea: 'top' },
  { name: 'left',   label: 'Left',   gridArea: 'left' },
  { name: 'front',  label: 'Front',  gridArea: 'front' },
  { name: 'right',  label: 'Right',  gridArea: 'right' },
  { name: 'bottom', label: 'Bottom', gridArea: 'bottom' },
  { name: 'back',   label: 'Back',   gridArea: 'back' },
]

const GRID_STYLE: React.CSSProperties = {
  display: 'grid',
  gridTemplateAreas: `
    ".    top    ."
    "left front  right"
    ".    bottom ."
    ".    back   ."
  `,
  gridTemplateColumns: 'repeat(3, 64px)',
  gridTemplateRows: 'repeat(4, 56px)',
  gap: '4px',
}

export function OrientationPicker({ selectedFace, onFaceChange, disabled }: Props) {
  return (
    <div className="orient-picker">
      <div style={GRID_STYLE}>
        {FACES.map(({ name, label, gridArea }) => {
          const isSelected = selectedFace === name
          return (
            <button
              key={name}
              onClick={() => onFaceChange(name)}
              disabled={disabled}
              style={{ gridArea }}
              className={[
                'cube-face-btn',
                isSelected ? 'cube-face-btn--selected' : '',
              ].filter(Boolean).join(' ')}
              title={name}
            >
              {label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
