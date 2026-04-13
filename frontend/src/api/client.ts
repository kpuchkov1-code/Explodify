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

export async function createJob(
  options: {
    previewId: string
    explodeScalar: number
    materialPrompt: string
    stylePrompt: string
    studioLighting: boolean
    darkBackdrop: boolean
    whiteBackdrop: boolean
    warmTone: boolean
    coldTone: boolean
    groundShadow: boolean
    masterAngle: FaceName
    rotationOffsetDeg: number
    orbitRangeDeg: number
    cameraZoom: number
    variantsToRender?: VariantName[]
    componentMaterials?: Record<string, string>
  },
): Promise<string> {
  const form = new FormData()
  form.append('preview_id', options.previewId)
  form.append('explode_scalar', String(options.explodeScalar))
  form.append('material_prompt', options.materialPrompt)
  form.append('style_prompt', options.stylePrompt)
  form.append('studio_lighting', String(options.studioLighting))
  form.append('dark_backdrop', String(options.darkBackdrop))
  form.append('white_backdrop', String(options.whiteBackdrop))
  form.append('warm_tone', String(options.warmTone))
  form.append('cold_tone', String(options.coldTone))
  form.append('ground_shadow', String(options.groundShadow))
  form.append('master_angle', options.masterAngle)
  form.append('rotation_offset_deg', String(options.rotationOffsetDeg))
  form.append('orbit_range_deg', String(options.orbitRangeDeg))
  form.append('camera_zoom', String(options.cameraZoom))
  if (options.variantsToRender) {
    form.append('variants_to_render', options.variantsToRender.join(','))
  }
  if (options.componentMaterials) {
    form.append('component_materials', JSON.stringify(options.componentMaterials))
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

export async function approvePhase4(
  jobId: string,
  selectedVariants: VariantName[],
  styleOpts?: {
    materialPrompt: string
    stylePrompt: string
    studioLighting: boolean
    darkBackdrop: boolean
    whiteBackdrop: boolean
    warmTone: boolean
    coldTone: boolean
    groundShadow: boolean
  },
): Promise<void> {
  const form = new FormData()
  form.append('selected_variants', selectedVariants.join(','))
  if (styleOpts) {
    form.append('material_prompt', styleOpts.materialPrompt)
    form.append('style_prompt', styleOpts.stylePrompt)
    form.append('studio_lighting', String(styleOpts.studioLighting))
    form.append('dark_backdrop', String(styleOpts.darkBackdrop))
    form.append('white_backdrop', String(styleOpts.whiteBackdrop))
    form.append('warm_tone', String(styleOpts.warmTone))
    form.append('cold_tone', String(styleOpts.coldTone))
    form.append('ground_shadow', String(styleOpts.groundShadow))
  }
  const resp = await fetch(`/jobs/${jobId}/approve`, { method: 'POST', body: form })
  if (!resp.ok) throw new Error(`Approval failed: ${resp.statusText}`)
}

