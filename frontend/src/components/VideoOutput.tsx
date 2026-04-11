// frontend/src/components/VideoOutput.tsx
import { useRef } from 'react'

interface Props {
  jobId: string
}

export function VideoOutput({ jobId }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const videoUrl = `/jobs/${jobId}/video`

  return (
    <div className="video-output">
      <div className="video-output-header">
        <span className="section-label">Styled Video</span>
        <a
          className="video-download-btn"
          href={videoUrl}
          download={`explodify_${jobId}.mp4`}
        >
          Download mp4
        </a>
      </div>
      <div className="video-player-wrap">
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          autoPlay
          loop
          playsInline
          className="video-player"
        />
      </div>
    </div>
  )
}
