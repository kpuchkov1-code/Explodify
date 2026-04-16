import type { DebugState } from './createViewer'

interface Props {
  state: DebugState
}

export function DebugOverlay({ state }: Props) {
  const w = Math.round(state.rect.width)
  const h = Math.round(state.rect.height)
  const degenerate = w < 2 || h < 2
  const lines = [
    `rect:  ${w} x ${h}`,
    `dpr:   ${state.pixelRatio}`,
    `downs: ${state.pointerDowns}`,
    `hit:   ${state.lastHit || '-'}`,
  ].join('\n')
  return (
    <div className={`ov-debug${degenerate ? ' ov-debug--error' : ''}`}>
      {lines}
    </div>
  )
}
