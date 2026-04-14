// frontend/src/api/client.ts

export interface PhaseStatus {
  [phase: number]: 'pending' | 'running' | 'done' | 'error'
}

export interface JobStatus {
  job_id: string
  status: 'queued' | 'running' | 'awaiting_approval' | 'done' | 'error'
  current_phase: number
  current_phase_name: string
  phases: PhaseStatus
  error: string | null
  ai_styled: boolean
  has_dual_variants: boolean
}

export type FaceName =
  | 'front' | 'back' | 'left' | 'right' | 'top' | 'bottom'

export type VariantName = 'longest' | 'shortest'

export interface PreviewResult {
  preview_id: string
  images: Record<FaceName, string>
  component_names: string[]
}

export async function getPreviewImages(file: File): Promise<PreviewResult> {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch('/preview', { method: 'POST', body: form })
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(detail.detail ?? resp.statusText)
  }
  return resp.json()
}

interface Row {
  part: string
  material: string
}

export async function createJob(
  options: {
    previewId: string
    explodeScalar: number
    rows: Row[]
    stylePrompt: string
    masterAngle: FaceName
    rotationOffsetDeg: number
    orbitRangeDeg: number
    cameraZoom: number
    variantsToRender?: VariantName[]
  },
): Promise<string> {
  const form = new FormData()
  form.append('preview_id', options.previewId)
  form.append('explode_scalar', String(options.explodeScalar))
  form.append('component_rows', JSON.stringify(options.rows))
  form.append('style_prompt', options.stylePrompt)
  form.append('master_angle', options.masterAngle)
  form.append('rotation_offset_deg', String(options.rotationOffsetDeg))
  form.append('orbit_range_deg', String(options.orbitRangeDeg))
  form.append('camera_zoom', String(options.cameraZoom))
  if (options.variantsToRender) {
    form.append('variants_to_render', options.variantsToRender.join(','))
  }

  const resp = await fetch('/jobs', { method: 'POST', body: form })
  if (!resp.ok) throw new Error(`Job creation failed: ${resp.statusText}`)
  const data = await resp.json()
  return data.job_id as string
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const resp = await fetch(`/jobs/${jobId}`)
  if (!resp.ok) throw new Error(`Status check failed: ${resp.statusText}`)
  return resp.json()
}

export async function restyleJob(
  sourceJobId: string,
  options: {
    rows: Row[]
    stylePrompt: string
    selectedVariants: VariantName[]
  },
): Promise<string> {
  const form = new FormData()
  form.append('component_rows', JSON.stringify(options.rows))
  form.append('style_prompt', options.stylePrompt)
  form.append('selected_variants', options.selectedVariants.join(','))
  const resp = await fetch(`/jobs/${sourceJobId}/restyle`, { method: 'POST', body: form })
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(detail.detail ?? resp.statusText)
  }
  const data = await resp.json()
  return data.job_id as string
}

export async function approvePhase4(
  jobId: string,
  selectedVariants: VariantName[],
  styleOpts?: {
    rows: Row[]
    stylePrompt: string
  },
): Promise<void> {
  const form = new FormData()
  form.append('selected_variants', selectedVariants.join(','))
  if (styleOpts) {
    form.append('component_rows', JSON.stringify(styleOpts.rows))
    form.append('style_prompt', styleOpts.stylePrompt)
  }
  const resp = await fetch(`/jobs/${jobId}/approve`, { method: 'POST', body: form })
  if (!resp.ok) throw new Error(`Approval failed: ${resp.statusText}`)
}

