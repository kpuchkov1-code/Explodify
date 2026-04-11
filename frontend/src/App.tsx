// frontend/src/App.tsx
import { useState, useEffect, useRef } from 'react'
import { UploadZone } from './components/UploadZone'
import { PromptInput } from './components/PromptInput'
import { PipelineProgress } from './components/PipelineProgress'
import { OrientationPicker } from './components/OrientationPicker'
import { FramesPreview } from './components/FramesPreview'
import { getPreviewImages, createJob, getJobStatus } from './api/client'
import type { JobStatus, FaceName, PreviewResult } from './api/client'

type AppState =
  | 'idle'
  | 'uploading'       // waiting for /preview response
  | 'orientation'     // showing 6-face picker
  | 'processing'      // pipeline running
  | 'done'
  | 'error'

export default function App() {
  const [state, setState] = useState<AppState>('uploading')  // start loading sample
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [stylePrompt, setStylePrompt] = useState('')
  const [scalar, setScalar] = useState(1.5)
  const [preview, setPreview] = useState<PreviewResult | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Auto-load sample on mount
  useEffect(() => {
    async function loadSample() {
      try {
        const resp = await fetch('/preview/sample')
        if (!resp.ok) throw new Error(`Sample preview failed: ${resp.statusText}`)
        const result: PreviewResult = await resp.json()
        setPreview(result)
        setState('orientation')
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : 'Failed to load sample')
        setState('error')
      }
    }
    loadSample()
  }, [])

  // Step 1: upload file → fetch 6 orientation previews
  async function handleUpload(file: File, uploadedScalar: number) {
    setScalar(uploadedScalar)
    setErrorMsg(null)
    try {
      setState('uploading')
      const result = await getPreviewImages(file)
      setPreview(result)
      setState('orientation')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Preview failed')
      setState('error')
    }
  }

  // Step 2: user confirms orientation → create job
  async function handleOrientationConfirm(face: FaceName, rotationDeg: number) {
    if (!preview) return
    try {
      const id = await createJob({
        previewId: preview.preview_id,
        explodeScalar: scalar,
        stylePrompt,
        masterAngle: face,
        rotationOffsetDeg: rotationDeg,
      })
      setJobId(id)
      setState('processing')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Job creation failed')
      setState('error')
    }
  }

  // Poll job status while processing
  useEffect(() => {
    if (state !== 'processing' || !jobId) return

    pollRef.current = setInterval(async () => {
      try {
        const status = await getJobStatus(jobId)
        setJobStatus(status)
        if (status.status === 'done') {
          setState('done')
          clearInterval(pollRef.current!)
        } else if (status.status === 'error') {
          setErrorMsg(status.error ?? 'Pipeline error')
          setState('error')
          clearInterval(pollRef.current!)
        }
      } catch {
        // keep polling on transient network errors
      }
    }, 2000)

    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [state, jobId])

  function reset() {
    setState('idle')
    setJobId(null)
    setJobStatus(null)
    setPreview(null)
    setStylePrompt('')
    setScalar(1.5)
    setErrorMsg(null)
  }

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-start px-4 py-16 gap-10">
      <header className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">Explodify</h1>
        <p className="text-gray-500 mt-2">CAD file → studio-grade exploded-view animation</p>
      </header>

      {/* Loading state (sample auto-load or user upload) */}
      {state === 'uploading' && (
        <p className="text-sm text-gray-500 animate-pulse">
          Rendering 6 orientation views…
        </p>
      )}

      {/* Upload your own (shown only when explicitly idle after reset) */}
      {state === 'idle' && (
        <>
          <PromptInput
            value={stylePrompt}
            onChange={setStylePrompt}
            disabled={false}
          />
          <UploadZone onUpload={handleUpload} disabled={false} />
        </>
      )}

      {/* Step 2: Orientation selection */}
      {state === 'orientation' && preview && (
        <>
          <OrientationPicker
            images={preview.images}
            onConfirm={handleOrientationConfirm}
          />
          <button
            onClick={() => setState('idle')}
            className="text-xs text-gray-400 hover:text-gray-600 underline -mt-4"
          >
            Upload your own file instead
          </button>
        </>
      )}

      {/* Step 3: Pipeline progress */}
      {state === 'processing' && jobStatus && (
        <PipelineProgress job={jobStatus} />
      )}
      {state === 'processing' && !jobStatus && (
        <p className="text-sm text-gray-500 animate-pulse">Starting pipeline...</p>
      )}

      {/* Step 4: Done */}
      {state === 'done' && jobId && (
        <>
          <FramesPreview jobId={jobId} />
          <button
            onClick={reset}
            className="text-sm text-gray-400 hover:text-gray-600 underline"
          >
            Try another orientation
          </button>
        </>
      )}

      {/* Error */}
      {state === 'error' && (
        <div className="flex flex-col items-center gap-4 max-w-md text-center">
          <p className="text-red-600 text-sm font-medium">
            {errorMsg ?? 'Something went wrong'}
          </p>
          <button
            onClick={reset}
            className="text-sm text-gray-500 hover:text-gray-800 underline"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  )
}
