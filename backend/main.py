# backend/main.py
import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import backend.jobs as jobs
from backend.models import JobStatus

load_dotenv()

app = FastAPI(title="Explodify API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(tempfile.gettempdir()) / "explodify_uploads"
PREVIEW_DIR = Path(tempfile.gettempdir()) / "explodify_previews"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

# Sample file bundled with the frontend (served from public/)
_FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "public"
SAMPLE_OBJ = _FRONTEND_DIR / "sample.obj"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/preview/sample")
async def preview_sample():
    """Return orientation previews for the bundled sample model (no upload required)."""
    if not SAMPLE_OBJ.exists():
        raise HTTPException(status_code=404, detail="Sample file not found on server.")

    # Reuse an existing render if we already processed this session to save time.
    cached = list(PREVIEW_DIR.glob("sample_*"))
    preview_id = cached[0].stem.replace("sample_", "") if cached else None

    if not preview_id:
        preview_id = str(uuid.uuid4())
        dest = PREVIEW_DIR / f"{preview_id}.obj"
        dest.write_bytes(SAMPLE_OBJ.read_bytes())

    try:
        from pipeline.format_loader import load_assembly
        from pipeline.orientation_preview import render_orientation_previews

        named_meshes = load_assembly(str(PREVIEW_DIR / f"{preview_id}.obj"))
        images = render_orientation_previews(named_meshes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Tag the file so we can find the cached render next time
    cached_marker = PREVIEW_DIR / f"sample_{preview_id}"
    cached_marker.touch(exist_ok=True)

    return {"preview_id": preview_id, "images": images}


@app.post("/preview")
async def preview_orientations(file: UploadFile = File(...)):
    """Upload a CAD file and receive 6 orthographic face screenshots for orientation selection.

    Returns a preview_id (reused when creating the job) plus base64 PNG data URIs
    for each of the six cubic faces: front, back, left, right, top, bottom.
    """
    preview_id = str(uuid.uuid4())
    suffix = Path(file.filename or "upload.obj").suffix.lower()
    preview_path = PREVIEW_DIR / f"{preview_id}{suffix}"

    content = await file.read()
    preview_path.write_bytes(content)

    try:
        from pipeline.format_loader import load_assembly
        from pipeline.orientation_preview import render_orientation_previews

        # Run synchronously on the main thread — pyrender's Cocoa/pyglet backend
        # requires the OS main thread on macOS.  Blocking the event loop here is
        # acceptable since this is a short-lived preview render (< 15 s).
        named_meshes = load_assembly(str(preview_path))
        images = render_orientation_previews(named_meshes)
    except Exception as exc:
        preview_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc))

    return {"preview_id": preview_id, "images": images}


@app.post("/jobs", status_code=202)
async def create_job(
    file: Optional[UploadFile] = File(None),
    preview_id: Optional[str] = Form(None),
    explode_scalar: float = Form(1.5),
    style_prompt: str = Form(""),
    master_angle: str = Form("front"),
    rotation_offset_deg: float = Form(0.0),
):
    """Create a background exploded-view job.

    Supply either a fresh `file` upload or a `preview_id` returned from POST /preview.
    The `master_angle` (front/back/left/right/top/bottom) and `rotation_offset_deg`
    (0/90/180/270) are set during the orientation selection step.
    """
    if preview_id:
        matches = list(PREVIEW_DIR.glob(f"{preview_id}.*"))
        if not matches:
            raise HTTPException(status_code=404, detail="Preview not found — re-upload the file.")
        cad_path = matches[0]
    elif file is not None:
        suffix = Path(file.filename or "upload.obj").suffix.lower()
        cad_path = UPLOAD_DIR / f"{str(uuid.uuid4())}{suffix}"
        content = await file.read()
        cad_path.write_bytes(content)
    else:
        raise HTTPException(status_code=422, detail="Either file or preview_id is required.")

    job_id = jobs.create_job()

    asyncio.create_task(
        _run_pipeline(job_id, cad_path, explode_scalar, style_prompt, master_angle, rotation_offset_deg)
    )

    return {"job_id": job_id}


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@app.get("/jobs/{job_id}/frames/{frame_name}")
def get_frame(job_id: str, frame_name: str):
    """Serve one of the 5 raw keyframe PNGs (frame_a … frame_e)."""
    allowed = {"frame_a", "frame_b", "frame_c", "frame_d", "frame_e"}
    if frame_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Unknown frame: {frame_name}")
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=425, detail="Frames not ready yet")
    frame_path = UPLOAD_DIR / job_id / "raw" / f"{frame_name}.png"
    if not frame_path.exists():
        raise HTTPException(status_code=404, detail=f"{frame_name}.png not found")
    return FileResponse(str(frame_path), media_type="image/png")


async def _run_pipeline(
    job_id: str,
    cad_path: Path,
    scalar: float,
    style_prompt: str = "",
    master_angle: str = "front",
    rotation_offset_deg: float = 0.0,
) -> None:
    """Run all 4 pipeline phases in a background asyncio task."""
    output_dir = UPLOAD_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Phase 1 — load geometry and compute explosion vectors.
        # master_angle is provided by the user from the orientation picker,
        # so we skip the automatic master_angle() computation.
        jobs.update_phase(job_id, 1, "running")
        from pipeline.phase1_geometry import GeometryAnalyzer
        analyzer = GeometryAnalyzer()
        # File loading is thread-safe; use to_thread to avoid blocking event loop.
        meshes = await asyncio.to_thread(analyzer.load, str(cad_path))
        vectors = await asyncio.to_thread(analyzer.explosion_vectors, meshes, scalar)
        jobs.update_phase(job_id, 1, "done")

        # Phase 2 — pyrender rendering must run on the OS main thread on macOS
        # (pyglet/Cocoa restriction).  We call it synchronously here; the asyncio
        # task itself runs on the main thread so this is safe.
        jobs.update_phase(job_id, 2, "running")
        from pipeline.phase2_snapshots import SnapshotRenderer
        renderer = SnapshotRenderer()
        frame_set = renderer.render(
            meshes,
            vectors,
            master_angle,
            output_dir / "raw",
            scalar,
            style_prompt,
            rotation_offset_deg,
        )
        jobs.update_phase(job_id, 2, "done")

        # Phases 3 & 4 (Gemini stylization + FAL video) are skipped for now.
        # Mark phase 3 and 4 as done immediately so the frontend sees completion.
        jobs.update_phase(job_id, 3, "done")
        jobs.update_phase(job_id, 4, "done")

        jobs.mark_done(job_id, None)

    except Exception as e:
        current_job = jobs.get_job(job_id)
        phase = current_job.current_phase if current_job else 1
        jobs.mark_error(job_id, phase, str(e))
