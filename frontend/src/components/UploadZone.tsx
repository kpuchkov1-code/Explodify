// frontend/src/components/UploadZone.tsx
import { useState } from 'react'
import type { DragEvent, ChangeEvent } from 'react'

interface Props {
  onUpload: (file: File) => void
  loading?: boolean
}

const FORMATS = [
  { ext: '.obj', note: 'recommended' },
  { ext: '.glb', note: null },
  { ext: '.stl', note: null },
  { ext: '.step', note: 'STP' },
] as const

export function UploadZone({ onUpload, loading }: Props) {
  const [dragging, setDragging] = useState(false)

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && !loading) onUpload(file)
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) onUpload(file)
    e.target.value = ''
  }

  const zoneClass = [
    'upload-zone',
    dragging ? 'upload-zone--drag' : '',
    loading ? 'upload-zone--loading' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className="upload-zone-wrapper">
      <div
        className={zoneClass}
        onDragOver={(e) => { e.preventDefault(); if (!loading) setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !loading && document.getElementById('cad-file-input')?.click()}
      >
        {loading ? (
          <div className="upload-loading-inner">
            <div className="sweep-bar" />
            <span>Reading geometry...</span>
          </div>
        ) : (
          <>
            <div className="upload-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="1.5"
                strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="upload-cta">
              {dragging ? 'Release to load' : 'Drop CAD file here'}
            </p>
            <p className="upload-sub">or click to browse</p>
          </>
        )}
        <input
          id="cad-file-input"
          type="file"
          accept=".obj,.glb,.stl,.step,.stp"
          style={{ display: 'none' }}
          onChange={handleFileChange}
          disabled={loading}
        />
      </div>

      <div className="format-list">
        {FORMATS.map(({ ext, note }) => (
          <span key={ext} className="format-tag">
            {ext}
            {note && <span className="format-note">{note}</span>}
          </span>
        ))}
      </div>
    </div>
  )
}
