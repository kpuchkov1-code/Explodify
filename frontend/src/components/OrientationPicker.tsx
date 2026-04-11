// frontend/src/components/OrientationPicker.tsx
import { useState } from 'react'
import type { FaceName } from '../api/client'

interface Props {
  images: Record<FaceName, string>
  onConfirm: (face: FaceName, rotationDeg: number) => void
  disabled?: boolean
}

const FACE_LABELS: Record<FaceName, string> = {
  front:  'Front',
  back:   'Back',
  left:   'Left',
  right:  'Right',
  top:    'Top',
  bottom: 'Bottom',
}

// Cube net layout (4 cols x 3 rows):
//   .     top    .      .
//  left  front  right  back
//   .   bottom   .      .
const CUBE_GRID_AREA: Record<FaceName, string> = {
  top:    'top',
  left:   'left',
  front:  'front',
  right:  'right',
  back:   'back',
  bottom: 'bottom',
}

const CUBE_GRID_STYLE: React.CSSProperties = {
  display: 'grid',
  gridTemplateAreas: `
    ".    top    .      ."
    "left front  right  back"
    ".    bottom .      ."
  `,
  gridTemplateColumns: 'repeat(4, 3.25rem)',
  gridTemplateRows:    'repeat(3, 3.25rem)',
  gap: '3px',
}

export function OrientationPicker({ images, onConfirm, disabled }: Props) {
  const [selected, setSelected] = useState<FaceName>('front')
  const [rotation, setRotation] = useState(0)

  function selectFace(face: FaceName) {
    setSelected(face)
    setRotation(0)
  }

  function rotate() {
    setRotation(prev => (prev + 90) % 360)
  }

  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-2xl">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-gray-900">Choose orientation</h2>
        <p className="text-sm text-gray-500 mt-1">
          Click a face on the cube to set it as the front of the exploded view.
          Rotate to correct alignment.
        </p>
      </div>

      <div className="flex items-center justify-center gap-12 w-full flex-wrap">
        {/* Large preview of selected face */}
        <div className="flex flex-col items-center gap-3">
          <div className="w-52 h-52 bg-[#1a1a1d] rounded-2xl overflow-hidden flex items-center justify-center shadow-lg">
            <img
              src={images[selected]}
              alt={`${FACE_LABELS[selected]} view`}
              className="w-full h-full object-contain transition-transform duration-200"
              style={{ transform: `rotate(${rotation}deg)` }}
              draggable={false}
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={rotate}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-colors select-none"
            >
              ↻ Rotate 90°
            </button>
            {rotation !== 0 && (
              <span className="text-sm text-gray-400 tabular-nums">{rotation}°</span>
            )}
          </div>
          <p className="text-sm font-medium text-gray-600">
            Selected: <span className="text-gray-900 font-semibold">{FACE_LABELS[selected]}</span>
          </p>
        </div>

        {/* Interactive cube net */}
        <div>
          <div style={CUBE_GRID_STYLE}>
            {(Object.keys(CUBE_GRID_AREA) as FaceName[]).map(face => {
              const isSelected = selected === face
              return (
                <button
                  key={face}
                  onClick={() => selectFace(face)}
                  style={{ gridArea: CUBE_GRID_AREA[face] }}
                  className={[
                    'flex items-center justify-center text-xs font-semibold rounded-lg border-2 transition-all select-none cursor-pointer',
                    isSelected
                      ? 'bg-gray-900 text-white border-gray-900 shadow-md scale-105'
                      : 'bg-white text-gray-600 border-gray-300 hover:border-gray-500 hover:bg-gray-50 hover:text-gray-900',
                  ].join(' ')}
                >
                  {FACE_LABELS[face]}
                </button>
              )
            })}
          </div>
          <p className="text-xs text-gray-400 text-center mt-3">Click a face to select</p>
        </div>
      </div>

      <button
        onClick={() => onConfirm(selected, rotation)}
        disabled={disabled}
        className="px-10 py-3 bg-gray-900 text-white rounded-xl font-medium hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Start Exploding →
      </button>
    </div>
  )
}
