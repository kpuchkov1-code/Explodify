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
    camera_angles_deg: list[float]  # [0.0, 15.0, 30.0] — camera orbit at each frame
    style_prompt: str = ""          # user-supplied aesthetic prompt; passed through to Phase 3 + 4


@dataclass
class FrameSet:
    """Three PNG keyframes produced by Phase 2, consumed by Phase 3."""
    frame_a: Path   # 0%   explosion, 0°  camera — assembled
    frame_b: Path   # 50%  explosion, 15° camera — mid-explode
    frame_c: Path   # 100% explosion, 30° camera — fully exploded
    metadata: PipelineMetadata

    def validate(self) -> None:
        """Raise ValueError if any frame file is missing."""
        for attr in ("frame_a", "frame_b", "frame_c"):
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
