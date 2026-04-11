# pipeline/models.py
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PipelineMetadata:
    """Geometry analysis results produced by Phase 1."""
    master_angle: str               # "top" | "bottom" | "left" | "right" | "front" | "back"
    explosion_scalar: float         # E multiplier applied to explosion vectors
    component_count: int            # number of unique mesh IDs detected
    camera_angles_deg: list[float]  # [0.0, 15.0, 30.0]


@dataclass
class FrameSet:
    """Three PNG keyframes produced by Phase 2, consumed by Phase 3."""
    frame_a: Path   # 0%   explosion, 0°  camera
    frame_b: Path   # 50%  explosion, 15° camera
    frame_c: Path   # 100% explosion, 30° camera
    metadata: PipelineMetadata

    def validate(self) -> None:
        for attr in ("frame_a", "frame_b", "frame_c"):
            p = getattr(self, attr)
            if not Path(p).exists():
                raise ValueError(f"Frame not found: {p}")


@dataclass
class JobResult:
    """Final result returned by the full pipeline."""
    frame_set: FrameSet
    stylized_frame_set: FrameSet
    video_path: Path
    error: Optional[str] = None
