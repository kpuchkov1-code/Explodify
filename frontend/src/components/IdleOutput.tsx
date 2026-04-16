export function IdleOutput() {
  return (
    <div className="idle-output animate-fade-in">
      <div className="idle-grid-bg" />
      <div className="idle-content">
        <div className="idle-diagram">
          <div className="idle-ring" />
          <div className="idle-ring-inner" />
          <div className="idle-crosshair">
            <div className="idle-dot" />
          </div>
        </div>
        <div className="idle-title">Upload a CAD file to begin</div>
        <div className="idle-hint">
          Supported formats: GLB, OBJ, STEP, STL<br />
          Drop a file or click to browse
        </div>
      </div>
    </div>
  )
}
