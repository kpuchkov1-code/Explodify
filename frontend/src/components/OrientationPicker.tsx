// frontend/src/components/OrientationPicker.tsx
import type { FaceName } from '../api/client'

interface Props {
  selectedFace: FaceName
  onFaceChange: (face: FaceName) => void
  disabled?: boolean
}

// Grid layout (5 cols x 5 rows):
//
//              [top-left]  [top]      [top-right]
//  [back] [left] [front-left] [front] [front-right] [right]
//              [bot-front] [bottom]   [bot-back]
//
// Simplified to a practical 5x3 grid with diagonals at corners:

interface FaceEntry {
  name: FaceName
  label: string
  gridArea: string
}

const FACES: FaceEntry[] = [
  // Top row
  { name: 'top-left',     label: 'TL',     gridArea: 'tl' },
  { name: 'top',          label: 'Top',    gridArea: 'top' },
  { name: 'top-right',    label: 'TR',     gridArea: 'tr' },
  // Middle row
  { name: 'left',         label: 'Left',   gridArea: 'left' },
  { name: 'front-left',   label: 'FL',     gridArea: 'fl' },
  { name: 'front',        label: 'Front',  gridArea: 'front' },
  { name: 'front-right',  label: 'FR',     gridArea: 'fr' },
  { name: 'right',        label: 'Right',  gridArea: 'right' },
  // Bottom row
  { name: 'top-front',    label: 'TF',     gridArea: 'tf' },
  { name: 'bottom',       label: 'Bot',    gridArea: 'bottom' },
  { name: 'top-back',     label: 'TB',     gridArea: 'tb' },
  // Extra row
  { name: 'bottom-front', label: 'BF',     gridArea: 'bf' },
  { name: 'back',         label: 'Back',   gridArea: 'back' },
  { name: 'bottom-back',  label: 'BB',     gridArea: 'bb' },
]

const GRID_STYLE: React.CSSProperties = {
  display: 'grid',
  gridTemplateAreas: `
    ".    tl    top   tr   ."
    "left fl    front fr   right"
    ".    tf    bottom tb  ."
    ".    bf    back  bb   ."
  `,
  gridTemplateColumns: 'repeat(5, 1fr)',
  gridTemplateRows: 'repeat(4, 28px)',
  gap: '2px',
}

export function OrientationPicker({ selectedFace, onFaceChange, disabled }: Props) {
  return (
    <div>
      <div style={GRID_STYLE}>
        {FACES.map(({ name, label, gridArea }) => {
          const isSelected = selectedFace === name
          const isDiagonal = label.length <= 2
          return (
            <button
              key={name}
              onClick={() => onFaceChange(name)}
              disabled={disabled}
              style={{ gridArea }}
              className={[
                'cube-face-btn',
                isSelected ? 'cube-face-btn--selected' : '',
                isDiagonal ? 'cube-face-btn--diag' : '',
              ].filter(Boolean).join(' ')}
              title={name}
            >
              {label}
            </button>
          )
        })}
      </div>
      <p className="orient-selected-info">
        View: <strong>{selectedFace}</strong>
      </p>
    </div>
  )
}
