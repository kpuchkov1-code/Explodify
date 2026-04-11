# Explodify

**Explodify** turns any CAD assembly file into a photorealistic, market-ready exploded-view animation — automatically.

> Built at the **[Tech: Europe] London AI Hackathon 2026**

---

## The Idea

Product teams spend thousands on Blender artists to produce exploded-view ads for hardware products. Explodify eliminates that bottleneck: upload a `.step` / `.glb` / `.obj` file, choose your orientation, and receive studio-grade animated keyframes in minutes.

The key insight is a **geometric-first** approach: rather than asking an AI to "guess" how parts come apart, we use Trimesh to compute mathematically correct explosion vectors and a user-confirmed viewing angle, then use those precise snapshots as anchors for AI stylization and video interpolation. The AI never has to invent geometry it cannot see.

---

## Pipeline

```
CAD file (.step / .glb / .obj / .stl / .ply / .3mf)
    │
    ▼
Orientation Preview  (POST /preview)
    │  • Load assembly; render 6 orthographic screenshots
    │    (front / back / left / right / top / bottom)
    │  • Return base64 PNGs + preview_id (file cached server-side)
    │  • User selects the "front" face and corrects roll (0°/90°/180°/270°)
    ▼
Phase 1: Geometric Analysis  (Trimesh + cascadio)
    │  • Load assembly; identify individual mesh components
    │  • Reorient: rotate longest axis to vertical (Y-up)
    │  • Compute global centroid; per-component explosion vectors:
    │      v⃗ = centroid_component − centroid_assembly × scalar
    ▼
Phase 2: Structural Snapshots  (pyrender)
    │  • Camera placed along user-selected face direction
    │  • Camera up-vector rotated by user roll offset (Rodrigues rotation)
    │  • Camera distance based on 2D view-plane footprint (correct zoom for any aspect ratio)
    │  • Export 5 clean PNG frames at 0° orbit with 10° incremental orbit per step:
    │      Frame A (0%   explosion, 0°  camera) — assembled
    │      Frame B (25%  explosion, 10° camera)
    │      Frame C (50%  explosion, 20° camera) — mid-explode
    │      Frame D (75%  explosion, 30° camera)
    │      Frame E (100% explosion, 40° camera) — fully exploded
    ▼
Output: 5 raw PNG keyframes served via GET /jobs/{id}/frames/{frame_name}

── Phases 3 & 4 (planned) ──────────────────────────────────────────────────
Phase 3: AI Stylization  (Gemini Flash — Google Deepmind)
    │  • Image-to-image: photorealistic product render preserving exact geometry
    ▼
Phase 4: Video Synthesis  (fal.ai Kling v2)
    │  • Keyframe-anchored interpolation across all 5 frames → 4 stitched clips
    ▼
Output: studio-grade exploded-view animation (.mp4)
```

---

## Supported Input Formats

### What works well

| Format | How to export | Why it works |
|--------|--------------|--------------|
| **STEP / STP** | SolidWorks: *File → Save As → STEP AP214*, tick **Export as assembly**<br>Fusion 360: *File → Export → STEP*, ensure components are not merged<br>Onshape: *Export → STEP*, select *Export each part as a separate body* | Preserves named assembly components when exported correctly |
| **GLB / GLTF** | Blender: *File → Export → glTF 2.0*<br>Fusion 360: *File → Export → OBJ or GLB* | Scene graph nodes become individual components |
| **OBJ + MTL** | Tinkercad: *Export → OBJ*<br>Blender: *File → Export → Wavefront OBJ* | Material groups become components; MTL colors are preserved |
| **STL** | Any CAD tool: *File → Save As → STL* | Single mesh only — best for simple parts |
| **PLY / 3MF** | Blender, MeshLab | Supported, single mesh |

### What does NOT work

| Situation | Error | Fix |
|-----------|-------|-----|
| STEP exported as a single solid (no assembly tree) | `>100 components` error | Re-export with assembly structure enabled |
| Proprietary formats (`.sldasm`, `.sldprt`, `.f3d`, `.ipt`) | Unsupported format error | Export to STEP or GLB from your CAD tool |
| More than 100 components after loading | `>100 components` error | File was tessellated per-face; re-export with assembly structure |

### Ideal input checklist

- [ ] File is STEP, GLB, or OBJ
- [ ] Assembly has **2–50 distinct parts** (not faces/surfaces)
- [ ] Each part is a separate mesh node or material group
- [ ] File size under ~50 MB

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/preview/sample` | Render 6 orientation views of the bundled sample model |
| `POST` | `/preview` | Upload a CAD file; receive 6 face screenshots + `preview_id` |
| `POST` | `/jobs` | Create explode job from `preview_id` + `master_angle` + `rotation_offset_deg` |
| `GET` | `/jobs/{id}` | Poll job status (queued / running / done / error) |
| `GET` | `/jobs/{id}/frames/{name}` | Fetch a rendered keyframe PNG (`frame_a` … `frame_e`) |

### POST /preview

```json
// Response
{
  "preview_id": "uuid",
  "images": {
    "front": "data:image/png;base64,...",
    "back":  "data:image/png;base64,...",
    "left":  "data:image/png;base64,...",
    "right": "data:image/png;base64,...",
    "top":   "data:image/png;base64,...",
    "bottom":"data:image/png;base64,..."
  }
}
```

### POST /jobs

```
Form fields:
  preview_id         string   (from /preview — file reused, no re-upload)
  master_angle       string   front | back | left | right | top | bottom
  rotation_offset_deg float   0 | 90 | 180 | 270  (camera roll correction)
  explode_scalar     float    default 1.5
  style_prompt       string   optional aesthetic hint (for future Phase 3)
```

---

## Why This Works

| Problem | Solution |
|---------|----------|
| AI invents geometry it cannot see | Trimesh snapshots anchor AI to exact views at 0–100% |
| Wrong viewing angle for consumer POV | User manually confirms orientation before rendering begins |
| Camera path is inconsistent | Rodrigues rotation applies user roll to camera up-vector exactly |
| Model exported sideways | Longest-axis reorientation aligns the assembly upright before rendering |
| Stylized frames drift visually | Single seed prompt used consistently across all 5 keyframes |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| STEP loading | [cascadio](https://github.com/OpenCASCADE/cascadio) (OpenCASCADE) | STEP → GLB conversion preserving assembly structure |
| Geometry | [Trimesh](https://trimesh.org/) | Assembly analysis, explosion vectors, ray-casting |
| Rendering | [pyrender](https://pyrender.readthedocs.io/) | Headless PNG snapshot export (orientation preview + keyframes) |
| Backend | Python 3.11 + FastAPI | Pipeline orchestration, job queue, file serving |
| AI Stylization *(planned)* | Gemini Flash (Google Deepmind) | Image-to-image photorealistic render |
| Video Synthesis *(planned)* | fal.ai Kling v2 | Keyframe-anchored video interpolation |

---

## Quickstart

```bash
git clone https://github.com/kpuchkov1-code/Explodify.git
cd Explodify
pip install -r requirements.txt

# Run the backend
PYTHONPATH=. uvicorn backend.main:app --port 8000

# Render 6 orientation previews for a file
curl -X POST http://localhost:8000/preview \
  -F "file=@your_assembly.obj" | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
print('preview_id:', d['preview_id'])
for face, uri in d['images'].items():
    open(f'preview_{face}.png', 'wb').write(base64.b64decode(uri.split(',')[1]))
print('Saved 6 face PNGs')
"

# Create a job from the preview (pick master_angle from your preferred face)
curl -X POST http://localhost:8000/jobs \
  -F "preview_id=<preview_id>" \
  -F "master_angle=front" \
  -F "rotation_offset_deg=0" \
  -F "explode_scalar=1.5"

# Poll status
curl http://localhost:8000/jobs/<job_id>

# Fetch keyframes when done
for frame in frame_a frame_b frame_c frame_d frame_e; do
  curl -o "${frame}.png" http://localhost:8000/jobs/<job_id>/frames/$frame
done
```

### CLI (phases 1 & 2 only)

```bash
python explodify.py --input your_assembly.step --explode 1.5
```

Output frames are written to `output/frames/` by default.

---

## Environment Variables

```env
GOOGLE_API_KEY=...       # Gemini Flash (Phase 3 stylization — not yet active)
FAL_KEY=...              # fal.ai video synthesis (Phase 4 — not yet active)
```

Copy `.env.example` to `.env`. Phases 1 & 2 run without any API keys.

---

## Roadmap

### v0.1 — Hackathon MVP (current)

- [x] Phase 1: Trimesh geometric analysis (explosion vectors)
- [x] Phase 1: STEP loading via cascadio (preserves named assembly components)
- [x] Phase 1: Automatic upright reorientation (longest-axis alignment)
- [x] Phase 2: pyrender snapshot export — **5 PNG keyframes** at 0/25/50/75/100% explosion
- [x] Phase 2: MTL material color extraction (OBJ/MTL diffuse → pyrender material)
- [x] Phase 2: View-plane footprint camera (correct zoom for any aspect ratio)
- [x] Phase 2: Camera up-vector rotation (Rodrigues) for user roll correction
- [x] Orientation preview: 6-face orthographic screenshots before pipeline starts
- [x] FastAPI backend: `/preview`, `/jobs`, `/jobs/{id}/frames/{name}` endpoints
- [x] Manual orientation selection: user picks front face + roll offset before rendering

### v0.2 — AI Stylization & Video

- [ ] Phase 3: Gemini Flash image-to-image stylization (5 frames)
- [ ] Phase 4: fal.ai Kling v2 video synthesis (4 interpolated clips → stitched MP4)
- [ ] Serve final MP4 via `/jobs/{id}/video`
- [ ] Style prompt editor in web UI

### v0.3 — Production

- [ ] Per-component material assignment (metal vs. plastic detection)
- [ ] Brand overlay (logo, color grading) post-processing pass
- [ ] Batch processing for product catalogues
- [ ] User accounts + job history
- [ ] Webhook delivery of finished MP4
- [ ] API for headless integration (CI/CD for product teams)

---

## Project Structure

```
Explodify/
├── explodify.py                  # CLI entry point (phases 1 & 2)
├── requirements.txt
├── README.md
├── .env.example                  # API key template
├── pipeline/
│   ├── models.py                 # Shared dataclasses: NamedMesh, FrameSet, PipelineMetadata
│   ├── format_loader.py          # Multi-format loader (STEP via cascadio, GLB/OBJ/STL via trimesh)
│   ├── phase1_geometry.py        # Trimesh: reorient, explosion vectors
│   ├── phase2_snapshots.py       # pyrender: 5 PNG keyframes + orientation preview frame renderer
│   └── orientation_preview.py   # 6-face orthographic preview renderer (used by /preview endpoint)
├── tests/
│   ├── backend/
│   │   └── test_api.py           # FastAPI endpoint tests
│   └── pipeline/
│       ├── conftest.py           # Shared fixtures (two-box GLB assembly)
│       ├── test_format_loader.py
│       ├── test_phase1_geometry.py
│       ├── test_phase2_snapshots.py
│       ├── test_orientation_preview.py
│       └── test_integration_phase1_2.py
└── backend/
    ├── main.py                   # FastAPI app: /preview, /jobs, /jobs/{id}/frames/{name}
    ├── jobs.py                   # In-memory job store
    └── models.py                 # Pydantic job/status models
```

---

## Partner Technologies

| Partner | Usage | Hackathon Prize Track |
|---------|-------|----------------------|
| **Google Deepmind / Gemini Flash** | Phase 3 image stylization *(planned)* | Gemini Credits |
| **fal.ai** | Phase 4 video synthesis *(planned)* | Best use of fal ($1000 USD credits) |

Hackathon voucher code for fal.ai: `techeurope-london`

---

## Hackathon

**Event:** Tech: Europe London AI Hackathon | April 2026
**Track:** Open Innovation + Best Use of fal.ai side challenge
**Submission:** 2-minute Loom demo + this public repo

---

## License

MIT
