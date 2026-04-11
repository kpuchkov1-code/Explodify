# Explodify — Phase 1 & 2 Implementation Plan (Collaborator)

**Status: COMPLETE**

All tasks below have been implemented and merged to `main`. The pipeline produces 5 PNG keyframes from any supported CAD file, with user-selected orientation and roll correction applied before rendering.

---

## What Was Built

### Phase 1: Geometric Analysis (`pipeline/phase1_geometry.py`)

`GeometryAnalyzer` class — three methods:

- **`load(path)`** — delegates to `pipeline/format_loader.py`, supports STEP (via cascadio), GLB, OBJ, STL, PLY, 3MF. Returns `List[NamedMesh]`.
- **`reorient(named_meshes)`** — rotates the assembly so its longest bounding-box axis aligns with Y (up). Handles models exported sideways from Tinkercad and similar tools.
- **`explosion_vectors(named_meshes, scalar)`** — computes `v⃗ = (centroid_i − centroid_assembly) × scalar` per component.

> **Note:** `master_angle()` (ray-cast optimal angle) is still present but is no longer called automatically by the pipeline. The user selects orientation via the orientation picker UI (see below). `master_angle()` remains available for headless CLI use.

### Phase 2: Structural Snapshots (`pipeline/phase2_snapshots.py`)

`SnapshotRenderer` class:

- **`render(named_meshes, explosion_vectors, master_angle, output_dir, scalar, source_format, rotation_offset_deg)`**
  - Renders **5 PNG keyframes** at 0/25/50/75/100% explosion
  - Camera orbits 0°→40° across the 5 frames (10° per step)
  - `master_angle` sets the base camera direction (user-selected face)
  - `rotation_offset_deg` rotates the camera up-vector via Rodrigues rotation (corrects model roll)
  - Camera distance based on 2D view-plane footprint, not 3D diagonal
  - Returns `FrameSet` with `frame_a … frame_e` paths

Public helper functions extracted for orientation preview use:
- **`render_preview_frame(meshes, cam_dir, resolution)`** — renders a single frame from an explicit camera direction vector, used by the orientation preview system
- **`_compute_up_vector(cam_dir, rotation_deg)`** — Rodrigues rotation of world-up around the camera direction axis

### Orientation Preview (`pipeline/orientation_preview.py`)

New module — `render_orientation_previews(named_meshes)`:
- Renders 6 orthographic face views (front/back/left/right/top/bottom) at 512×384
- Returns `dict[str, str]` mapping face name → base64 PNG data URI
- Called by `POST /preview` before the user starts the pipeline

---

## Interface Contract

### Input to Phase 1

```python
from pipeline.phase1_geometry import GeometryAnalyzer

analyzer = GeometryAnalyzer()
named_meshes = analyzer.load("assembly.step")     # List[NamedMesh]
vectors = analyzer.explosion_vectors(named_meshes, scalar=1.5)  # dict[int, np.ndarray]
```

### Output of Phase 2 (what Phase 3 will consume)

```python
from pipeline.phase2_snapshots import SnapshotRenderer

renderer = SnapshotRenderer()
frame_set = renderer.render(
    named_meshes,
    vectors,
    master_angle="front",         # user-selected
    output_dir=Path("output/raw"),
    scalar=1.5,
    source_format=".obj",
    rotation_offset_deg=90.0,     # user roll correction (0/90/180/270)
)
# frame_set.frame_a … frame_e: Path to PNG
# frame_set.metadata: PipelineMetadata (master_angle, scalar, component_count, etc.)
```

### FrameSet dataclass (pipeline/models.py)

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

---

## Changes from Original Plan

| Original | Actual |
|----------|--------|
| 3 keyframes (0/50/100%) | **5 keyframes** (0/25/50/75/100%) |
| Automatic `master_angle()` selection | **User picks orientation** via `/preview` endpoint; `master_angle()` overridden |
| No roll correction | **`rotation_offset_deg`** (0/90/180/270°) applied via Rodrigues rotation |
| Phase 3/4 stubs | Phase 3 & 4 files **removed** until API keys wired — pipeline exits cleanly at Phase 2 |
| No orientation preview | **`orientation_preview.py`** added — 6-face screenshots before pipeline starts |

---

## Tests

All tests passing (`pytest tests/ -q` → 35 passed):

| Test file | Coverage |
|-----------|----------|
| `tests/pipeline/test_phase1_geometry.py` | load, reorient, master_angle, explosion_vectors |
| `tests/pipeline/test_phase2_snapshots.py` | render (5 frames), metadata fields, valid PNG output |
| `tests/pipeline/test_orientation_preview.py` | 6 faces returned, valid base64 PNG, distinct images |
| `tests/pipeline/test_integration_phase1_2.py` | end-to-end CAD → FrameSet |
| `tests/pipeline/test_format_loader.py` | format loader for all supported extensions |
| `tests/backend/test_api.py` | /health, /preview (mocked render), /jobs, /jobs/{id} |

---

## Handoff Notes for Phase 3 (Kirill)

Phase 3 consumes a `FrameSet` with 5 frames instead of the originally planned 3. The Gemini stylization call should be applied to all 5 (`frame_a` through `frame_e`). The `metadata.style_prompt` field carries the user's aesthetic prompt through from job creation.

The `master_angle` in metadata reflects the **user-selected** orientation (not auto-detected), so Phase 3 can trust it as the intended front face.

When Phase 3 is ready, re-add `pipeline/phase3_stylize.py` and re-wire in `backend/main.py` at the marked `# Phases 3 & 4 (planned)` comment.
