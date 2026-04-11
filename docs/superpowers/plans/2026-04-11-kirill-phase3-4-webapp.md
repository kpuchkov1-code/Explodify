# Explodify — Phase 3 & 4 Implementation Plan (Kirill)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 3 (Gemini Flash image stylization) and Phase 4 (fal.ai video synthesis), then wire them back into the existing FastAPI backend.

**Architecture:** Phases 1 & 2 are complete and merged. The backend (`backend/main.py`) already runs the full pipeline as async jobs and serves 5 raw PNG keyframes. Phase 3 and 4 were removed from the codebase until API keys are wired — they need to be re-added as `pipeline/phase3_stylize.py` and `pipeline/phase4_video.py`, then re-wired at the marked `# Phases 3 & 4 (planned)` comment in `backend/main.py`.

**Tech Stack:** Python 3.11, google-genai>=1.0, fal-client>=0.4

**Read first:** `docs/superpowers/plans/2026-04-11-interface-contract.md`

---

## IMPORTANT: FrameSet Has 5 Frames (Not 3)

The original plan referenced `frame_a`, `frame_b`, `frame_c`. The actual implementation produces **5 frames**:

```python
@dataclass
class FrameSet:
    frame_a: Path   # 0%   explosion, 0°  camera orbit
    frame_b: Path   # 25%  explosion, 10° camera orbit
    frame_c: Path   # 50%  explosion, 20° camera orbit
    frame_d: Path   # 75%  explosion, 30° camera orbit
    frame_e: Path   # 100% explosion, 40° camera orbit
    metadata: PipelineMetadata
```

All Phase 3 and Phase 4 code must process all 5 frames (`frame_a` through `frame_e`).

---

## What's Already Built

The backend is fully wired. You do NOT need to create or modify:

| File | Status |
|------|--------|
| `backend/main.py` | Done — `/preview`, `/jobs`, `/jobs/{id}`, `/jobs/{id}/frames/{name}` |
| `backend/jobs.py` | Done — in-memory job store with phase tracking |
| `backend/models.py` | Done — `JobStatus`, `PhaseStatus` |
| `pipeline/models.py` | Done — `FrameSet` (5 frames), `PipelineMetadata`, `NamedMesh` |
| `pipeline/phase1_geometry.py` | Done |
| `pipeline/phase2_snapshots.py` | Done |
| `pipeline/orientation_preview.py` | Done |

### Where to re-wire Phase 3 & 4

In `backend/main.py`, find:

```python
# Phases 3 & 4 (planned)
# stylized = GeminiStylizer(api_key=...).stylize(frame_set, ...)
# video_path = FalVideoSynth().synthesize(stylized, ...)
jobs.mark_done(job_id, None)
```

Replace with real calls once the modules exist.

---

## Prerequisites

```bash
pip install google-genai fal-client
```

Add to `requirements.txt`:

```
google-genai>=1.0.0
fal-client>=0.4.0
```

Set env vars (do NOT commit):

```
GOOGLE_API_KEY=your_actual_gemini_key
FAL_KEY=your_actual_fal_key
```

---

## Task 1: Phase 3 — Gemini Flash Stylization

**Files to create:**
- `pipeline/phase3_stylize.py`
- `tests/pipeline/test_phase3_stylize.py`

### Step 1: Write failing tests

```python
# tests/pipeline/test_phase3_stylize.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pipeline.phase3_stylize import GeminiStylizer
from pipeline.models import FrameSet, PipelineMetadata
from PIL import Image
import io


@pytest.fixture
def mock_frame_set(tmp_path):
    """FrameSet with real (blank white) PNGs for testing."""
    for name in ("frame_a.png", "frame_b.png", "frame_c.png", "frame_d.png", "frame_e.png"):
        Image.new("RGB", (256, 256), color=(200, 200, 200)).save(tmp_path / name)
    return FrameSet(
        frame_a=tmp_path / "frame_a.png",
        frame_b=tmp_path / "frame_b.png",
        frame_c=tmp_path / "frame_c.png",
        frame_d=tmp_path / "frame_d.png",
        frame_e=tmp_path / "frame_e.png",
        metadata=PipelineMetadata(
            master_angle="front",
            explosion_scalar=1.5,
            component_count=2,
            camera_angles_deg=[0.0, 10.0, 20.0, 30.0, 40.0],
        ),
    )


@pytest.fixture
def fake_gemini_response():
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), color=(240, 240, 240)).save(buf, format="PNG")
    part = MagicMock()
    part.inline_data.data = buf.getvalue()
    part.inline_data.mime_type = "image/png"
    response = MagicMock()
    response.candidates[0].content.parts = [part]
    return response


def test_stylize_returns_frame_set_with_five_pngs(mock_frame_set, tmp_path, fake_gemini_response):
    with patch("pipeline.phase3_stylize.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_gemini_response

        stylizer = GeminiStylizer(api_key="fake_key")
        result = stylizer.stylize(mock_frame_set, output_dir=tmp_path / "stylized")

    assert isinstance(result, FrameSet)
    for attr in ("frame_a", "frame_b", "frame_c", "frame_d", "frame_e"):
        assert getattr(result, attr).exists(), f"{attr} missing"


def test_stylize_calls_gemini_five_times(mock_frame_set, tmp_path, fake_gemini_response):
    """One Gemini call per frame — 5 total."""
    with patch("pipeline.phase3_stylize.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_gemini_response

        GeminiStylizer(api_key="fake_key").stylize(mock_frame_set, output_dir=tmp_path / "s")

    assert mock_client.models.generate_content.call_count == 5


def test_stylize_uses_custom_style_prompt(mock_frame_set, tmp_path, fake_gemini_response):
    mock_frame_set.metadata.style_prompt = "Neon cyberpunk aesthetic, glowing edges"

    with patch("pipeline.phase3_stylize.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_gemini_response

        GeminiStylizer(api_key="fake_key").stylize(mock_frame_set, output_dir=tmp_path / "s")

    call_args = mock_client.models.generate_content.call_args_list[0]
    contents = call_args.kwargs.get("contents") or call_args[1]["contents"]
    prompt_text = next(p.text for p in contents if hasattr(p, "text"))
    assert "Neon cyberpunk" in prompt_text
    assert "Preserve the exact structure" in prompt_text


def test_stylize_preserves_metadata(mock_frame_set, tmp_path, fake_gemini_response):
    with patch("pipeline.phase3_stylize.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_gemini_response

        result = GeminiStylizer(api_key="fake_key").stylize(mock_frame_set, output_dir=tmp_path / "s")

    assert result.metadata.master_angle == "front"
    assert result.metadata.component_count == 2
```

### Step 2: Run to verify failure

```bash
pytest tests/pipeline/test_phase3_stylize.py -v
```

Expected: FAIL with `ModuleNotFoundError`

### Step 3: Implement `GeminiStylizer`

```python
# pipeline/phase3_stylize.py
import io
import os
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from pipeline.models import FrameSet

DEFAULT_STYLE_PROMPT = (
    "High-end industrial design render, Blender Cycles quality, "
    "dramatic studio lighting with soft shadows, brushed aluminum and polycarbonate materials, "
    "pure white background, photorealistic product photography style."
)

STRUCTURAL_CONSTRAINT = (
    "Preserve the exact structure, layout, and positions of all components. "
    "Do not add, remove, or rearrange parts."
)

MODEL = "gemini-2.0-flash-preview-image-generation"

FRAME_ATTRS = ("frame_a", "frame_b", "frame_c", "frame_d", "frame_e")


def _build_prompt(style_prompt: str) -> str:
    aesthetic = style_prompt.strip() if style_prompt.strip() else DEFAULT_STYLE_PROMPT
    return f"Transform this 3D render. {STRUCTURAL_CONSTRAINT} {aesthetic}"


class GeminiStylizer:
    """Phase 3: Stylize 5 raw PNG snapshots via Gemini Flash image-to-image."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ["GOOGLE_API_KEY"]
        self._client = genai.Client(api_key=self._api_key)

    def stylize(self, frame_set: FrameSet, output_dir: Path) -> FrameSet:
        """Apply Gemini stylization to all 5 frames.

        Args:
            frame_set: Raw FrameSet from Phase 2.
            output_dir: Directory to write stylized PNGs.

        Returns:
            New FrameSet pointing to stylized PNGs, same metadata.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        prompt = _build_prompt(frame_set.metadata.style_prompt)
        output_paths = {}

        for attr in FRAME_ATTRS:
            src = getattr(frame_set, attr)
            out = output_dir / f"{attr}.png"
            self._stylize_single(src, prompt).save(str(out))
            output_paths[attr] = out

        return FrameSet(**output_paths, metadata=frame_set.metadata)

    def _stylize_single(self, frame_path: Path, prompt: str) -> Image.Image:
        with open(frame_path, "rb") as f:
            image_bytes = f.read()

        response = self._client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                types.Part.from_text(prompt),
            ],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and "image" in part.inline_data.mime_type:
                return Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")

        raise RuntimeError(f"Gemini returned no image for {frame_path.name}")
```

### Step 4: Run tests

```bash
pytest tests/pipeline/test_phase3_stylize.py -v
```

Expected: 4 PASSED

### Step 5: Commit

```bash
git add pipeline/phase3_stylize.py tests/pipeline/test_phase3_stylize.py
git commit -m "feat: GeminiStylizer — Gemini Flash stylization for all 5 keyframes"
```

---

## Task 2: Phase 4 — fal.ai Video Synthesis

**Files to create:**
- `pipeline/phase4_video.py`
- `tests/pipeline/test_phase4_video.py`

`★ Insight ─────────────────────────────────────`
fal.ai Kling v2 takes a start and end image per clip. With 5 frames we generate 4 clips (A→B, B→C, C→D, D→E) then stitch them. Each clip is 5 seconds → ~20s total.
`─────────────────────────────────────────────────`

### Step 1: Write failing tests

```python
# tests/pipeline/test_phase4_video.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pipeline.phase4_video import FalVideoSynth
from pipeline.models import FrameSet, PipelineMetadata
from PIL import Image


@pytest.fixture
def stylized_frame_set(tmp_path):
    for name in ("frame_a.png", "frame_b.png", "frame_c.png", "frame_d.png", "frame_e.png"):
        Image.new("RGB", (256, 256), color=(200, 200, 200)).save(tmp_path / name)
    return FrameSet(
        frame_a=tmp_path / "frame_a.png",
        frame_b=tmp_path / "frame_b.png",
        frame_c=tmp_path / "frame_c.png",
        frame_d=tmp_path / "frame_d.png",
        frame_e=tmp_path / "frame_e.png",
        metadata=PipelineMetadata(
            master_angle="front",
            explosion_scalar=1.5,
            component_count=2,
            camera_angles_deg=[0.0, 10.0, 20.0, 30.0, 40.0],
        ),
    )


def test_synthesize_produces_mp4(stylized_frame_set, tmp_path):
    output_path = tmp_path / "output.mp4"

    with patch("pipeline.phase4_video.fal_client") as mock_fal:
        mock_fal.subscribe.return_value = {"video": {"url": "https://fake.fal.ai/clip.mp4"}}
        with patch("pipeline.phase4_video.requests") as mock_requests:
            mock_resp = MagicMock()
            mock_resp.content = b"\x00" * 1024
            mock_requests.get.return_value = mock_resp

            result = FalVideoSynth(fal_key="fake_key").synthesize(stylized_frame_set, output_path)

    assert result == output_path
    assert output_path.exists()


def test_synthesize_calls_fal_four_times(stylized_frame_set, tmp_path):
    """Four fal.ai calls: A→B, B→C, C→D, D→E."""
    output_path = tmp_path / "output.mp4"

    with patch("pipeline.phase4_video.fal_client") as mock_fal:
        mock_fal.subscribe.return_value = {"video": {"url": "https://fake.fal.ai/clip.mp4"}}
        with patch("pipeline.phase4_video.requests") as mock_requests:
            mock_resp = MagicMock()
            mock_resp.content = b"\x00" * 512
            mock_requests.get.return_value = mock_resp

            FalVideoSynth(fal_key="fake_key").synthesize(stylized_frame_set, output_path)

    assert mock_fal.subscribe.call_count == 4
```

### Step 2: Run to verify failure

```bash
pytest tests/pipeline/test_phase4_video.py -v
```

Expected: FAIL with `ModuleNotFoundError`

### Step 3: Implement `FalVideoSynth`

```python
# pipeline/phase4_video.py
import base64
import os
import tempfile
from pathlib import Path

import fal_client
import requests

from pipeline.models import FrameSet

FAL_MODEL = "fal-ai/kling-video/v2/master/image-to-video"
CLIP_DURATION = "5"
DEFAULT_VIDEO_PROMPT = (
    "Smooth product advertisement animation. Parts separate cleanly and gracefully. "
    "Studio lighting. Clean white background."
)

FRAME_ATTRS = ("frame_a", "frame_b", "frame_c", "frame_d", "frame_e")


def _build_prompt(style_prompt: str) -> str:
    motion = "Smooth animation, parts separate cleanly."
    aesthetic = style_prompt.strip() if style_prompt.strip() else DEFAULT_VIDEO_PROMPT
    return f"{motion} {aesthetic}"


def _to_data_uri(path: Path) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{data}"


class FalVideoSynth:
    """Phase 4: Generate video from 5 stylized keyframes via fal.ai Kling v2."""

    def __init__(self, fal_key: str | None = None):
        key = fal_key or os.environ.get("FAL_KEY", "")
        os.environ["FAL_KEY"] = key

    def synthesize(self, stylized: FrameSet, output_path: Path) -> Path:
        """Generate 4 video clips (consecutive frame pairs) and stitch into one MP4.

        Args:
            stylized: FrameSet from GeminiStylizer.stylize().
            output_path: Path to write the final .mp4.

        Returns:
            output_path after writing.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        frames = [getattr(stylized, attr) for attr in FRAME_ATTRS]
        video_prompt = _build_prompt(stylized.metadata.style_prompt)

        clip_paths = []
        for i in range(len(frames) - 1):
            clip_bytes = self._generate_clip(
                _to_data_uri(frames[i]),
                _to_data_uri(frames[i + 1]),
                video_prompt,
            )
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp.write(clip_bytes)
                clip_paths.append(Path(tmp.name))

        self._stitch(clip_paths, output_path)
        return output_path

    def _generate_clip(self, start_uri: str, end_uri: str, prompt: str) -> bytes:
        result = fal_client.subscribe(
            FAL_MODEL,
            arguments={
                "prompt": prompt,
                "image_url": start_uri,
                "tail_image_url": end_uri,
                "duration": CLIP_DURATION,
            },
        )
        clip_url = result["video"]["url"]
        return requests.get(clip_url).content

    def _stitch(self, clip_paths: list[Path], output_path: Path) -> None:
        """Concatenate MP4 clips via ffmpeg concat demuxer."""
        import subprocess, tempfile as tf

        list_file = tf.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        for p in clip_paths:
            list_file.write(f"file '{p}'\n")
        list_file.close()

        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file.name, "-c", "copy", str(output_path),
            ],
            check=True,
            capture_output=True,
        )
```

### Step 4: Run tests

```bash
pytest tests/pipeline/test_phase4_video.py -v
```

Expected: 2 PASSED

### Step 5: Commit

```bash
git add pipeline/phase4_video.py tests/pipeline/test_phase4_video.py
git commit -m "feat: FalVideoSynth — fal.ai Kling v2 video synthesis from 5 keyframes"
```

---

## Task 3: Wire Phase 3 & 4 into the Backend

**File to modify:** `backend/main.py`

Find the placeholder comment inside `_run_pipeline`:

```python
# Phases 3 & 4 (planned)
# stylized = GeminiStylizer(api_key=...).stylize(frame_set, ...)
# video_path = FalVideoSynth().synthesize(stylized, ...)
jobs.mark_done(job_id, None)
```

Replace with:

```python
# Phase 3: AI stylization
jobs.update_phase(job_id, 3, "running")
stylized_dir = upload_dir / "stylized"
stylized = GeminiStylizer().stylize(frame_set, output_dir=stylized_dir)
jobs.update_phase(job_id, 3, "done")

# Phase 4: Video synthesis
jobs.update_phase(job_id, 4, "running")
video_path = FalVideoSynth().synthesize(stylized, upload_dir / "output.mp4")
jobs.mark_done(job_id, video_path)
```

Also add a `GET /jobs/{job_id}/video` endpoint to serve the final MP4:

```python
@app.get("/jobs/{job_id}/video")
async def get_video(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "done":
        raise HTTPException(400, "Job not done yet")
    video = jobs.get_video_path(job_id)
    if not video or not video.exists():
        raise HTTPException(404, "Video not found")
    return FileResponse(str(video), media_type="video/mp4")
```

You'll also need to restore `video_url` in `backend/models.py` and `_video_paths` + `get_video_path()` in `backend/jobs.py` — these were removed during the Phase 1/2 cleanup.

### Commit

```bash
git add backend/main.py backend/jobs.py backend/models.py
git commit -m "feat: wire phase 3 and 4 into backend pipeline"
```

---

## Task 4: Update Frontend

The React frontend is in `frontend/`. It already has:
- `OrientationPicker` — face selection before pipeline start
- `FramesPreview` — 5 raw keyframe thumbnails
- Phase progress tracking

Add:
- Style prompt textarea (send `style_prompt` in the `POST /jobs` form)
- Video player in a new `VideoPreview` component (poll `/jobs/{id}/video` after `status === 'done'`)

No new endpoints or data models needed — the `style_prompt` field is already threaded through `PipelineMetadata`.

---

## Running Everything

```bash
# Backend
PYTHONPATH=. uvicorn backend.main:app --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev
```

The frontend dev server proxies `/preview`, `/jobs`, and `/health` to port 8000 via `vite.config.ts`.
