import { forwardRef, useImperativeHandle, useMemo, useRef, useState } from 'react'
import type { ExplosionAxes, VariantName, FaceName } from '../api/client'
import { OrientationViewer } from './orientation/OrientationViewer'
import type { Orientation, Vec3 } from './orientation/createViewer'

const THREE_D_FORMATS = ['glb', 'gltf', 'obj']

function fileExt(name: string): string {
  return name.split('.').pop()?.toLowerCase() ?? ''
}

interface Props {
  file: File
  previewImages: Record<FaceName, string>
  explosionAxes: ExplosionAxes | null
  selectedAxis: VariantName
  onAxisChange: (axis: VariantName) => void
  explodeScalar: number
  onExplodeChange: (v: number) => void
  orbitRangeDeg: number
  onOrbitRangeChange: (v: number) => void
  onCameraDirectionChange?: (dir: Vec3) => void
  initialCameraDirection?: Vec3
}

export interface MeshViewerHandle {
  getCameraDirection: () => Vec3
}

function StaticPreview({ imageSrc, fileName }: { imageSrc: string; fileName: string }) {
  const ext = fileExt(fileName).toUpperCase()
  return (
    <>
      <div className="orient-face-badge">{ext} model</div>
      <img src={imageSrc} alt="Model preview" className="orient-preview-img" draggable={false} />
    </>
  )
}

export const MeshViewer = forwardRef<MeshViewerHandle, Props>(function MeshViewer({
  file,
  previewImages,
  explosionAxes,
  selectedAxis,
  onAxisChange,
  explodeScalar,
  onExplodeChange,
  orbitRangeDeg,
  onOrbitRangeChange,
  onCameraDirectionChange,
  initialCameraDirection,
}, ref) {
  const ext = useMemo(() => fileExt(file.name), [file.name])
  const is3D = THREE_D_FORMATS.includes(ext)
  const [forceStatic] = useState(false)

  const dirRef = useRef<Vec3>([0.3, 0.3, 1.0])
  const [displayDir, setDisplayDir] = useState<Vec3>([0.3, 0.3, 1.0])

  useImperativeHandle(ref, () => ({
    getCameraDirection: () => dirRef.current,
  }))

  // Stable callback reference — captured once by OrientationViewer's useEffect.
  // Reads through dirRef so it always reflects the latest direction on imperative reads.
  const onChangeCbRef = useRef<((o: Orientation) => void) | null>(null)
  onChangeCbRef.current = (o: Orientation) => {
    const dx = o.position[0] - o.target[0]
    const dy = o.position[1] - o.target[1]
    const dz = o.position[2] - o.target[2]
    const len = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1
    const dir: Vec3 = [dx / len, dy / len, dz / len]
    dirRef.current = dir
    setDisplayDir(dir)
    onCameraDirectionChange?.(dir)
  }
  const stableOrientationCb = useRef<(o: Orientation) => void>((o) => {
    onChangeCbRef.current?.(o)
  })

  const axisLabel = (a: VariantName) =>
    a === 'longest' ? 'Longest Axis' : 'Shortest Axis'

  const axisDirection: Vec3 | null = explosionAxes
    ? (explosionAxes[selectedAxis] as Vec3)
    : null

  const show3D = is3D && !forceStatic

  // Progress percentage for slider fill styling
  const explodePct = ((explodeScalar - 0.5) / (4.0 - 0.5)) * 100
  const orbitPct = (orbitRangeDeg / 60) * 100

  return (
    <div className="mesh-viewer-panel animate-fade-in">
      <div className="mesh-viewer-canvas-wrap">
        {show3D ? (
          <OrientationViewer
            file={file}
            axisDirection={axisDirection}
            explodeScalar={explodeScalar}
            orbitRangeDeg={orbitRangeDeg}
            onOrientationChange={stableOrientationCb.current}
            initialCameraDirection={initialCameraDirection}
          />
        ) : (
          <StaticPreview imageSrc={previewImages['front']} fileName={file.name} />
        )}

        {/* Axis selector — top right */}
        {explosionAxes && (
          <div className="mesh-viewer-axis-overlay">
            <div className="mesh-viewer-axis-title">Explosion Axis</div>
            {(['longest', 'shortest'] as VariantName[]).map((axis) => (
              <button
                key={axis}
                className={[
                  'mesh-axis-btn',
                  `mesh-axis-btn--${axis}`,
                  selectedAxis === axis ? 'mesh-axis-btn--active' : '',
                ].filter(Boolean).join(' ')}
                onClick={() => onAxisChange(axis)}
              >
                <span className="mesh-axis-indicator" />
                <span className="mesh-axis-name">{axisLabel(axis)}</span>
              </button>
            ))}
          </div>
        )}

        {/* Vector readout — bottom right */}
        {explosionAxes && (
          <div className="mesh-axis-vector">
            [{explosionAxes[selectedAxis].map((v) => v.toFixed(2)).join(', ')}]
          </div>
        )}

        {/* Camera direction readout — bottom centre */}
        {show3D && (
          <div className="mesh-cam-dir-readout">
            cam [{displayDir.map((v) => v.toFixed(2)).join(', ')}]
          </div>
        )}

        {/* Sliders — bottom left */}
        <div className="viewer-sliders">
          <div className="viewer-slider-row">
            <div className="viewer-slider-header">
              <span className="viewer-slider-label" style={{ color: '#f5a623' }}>Explosion Level</span>
              <span className="viewer-slider-value" style={{ color: '#f5a623' }}>{explodeScalar.toFixed(1)}×</span>
            </div>
            <input
              type="range"
              className="viewer-slider viewer-slider--explode"
              min={0.5} max={4.0} step={0.1}
              value={explodeScalar}
              style={{ '--pct': `${explodePct}%` } as React.CSSProperties}
              onChange={e => onExplodeChange(parseFloat(e.target.value))}
            />
          </div>

          <div className="viewer-slider-row">
            <div className="viewer-slider-header">
              <span className="viewer-slider-label" style={{ color: '#4a90e2' }}>Camera Orbit</span>
              <span className="viewer-slider-value" style={{ color: '#4a90e2' }}>{orbitRangeDeg}°</span>
            </div>
            <input
              type="range"
              className="viewer-slider viewer-slider--orbit"
              min={0} max={60} step={5}
              value={orbitRangeDeg}
              style={{ '--pct': `${orbitPct}%` } as React.CSSProperties}
              onChange={e => onOrbitRangeChange(parseInt(e.target.value))}
            />
          </div>
        </div>
      </div>
    </div>
  )
})
