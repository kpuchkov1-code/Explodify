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

_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

app = FastAPI(title="Explodify API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(tempfile.gettempdir()) / "explodify_uploads"
PREVIEW_DIR = Path(tempfile.gettempdir()) / "explodify_previews"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

VARIANT_NAMES = ("longest", "shortest")


@app.get("/health")
def health():
    return {"status": "ok"}



@app.post("/preview")
async def preview_orientations(file: UploadFile = File(...)):
    preview_id = str(uuid.uuid4())
    suffix = Path(file.filename or "upload.obj").suffix.lower()
    preview_path = PREVIEW_DIR / f"{preview_id}{suffix}"

    content = await file.read()
    preview_path.write_bytes(content)

    try:
        from pipeline.format_loader import load_assembly
        from pipeline.orientation_preview import render_orientation_previews
        from pipeline.phase1_geometry import GeometryAnalyzer

        named_meshes = load_assembly(str(preview_path))
        named_meshes = GeometryAnalyzer().reorient(named_meshes)
        images = render_orientation_previews(named_meshes)
    except Exception as exc:
        preview_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc))

    component_names = [nm.name for nm in named_meshes]
    return {"preview_id": preview_id, "images": images, "component_names": component_names}


@app.post("/jobs", status_code=202)
async def create_job(
    file: Optional[UploadFile] = File(None),
    preview_id: Optional[str] = Form(None),
    explode_scalar: float = Form(1.5),
    style_prompt: str = Form(""),
    component_rows: str = Form("[]"),
    master_angle: str = Form("front"),
    rotation_offset_deg: float = Form(0.0),
    orbit_range_deg: float = Form(40.0),
    camera_zoom: float = Form(1.0),
    variants_to_render: str = Form("longest,shortest"),
):
    if preview_id:
        matches = list(PREVIEW_DIR.glob(f"{preview_id}.*"))
        if not matches:
            raise HTTPException(status_code=404, detail="Preview not found -- re-upload the file.")
        cad_path = matches[0]
    elif file is not None:
        suffix = Path(file.filename or "upload.obj").suffix.lower()
        cad_path = UPLOAD_DIR / f"{str(uuid.uuid4())}{suffix}"
        content = await file.read()
        cad_path.write_bytes(content)
    else:
        raise HTTPException(status_code=422, detail="Either file or preview_id is required.")

    job_id = jobs.create_job()

    parsed_variants = [
        v.strip() for v in variants_to_render.split(",")
        if v.strip() in VARIANT_NAMES
    ] or list(VARIANT_NAMES)

    import json as _json
    try:
        parsed_rows: list[dict] = _json.loads(component_rows)
        if not isinstance(parsed_rows, list):
            parsed_rows = []
    except Exception:
        parsed_rows = []

    asyncio.create_task(
        _run_pipeline(
            job_id, cad_path, explode_scalar,
            rows=parsed_rows,
            style_prompt=style_prompt,
            master_angle=master_angle,
            rotation_offset_deg=rotation_offset_deg,
            orbit_range_deg=orbit_range_deg,
            camera_zoom=camera_zoom,
            variants_to_render=parsed_variants,
        )
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
    allowed = {"frame_a", "frame_b", "frame_c", "frame_d", "frame_e"}
    if frame_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Unknown frame: {frame_name}")
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("running", "awaiting_approval", "done"):
        raise HTTPException(status_code=425, detail="Frames not ready yet")
    frame_path = UPLOAD_DIR / job_id / "raw" / f"{frame_name}.png"
    if not frame_path.exists():
        raise HTTPException(status_code=404, detail=f"{frame_name}.png not found")
    return FileResponse(str(frame_path), media_type="image/png")


@app.post("/jobs/{job_id}/approve", status_code=202)
async def approve_job(
    job_id: str,
    component_rows: Optional[str] = Form(None),
    style_prompt: Optional[str] = Form(None),
    selected_variants: Optional[str] = Form(None),
):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if job.status != "awaiting_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not awaiting approval (status: {job.status})",
        )

    import json as _json
    style_overrides = None
    if component_rows is not None:
        try:
            parsed_override_rows: list[dict] = _json.loads(component_rows)
            if not isinstance(parsed_override_rows, list):
                parsed_override_rows = []
        except Exception:
            parsed_override_rows = []
        style_overrides = {
            "rows": parsed_override_rows,
            "style_prompt": style_prompt or "",
        }

    variants = None
    if selected_variants:
        variants = [v.strip() for v in selected_variants.split(",") if v.strip() in VARIANT_NAMES]

    signalled = jobs.approve_phase4(
        job_id, style_overrides=style_overrides, selected_variants=variants,
    )
    if not signalled:
        raise HTTPException(status_code=409, detail="Approval event already consumed")
    return {"ok": True}


@app.get("/jobs/{job_id}/base_video/{variant}")
def get_base_video_variant(job_id: str, variant: str):
    from backend.models import PhaseStatus
    if variant not in VARIANT_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown variant: {variant}")
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.phases.get(3) != PhaseStatus.done:
        raise HTTPException(status_code=425, detail="Base video not ready yet")
    video_path = UPLOAD_DIR / job_id / f"base_video_{variant}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Base video ({variant}) not found")
    return FileResponse(str(video_path), media_type="video/mp4")


@app.get("/jobs/{job_id}/base_video")
def get_base_video(job_id: str):
    """Legacy endpoint -- serves the longest-axis variant."""
    return get_base_video_variant(job_id, "longest")


@app.get("/jobs/{job_id}/loop_video/{variant}")
def get_loop_video(job_id: str, variant: str):
    if variant not in VARIANT_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown variant: {variant}")
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    path = UPLOAD_DIR / job_id / f"loop_video_{variant}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Loop video not ready")
    return FileResponse(str(path), media_type="video/mp4")


@app.get("/jobs/{job_id}/video/{variant}")
def get_video_variant(job_id: str, variant: str):
    if variant not in VARIANT_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown variant: {variant}")
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("awaiting_approval", "done"):
        raise HTTPException(status_code=425, detail="Video not ready yet")
    video_path = UPLOAD_DIR / job_id / f"final_video_{variant}.mp4"
    if not video_path.exists():
        video_path = UPLOAD_DIR / job_id / f"base_video_{variant}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(str(video_path), media_type="video/mp4")


@app.get("/jobs/{job_id}/video")
def get_video(job_id: str):
    """Legacy endpoint -- serves longest-axis variant."""
    return get_video_variant(job_id, "longest")


@app.post("/jobs/{job_id}/restyle", status_code=202)
async def restyle_job(
    job_id: str,
    component_rows: str = Form("[]"),
    style_prompt: str = Form(""),
    selected_variants: str = Form("longest,shortest"),
):
    source_job = jobs.get_job(job_id)
    if source_job is None:
        raise HTTPException(status_code=404, detail="Source job not found")

    source_dir = UPLOAD_DIR / job_id
    variants = [v.strip() for v in selected_variants.split(",") if v.strip() in VARIANT_NAMES]
    if not variants:
        variants = list(VARIANT_NAMES)

    available = [v for v in variants if (source_dir / f"base_video_{v}.mp4").exists()]
    if not available:
        raise HTTPException(status_code=425, detail="Base video not ready — cannot restyle")

    import json as _json
    try:
        parsed_rows: list[dict] = _json.loads(component_rows)
        if not isinstance(parsed_rows, list):
            parsed_rows = []
    except Exception:
        parsed_rows = []

    new_job_id = jobs.create_job()
    new_dir = UPLOAD_DIR / new_job_id
    new_dir.mkdir(parents=True, exist_ok=True)

    import shutil as _shutil
    for v in available:
        _shutil.copy2(source_dir / f"base_video_{v}.mp4", new_dir / f"base_video_{v}.mp4")

    asyncio.create_task(
        _run_phase4_only(new_job_id, parsed_rows, style_prompt, available)
    )

    return {"job_id": new_job_id}


async def _run_phase4_only(
    job_id: str,
    rows: list[dict],
    style_prompt: str,
    variants: list[str],
) -> None:
    output_dir = UPLOAD_DIR / job_id
    try:
        fal_key = os.environ.get("FAL_KEY", "")
        if not fal_key:
            import logging
            logging.warning("FAL_KEY not set; skipping restyle phase 4")
            jobs.update_phase(job_id, 4, "done")
            jobs.mark_done(job_id, ai_styled=False)
            return

        jobs.update_phase(job_id, 4, "running")
        from pipeline.prompt_interpreter import build_fal_prompt
        from pipeline.phase4_video import KlingVideoEditor

        fal_prompt = build_fal_prompt(rows=rows, style_prompt=style_prompt)
        editor = KlingVideoEditor(fal_key=fal_key)

        style_tasks = [
            editor.edit(
                output_dir / f"base_video_{v}.mp4",
                fal_prompt,
                output_dir / f"final_video_{v}.mp4",
            )
            for v in variants
            if (output_dir / f"base_video_{v}.mp4").exists()
        ]

        if style_tasks:
            await asyncio.gather(*style_tasks)

        jobs.update_phase(job_id, 4, "done")
        jobs.mark_done(job_id, ai_styled=len(style_tasks) > 0)

    except Exception as exc:
        jobs.mark_error(job_id, 4, str(exc))


async def _run_pipeline(
    job_id: str,
    cad_path: Path,
    scalar: float,
    rows: list[dict] | None = None,
    style_prompt: str = "",
    master_angle: str = "front",
    rotation_offset_deg: float = 0.0,
    orbit_range_deg: float = 40.0,
    camera_zoom: float = 1.0,
    variants_to_render: list[str] | None = None,
) -> None:
    _variants = variants_to_render or list(VARIANT_NAMES)
    output_dir = UPLOAD_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # -- Phase 1: geometry -------------------------------------------------
        jobs.update_phase(job_id, 1, "running")
        from pipeline.phase1_geometry import GeometryAnalyzer
        analyzer = GeometryAnalyzer()
        meshes = await asyncio.to_thread(analyzer.load, str(cad_path))
        meshes = analyzer.reorient(meshes)
        longest_vecs, shortest_vecs = await asyncio.to_thread(
            analyzer.dual_axis_explosion_vectors, meshes, scalar,
        )
        jobs.update_phase(job_id, 1, "done")

        # -- Phase 2: render only requested variants (sequential — pyrender
        #    requires the main thread on macOS; no parallelism possible here).
        jobs.update_phase(job_id, 2, "running")
        from pipeline.phase2_snapshots import SnapshotRenderer
        renderer = SnapshotRenderer()

        render_kwargs = dict(
            master_angle=master_angle,
            num_frames=72,
            orbit_range_deg=orbit_range_deg,
            rotation_offset_deg=rotation_offset_deg,
            camera_zoom=camera_zoom,
        )

        variant_vecs = {"longest": longest_vecs, "shortest": shortest_vecs}
        for variant in _variants:
            print(f"[Phase 2] Rendering {variant}-axis variant...")
            renderer.render_video_frames(
                meshes, variant_vecs[variant],
                output_dir=output_dir / f"video_frames_{variant}",
                **render_kwargs,
            )
        jobs.update_phase(job_id, 2, "done")

        # -- Phase 3: assemble requested variants (ffmpeg runs in threads) -----
        jobs.update_phase(job_id, 3, "running")
        from pipeline.phase3_assemble import FrameAssembler
        assembler = FrameAssembler()

        assemble_tasks = [
            asyncio.to_thread(
                assembler.assemble,
                output_dir / f"video_frames_{v}",
                output_dir / f"base_video_{v}.mp4",
            )
            for v in _variants
        ]
        await asyncio.gather(*assemble_tasks)

        loop_tasks = [
            asyncio.to_thread(
                assembler.reverse_and_concat,
                output_dir / f"base_video_{v}.mp4",
                output_dir / f"loop_video_{v}.mp4",
            )
            for v in _variants
        ]
        await asyncio.gather(*loop_tasks)
        jobs.update_phase(job_id, 3, "done")

        # -- Phase 4: Kling styling (user selects which variants) --------------
        approval_event = jobs.mark_awaiting_approval(job_id)
        await approval_event.wait()

        overrides = jobs.get_approval_style(job_id)
        if overrides:
            rows = overrides.get("rows") or rows
            style_prompt = overrides.get("style_prompt", style_prompt)

        selected = jobs.get_approval_variants(job_id)

        fal_key = os.environ.get("FAL_KEY", "")
        if not fal_key:
            import logging
            logging.warning("FAL_KEY not set; skipping Phase 4 Kling edit")
            jobs.update_phase(job_id, 4, "done")
            jobs.mark_done(job_id, ai_styled=False)
            return

        jobs.update_phase(job_id, 4, "running")
        from pipeline.prompt_interpreter import build_fal_prompt
        from pipeline.phase4_video import KlingVideoEditor

        fal_prompt = build_fal_prompt(
            rows=rows,
            style_prompt=style_prompt,
        )

        editor = KlingVideoEditor(fal_key=fal_key)
        style_tasks = []
        for variant in selected:
            base_path = output_dir / f"base_video_{variant}.mp4"
            final_path = output_dir / f"final_video_{variant}.mp4"
            if base_path.exists():
                style_tasks.append(editor.edit(base_path, fal_prompt, final_path))

        if style_tasks:
            await asyncio.gather(*style_tasks)

        jobs.update_phase(job_id, 4, "done")
        jobs.mark_done(job_id, ai_styled=len(style_tasks) > 0)

    except Exception as exc:
        current_job = jobs.get_job(job_id)
        phase = current_job.current_phase if current_job else 1
        jobs.mark_error(job_id, phase, str(exc))
