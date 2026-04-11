// frontend/src/components/FramesPreview.tsx
const FRAME_NAMES = ['frame_a', 'frame_b', 'frame_c', 'frame_d', 'frame_e'] as const
const FRAME_LABELS = ['0% — assembled', '25%', '50%', '75%', '100% — exploded']

interface Props {
  jobId: string
}

export function FramesPreview({ jobId }: Props) {
  return (
    <div className="flex flex-col items-center gap-6 w-full max-w-5xl">
      <h2 className="text-lg font-semibold text-gray-900">Keyframes</h2>
      <div className="grid grid-cols-5 gap-3 w-full">
        {FRAME_NAMES.map((name, i) => (
          <div key={name} className="flex flex-col gap-1">
            <div className="rounded-lg overflow-hidden bg-[#262629] aspect-[4/3]">
              <img
                src={`/jobs/${jobId}/frames/${name}`}
                alt={FRAME_LABELS[i]}
                className="w-full h-full object-contain"
              />
            </div>
            <p className="text-[11px] text-gray-500 text-center">{FRAME_LABELS[i]}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
