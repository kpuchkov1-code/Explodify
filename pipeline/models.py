# pipeline/models.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import trimesh

# Formats loaded natively by trimesh (no conversion needed)
TRIMESH_FORMATS = frozenset({
    ".glb", ".gltf", ".obj", ".stl", ".ply", ".off", ".3mf",
})

# Formats converted via cascadio (OpenCASCADE STEP reader -> GLB intermediate)
CASCADIO_FORMATS = frozenset({
    ".step", ".stp",
})

ALL_SUPPORTED_FORMATS = TRIMESH_FORMATS | CASCADIO_FORMATS

UNSUPPORTED_FORMAT_HELP = """
Only STEP (.step / .stp) and mesh files (GLB, OBJ, STL, PLY, 3MF) are supported.

To convert a proprietary CAD file to STEP:

  SolidWorks:    File -> Save As -> STEP AP214 or AP242
  Fusion 360:    File -> Export -> STEP
  Inventor:      File -> Save As -> STEP
  CATIA:         File -> Save As -> STEP
  Onshape:       Export -> STEP
  FreeCAD:       File -> Export -> STEP

Supported: {supported}
""".format(supported=", ".join(sorted(ALL_SUPPORTED_FORMATS)))


class UnsupportedFormatError(ValueError):
    """Raised when the input file format cannot be loaded by Explodify."""


@dataclass
class NamedMesh:
    """A single component mesh with its assembly name."""
    name: str
    mesh: trimesh.Trimesh


@dataclass
class PipelineMetadata:
    """Geometry analysis results produced by Phase 1."""
    master_angle: str               # "top" | "bottom" | "left" | "right" | "front" | "back"
    explosion_scalar: float         # E multiplier applied to explosion vectors
    component_count: int            # number of unique mesh IDs detected
    camera_angles_deg: list[float]  # [0.0, 15.0, 30.0] — camera orbit at each frame
    style_prompt: str = ""          # user-supplied aesthetic prompt; passed through to Phase 3 + 4
    source_format: str = ""         # file extension of the input, e.g. ".step"
    component_names: list[str] = field(default_factory=list)


@dataclass
class FrameSet:
    """Five PNG keyframes produced by Phase 2, consumed by Phase 3."""
    frame_a: Path   # 0%   explosion, 0°  camera — assembled
    frame_b: Path   # 25%  explosion, 10° camera
    frame_c: Path   # 50%  explosion, 20° camera — mid-explode
    frame_d: Path   # 75%  explosion, 30° camera
    frame_e: Path   # 100% explosion, 40° camera — fully exploded
    metadata: PipelineMetadata

    def validate(self) -> None:
        """Raise ValueError if any frame file is missing."""
        for attr in ("frame_a", "frame_b", "frame_c", "frame_d", "frame_e"):
            p = getattr(self, attr)
            if not Path(p).exists():
                raise ValueError(f"Frame not found: {p}")


@dataclass
class JobResult:
    """Final result returned by the full pipeline."""
    frame_set: FrameSet                 # raw frames from Phase 2
    stylized_frame_set: FrameSet        # AI-rendered frames from Phase 3
    video_path: Path                    # MP4 output from Phase 4
    error: Optional[str] = None
