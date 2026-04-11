// frontend/src/components/VideoOutput.tsx

interface Props {
  jobId: string
}

export function VideoOutput({ jobId }: Props) {
  const styledUrl = `/jobs/${jobId}/video`

  return (
    <div className="video-output-section animate-fade-in">
      <div className="video-hero">
        <div className="video-hero-header">
          <div className="video-hero-title-row">
            <span className="video-hero-badge">FINAL OUTPUT</span>
            <span className="video-hero-title">AI STYLED VIDEO</span>
          </div>
          <a
            className="video-dl-btn"
            href={styledUrl}
            download={`explodify_styled_${jobId}.mp4`}
          >
            ↓ Download
          </a>
        </div>
        <div className="video-hero-stage">
          <video
            src={styledUrl}
            controls
            autoPlay
            loop
            playsInline
            className="video-hero-player"
          />
        </div>
      </div>
    </div>
  )
}
