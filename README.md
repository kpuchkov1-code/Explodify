# Explodify

**Explodify** turns any CAD assembly file into a photorealistic, market-ready exploded-view animation — automatically.

> Built at the **[Tech: Europe] London AI Hackathon 2026**

---

## The Idea

Product teams spend thousands on Blender artists to produce exploded-view ads for hardware products. Explodify eliminates that bottleneck: upload a `.step` / `.glb` / `.obj` file, receive a studio-grade animated MP4 in minutes.

The key insight is a **geometric-first** approach: rather than asking an AI to "guess" how parts come apart, we use Trimesh to compute the mathematically correct explosion vectors and optimal viewing angle, then use those precise snapshots as anchors for AI stylization and video interpolation. The AI never has to invent geometry it cannot see.

---

## Pipeline (4 Phases)

```
CAD file (.step / .glb / .obj / .stl / .ply / .3mf)
    │
    ▼
Phase 1: Geometric Analysis (Trimesh + cascadio)
    │  • Load assembly; identify individual mesh components
    │  • Reorient: rotate longest axis to vertical (Y-up)
    │  • Ray-cast from 6 cardinal directions (Top/Bottom/Left/Right/Front/Back)
    │    — grid spans the actual per-direction footprint, not a global max
    │  • Select "Master Angle" = direction hitting most unique mesh IDs
    │  • Compute global centroid; per-component explosion vectors:
    │      v⃗ = centroid_component − centroid_assembly
    │  • Apply scalar E to get positions at 50% and 100% explosion
    ▼
Phase 2: Structural Snapshots (pyrender)
    │  • Camera distance based on 2D view-plane footprint (not 3D diagonal)
    │  • Export 3 clean PNG frames:
    │      Frame A (0%  explosion, 0°  camera) — assembled
    │      Frame B (50% explosion, 15° camera) — mid-explode
    │      Frame C (100% explosion, 30° camera) — fully exploded
    ▼
Phase 3: AI Stylization (Gemini Flash — Google Deepmind)
    │  • Feed each PNG into Gemini Flash image_edit
    │  • Seed prompt: "High-end industrial design render, Blender Cycles,
    │    studio lighting, brushed aluminum and polycarbonate materials,
    │    clean white background."
    │  • Output: 3 photorealistic keyframes preserving exact geometry
    ▼
Phase 4: Video Synthesis (fal.ai)
    │  • Upload 3 stylized keyframes to fal.ai video model
    │  • Use Start / Middle / End frame anchoring
    │    (forces AI to respect Trimesh-calculated geometry at 50% mark)
    │  • Export final MP4
    ▼
Output: studio-grade exploded-view animation
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
| STEP exported as a single solid (no assembly tree) | `>100 components` error | Re-export with assembly structure enabled (see table above) |
| Proprietary formats (`.sldasm`, `.sldprt`, `.f3d`, `.ipt`) | Unsupported format error | Export to STEP or GLB from your CAD tool |
| More than 100 components after loading | `>100 components` error | File was tessellated per-face; re-export with assembly structure |

### Ideal input checklist

- [ ] File is STEP, GLB, or OBJ
- [ ] Assembly has **2–50 distinct parts** (not faces/surfaces)
- [ ] Each part is a separate mesh node or material group
- [ ] File size under ~50 MB

---

## Example Output Frames

The pipeline produces 3 keyframes for every input:

| Frame A — Assembled | Frame B — Mid-explode | Frame C — Fully exploded |
|---|---|---|
| 0% explosion, 0° orbit | 50% explosion, 15° orbit | 100% explosion, 30° orbit |

These are fed into Phases 3 and 4 for AI stylization and video synthesis.

---

## Why This Works

| Problem | Solution |
|---------|----------|
| AI invents geometry it cannot see | Trimesh snapshots give it exact views at 0%, 50%, 100% |
| Camera path is inconsistent | We rotate before handing to AI, so it interpolates known views |
| Wrong viewing angle for consumer POV | Ray-casting finds the angle that exposes the most components |
| Model exported sideways | Longest-axis reorientation aligns the assembly upright before rendering |
| Stylized frames drift visually | Single seed prompt used consistently across all 3 keyframes |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| STEP loading | [cascadio](https://github.com/OpenCASCADE/cascadio) (OpenCASCADE) | STEP → GLB conversion preserving assembly structure |
| Geometry | [Trimesh](https://trimesh.org/) | Assembly analysis, explosion vectors, ray-casting |
| Rendering | [pyrender](https://pyrender.readthedocs.io/) | Headless PNG snapshot export |
| AI Stylization | [Gemini Flash](https://deepmind.google/) (Google Deepmind) | Image-to-image photorealistic render |
| Video Synthesis | [fal.ai](https://fal.ai/) | Keyframe-anchored video interpolation |
| Backend | Python 3.11+ | Pipeline orchestration |
| Frontend | React + FastAPI | Web upload UI, progress tracking, video preview |

---

## Quickstart (CLI)

```bash
git clone https://github.com/kpuchkov1-code/Explodify.git
cd Explodify
pip install -r requirements.txt

# STEP assembly (recommended for multi-part CAD)
python explodify.py --input your_assembly.step --explode 1.5

# Tinkercad OBJ export
python explodify.py --input tinker.obj --explode 1.5

# GLB with custom style and output path
python explodify.py --input assembly.glb --explode 2.0 \
  --style-prompt "Dark marble, dramatic rim lighting" \
  --output output/exploded.mp4
```

Output frames are written to `output/frames/` by default. Phases 3 and 4 require API keys (see below); without them, the pipeline exits cleanly after Phase 2 with the 3 PNG keyframes ready.

---

## Environment Variables

```env
GOOGLE_API_KEY=...       # Gemini Flash (Phase 3 stylization)
FAL_KEY=...              # fal.ai video synthesis (Phase 4)
```

Copy `.env.example` to `.env` and fill in your keys.

---

## Roadmap

### v0.1 — Hackathon MVP (current sprint)
- [x] Phase 1: Trimesh geometric analysis (optimal angle + explosion vectors)
- [x] Phase 1: STEP loading via cascadio (preserves named assembly components)
- [x] Phase 1: Automatic upright reorientation (longest-axis alignment)
- [x] Phase 1: Per-direction ray-cast grid (fixes camera angle for tall/wide assemblies)
- [x] Phase 2: pyrender snapshot export (3 PNG keyframes)
- [x] Phase 2: MTL material color extraction (OBJ/MTL diffuse → pyrender material)
- [x] Phase 2: View-plane footprint camera (correct zoom for any aspect ratio)
- [x] Phase 3: Gemini Flash stylization
- [x] Phase 4: fal.ai video synthesis (Kling with keyframe anchoring)
- [ ] FastAPI backend wiring all phases together
- [ ] React frontend: upload → progress → download

### v0.2 — Post-Hackathon Polish
- [ ] Per-component material assignment (metal vs. plastic detection)
- [ ] Custom style prompt editor in UI
- [ ] Brand overlay (logo, color grading) post-processing pass
- [ ] Batch processing for product catalogues

### v0.3 — Production
- [ ] User accounts + job history
- [ ] Webhook delivery of finished MP4
- [ ] API for headless integration (CI/CD for product teams)
- [ ] White-label embed widget

---

## Partner Technologies

| Partner | Usage | Hackathon Prize Track |
|---------|-------|----------------------|
| **Google Deepmind / Gemini Flash** | Phase 3 image stylization | Gemini Credits (finalist prizes) |
| **fal.ai** | Phase 4 video synthesis | Best use of fal ($1000 USD credits) |

Hackathon voucher code for fal.ai: `techeurope-london`

---

## Project Structure

```
Explodify/
├── explodify.py              # CLI entry point
├── requirements.txt
├── README.md
├── .env.example              # API key template
├── pipeline/
│   ├── models.py             # Shared dataclasses: NamedMesh, FrameSet, PipelineMetadata
│   ├── format_loader.py      # Multi-format loader (STEP via cascadio, GLB/OBJ/STL via trimesh)
│   ├── phase1_geometry.py    # Trimesh: reorient, optimal angle, explosion vectors
│   ├── phase2_snapshots.py   # pyrender: PNG keyframe export
│   ├── phase3_stylize.py     # Gemini Flash: image-to-image stylization
│   └── phase4_video.py       # fal.ai: video synthesis
├── tests/
│   └── pipeline/
│       ├── conftest.py           # Shared fixtures (two-box GLB assembly)
│       ├── test_format_loader.py
│       ├── test_phase1_geometry.py
│       ├── test_phase2_snapshots.py
│       └── test_integration_phase1_2.py
├── backend/
│   ├── main.py               # FastAPI app + job queue
│   └── models.py             # Pydantic job/status models
└── frontend/
    └── src/
        ├── App.tsx
        └── components/
            ├── UploadZone.tsx
            ├── PipelineProgress.tsx
            └── VideoPreview.tsx
```

---

## Hackathon

**Event:** Tech: Europe London AI Hackathon | April 2026
**Track:** Open Innovation + Best Use of fal.ai side challenge
**Submission:** 2-minute Loom demo + this public repo

---

## License

MIT
