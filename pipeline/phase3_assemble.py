# pipeline/phase3_assemble.py
"""Phase 3: Assemble PNG video frames into an mp4 using ffmpeg.

The 72 pyrender frames provide geometrically exact motion — no AI involved.
This mp4 is then passed to Phase 4 (Kling o1 edit) which applies photorealistic
style while preserving the motion exactly.
"""
import subprocess
from pathlib import Path

VIDEO_FPS = 24


class FrameAssembler:
    """Assemble a directory of video_NNNN.png frames into a single mp4."""

    def assemble(
        self,
        frames_dir: Path,
        output_path: Path,
        fps: int = VIDEO_FPS,
    ) -> Path:
        """Run ffmpeg to produce a clean H.264 mp4 from the PNG sequence.

        Args:
            frames_dir:  Directory containing video_0000.png … video_NNNN.png
            output_path: Destination .mp4 path.
            fps:         Frame rate (default 24 — 72 frames = 3 s).

        Returns:
            output_path after writing.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pattern = str(frames_dir / "video_%04d.png")

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-r", str(fps),
                    "-i", pattern,
                    "-c:v", "libx264",
                    "-preset", "slow",
                    "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"ffmpeg failed assembling frames:\n{exc.stderr[-600:]}"
            ) from exc
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Install with: brew install ffmpeg"
            )

        print(f"[Phase 3] Assembled {fps} fps mp4 → {output_path}")
        return output_path
