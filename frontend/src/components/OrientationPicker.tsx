// frontend/src/components/OrientationPicker.tsx
import { useState } from 'react'
import type { FaceName } from '../api/client'

const FACES: FaceName[] = ['front', 'back', 'left', 'right', 'top', 'bottom']

const FACE_LABELS: Record<FaceName, string> = {
  front:  'Front',
  back:   'Back',
  left:   'Left',
  right:  'Right',
  top:    'Top',
  bottom: 'Bottom',
}

interface Props {
  images: Record<FaceName, string>
  onConfirm: (face: FaceName, rotationDeg: number) => void
  disabled?: boolean
}

type RotationMap = Record<FaceName, number>

const ZERO_ROTATIONS: RotationMap = {
  front: 0, back: 0, left: 0, right: 0, top: 0, bottom: 0,
}

export function OrientationPicker({ images, onConfirm, disabled }: Props) {
  const [selected, setSelected] = useState<FaceName>('front')
  const [rotations, setRotations] = useState<RotationMap>(ZERO_ROTATIONS)

  function rotateCW(face: FaceName, e: React.MouseEvent) {
    e.stopPropagation()
    setRotations(prev => ({ ...prev, [face]: (prev[face] + 90) % 360 }))
  }

  function rotateCCW(face: FaceName, e: React.MouseEvent) {
    e.stopPropagation()
    setRotations(prev => ({ ...prev, [face]: (prev[face] + 270) % 360 }))
  }

  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-3xl">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-gray-900">Choose orientation</h2>
        <p className="text-sm text-gray-500 mt-1">
          Select the face that should be the <strong>front</strong> of the exploded view.
          Rotate to correct alignment if needed.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4 w-full">
        {FACES.map(face => {
          const isSelected = selected === face
          return (
            <div
              key={face}
              onClick={() => setSelected(face)}
              className={[
                'flex flex-col items-center gap-2 cursor-pointer rounded-xl p-2 transition-all select-none',
                isSelected
                  ? 'ring-2 ring-gray-900 bg-gray-50 shadow-sm'
                  : 'ring-1 ring-gray-200 hover:ring-gray-400 hover:bg-gray-50',
              ].join(' ')}
            >
              {/* Thumbnail */}
              <div className="relative w-full overflow-hidden rounded-lg bg-[#262629] aspect-[4/3] flex items-center justify-center">
                <img
                  src={images[face]}
                  alt={`${FACE_LABELS[face]} view`}
                  className="w-full h-full object-contain transition-transform duration-200"
                  style={{ transform: `rotate(${rotations[face]}deg)` }}
                  draggable={false}
                />
                {isSelected && (
                  <div className="absolute top-1.5 right-1.5 bg-gray-900 text-white text-[10px] font-semibold px-1.5 py-0.5 rounded">
                    SELECTED
                  </div>
                )}
              </div>

              {/* Label + rotate controls */}
              <div className="flex items-center justify-between w-full px-0.5">
                <span className="text-xs font-medium text-gray-700">
                  {FACE_LABELS[face]}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => rotateCCW(face, e)}
                    title="Rotate 90° counter-clockwise"
                    className="text-xs text-gray-400 hover:text-gray-700 w-6 h-6 flex items-center justify-center rounded border border-gray-200 hover:border-gray-400 transition-colors"
                  >
                    ↺
                  </button>
                  <span className="text-[10px] text-gray-400 w-7 text-center tabular-nums">
                    {rotations[face]}°
                  </span>
                  <button
                    onClick={(e) => rotateCW(face, e)}
                    title="Rotate 90° clockwise"
                    className="text-xs text-gray-400 hover:text-gray-700 w-6 h-6 flex items-center justify-center rounded border border-gray-200 hover:border-gray-400 transition-colors"
                  >
                    ↻
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex flex-col items-center gap-2">
        <button
          onClick={() => onConfirm(selected, rotations[selected])}
          disabled={disabled}
          className="px-10 py-3 bg-gray-900 text-white rounded-xl font-medium hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Start Exploding →
        </button>
        <p className="text-xs text-gray-400">
          Front: <strong>{FACE_LABELS[selected]}</strong>
          {rotations[selected] !== 0 && ` · rotated ${rotations[selected]}°`}
        </p>
      </div>
    </div>
  )
}
