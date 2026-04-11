# Explodify

**Explodify** turns any CAD assembly file into a photorealistic, market-ready exploded-view animation — automatically.

> Built at the **[Tech: Europe] London AI Hackathon 2026**

---

## The Idea

Product teams spend thousands on Blender artists to produce exploded-view ads for hardware products. Explodify eliminates that bottleneck: upload a `.glb` / `.obj` / `.stl` file, receive a studio-grade animated MP4 in minutes.

The key insight is a **geometric-first** approach: rather than asking an AI to "guess" how parts come apart, we use Trimesh to compute the mathematically correct explosion vectors and optimal viewing angle, then use those precise snapshots as anchors for AI stylization and video interpolation. The AI never has to invent geometry it cannot see.

---

## Pipeline (4 Phases)

```
CAD file (.glb / .obj / .stl)
    │
    ▼
Phase 1: Geometric Analysis (Trimesh)
    │  • Load assembly; identify individual mesh components
    │  • Ray-cast from 6 cardinal directions (Top/Bottom/Left/Right/Front/Back)
    │  • Select "Master Angle" = direction hitting most unique mesh IDs
    │  • Compute global centroid; per-component explosion vectors:
    │      v⃗ = centroid_component − centroid_assembly
    │  • Apply scalar E to get positions at 50% and 100% explosion
    ▼
Phase 2: Structural Snapshots (pyrender)
    │  • Define orbital camera path: 0° → 15° → 30° rotation
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
Phase 4: Video Synthesis (fal.ai — Kling / Luma)
    │  • Upload 3 stylized keyframes to fal.ai video model
    │  • Use Start / Middle / End frame anchoring
    │    (forces AI to respect Trimesh-calculated geometry at 50% mark)
    │  • Export final MP4
    ▼
Output: studio-grade exploded-view animation
```

---

## Why This Works

| Problem | Solution |
|---------|----------|
| AI invents geometry it cannot see | Trimesh snapshots give it exact views at 0%, 50%, 100% |
| Camera path is inconsistent | We rotate before handing to AI, so it interpolates known views |
| Wrong viewing angle for consumer POV | Ray-casting finds the angle that exposes the most components |
| Stylized frames drift visually | Single seed prompt used consistently across all 3 keyframes |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Geometry | [Trimesh](https://trimesh.org/) | Assembly analysis, explosion vectors, ray-casting |
| Rendering | [pyrender](https://pyrender.readthedocs.io/) | Headless PNG snapshot export |
| AI Stylization | [Gemini Flash](https://deepmind.google/) (Google Deepmind) | Image-to-image photorealistic render |
| Video Synthesis | [fal.ai](https://fal.ai/) — Kling / Luma | Keyframe-anchored video interpolation |
| Backend | Python 3.11+ | Pipeline orchestration |
| Frontend | React + FastAPI | Web upload UI, progress tracking, video preview |

---

## Web App Vision

The end product is a **web application** where a user can:

1. **Upload** a CAD file via drag-and-drop (`.glb`, `.obj`, `.stl`)
2. **Configure** explosion strength, style prompt, output resolution
3. **Watch** a live progress feed as each pipeline phase completes
4. **Preview and download** the final MP4 animation

The backend runs the full Python pipeline (Phases 1–4) as an async job. The frontend polls for status and streams phase-by-phase progress back to the user.

---

## Roadmap

### v0.1 — Hackathon MVP (current sprint)
- [ ] Phase 1: Trimesh geometric analysis (optimal angle + explosion vectors)
- [ ] Phase 2: pyrender snapshot export (3 PNG keyframes)
- [ ] Phase 3: Gemini Flash stylization
- [ ] Phase 4: fal.ai video synthesis (Kling with keyframe anchoring)
- [ ] FastAPI backend wiring all phases together
- [ ] React frontend: upload → progress → download

### v0.2 — Post-Hackathon Polish
- [ ] Support STEP / IGES files via Open CASCADE wrapper
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

## Quickstart (CLI)

```bash
git clone https://github.com/kpuchkov1-code/explodify.git
cd explodify
pip install -r requirements.txt
python explodify.py --input examples/assembly.glb --explode 1.5
```

---

## Environment Variables

```env
GOOGLE_API_KEY=...       # Gemini Flash (Google Deepmind)
FAL_KEY=...              # fal.ai video synthesis
```

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
explodify/
├── explodify.py          # CLI entry point
├── requirements.txt
├── README.md
├── .env.example          # API key template
├── pipeline/
│   ├── phase1_geometry.py    # Trimesh: optimal angle + explosion vectors
│   ├── phase2_snapshots.py   # pyrender: PNG keyframe export
│   ├── phase3_stylize.py     # Gemini Flash: image-to-image stylization
│   └── phase4_video.py       # fal.ai: video synthesis
├── backend/
│   ├── main.py               # FastAPI app + job queue
│   └── models.py             # Pydantic job/status models
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   ├── components/
    │   │   ├── UploadZone.tsx
    │   │   ├── PipelineProgress.tsx
    │   │   └── VideoPreview.tsx
    │   └── api/
    │       └── client.ts
    └── package.json
```

---

## Hackathon

**Event:** Tech: Europe London AI Hackathon | April 2026
**Track:** Open Innovation + Best Use of fal.ai side challenge
**Submission:** 2-minute Loom demo + this public repo

---

## License

MIT
