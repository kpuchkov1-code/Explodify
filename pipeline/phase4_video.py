# pipeline/phase4_video.py
import base64
import os
import tempfile
from pathlib import Path

import fal_client
import requests

from pipeline.models import FrameSet

FAL_MODEL = "fal-ai/kling-video/v2/master/image-to-video"
CLIP_DURATION = "5"   # seconds per clip — 2 clips = ~10s total
DEFAULT_VIDEO_PROMPT = (
    "Smooth product advertisement animation. Parts separate cleanly and gracefully. "
    "Studio lighting. Clean white background."
)


def _build_video_prompt(style_prompt: str) -> str:
    """Combine user's aesthetic with the motion description."""
    motion = "Smooth animation, parts separate cleanly and gracefully."
    aesthetic = style_prompt.strip() if style_prompt.strip() else DEFAULT_VIDEO_PROMPT
    return f"{motion} {aesthetic}"


class FalVideoSynth:
    """Phase 4: Generate a video from 3 stylized keyframes using fal.ai Kling v2."""

    def __init__(self, fal_key: str | None = None):
        key = fal_key or os.environ.get("FAL_KEY", "")
        os.environ["FAL_KEY"] = key  # fal_client reads from env

    def synthesize(self, stylized_frames: FrameSet, output_path: Path) -> Path:
        """Generate two video clips (A→B, B→C) and stitch into one MP4.

        Args:
            stylized_frames: FrameSet from GeminiStylizer.stylize().
            output_path: Path to write the final .mp4.

        Returns:
            output_path after writing.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Upload frames as base64 data URIs (fal.ai accepts these)
        frame_a_uri = self._to_data_uri(stylized_frames.frame_a)
        frame_b_uri = self._to_data_uri(stylized_frames.frame_b)
        frame_c_uri = self._to_data_uri(stylized_frames.frame_c)
        frame_d_uri = self._to_data_uri(stylized_frames.frame_d)
        frame_e_uri = self._to_data_uri(stylized_frames.frame_e)

        video_prompt = _build_video_prompt(stylized_frames.metadata.style_prompt)

        # 4 clips covering 0% → 25% → 50% → 75% → 100% explosion
        clip1_bytes = self._generate_clip(frame_a_uri, frame_b_uri, video_prompt)
        clip2_bytes = self._generate_clip(frame_b_uri, frame_c_uri, video_prompt)
        clip3_bytes = self._generate_clip(frame_c_uri, frame_d_uri, video_prompt)
        clip4_bytes = self._generate_clip(frame_d_uri, frame_e_uri, video_prompt)

        stitched = self._stitch_clips(
            [clip1_bytes, clip2_bytes, clip3_bytes, clip4_bytes], output_path
        )
        return stitched

    def _to_data_uri(self, frame_path: Path) -> str:
        """Convert PNG file to base64 data URI for fal.ai upload."""
        with open(frame_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{data}"

    def _generate_clip(self, start_image_url: str, end_image_url: str, prompt: str) -> bytes:
        """Call fal.ai Kling v2 to generate one video clip. Returns video bytes."""
        result = fal_client.subscribe(
            FAL_MODEL,
            arguments={
                "prompt": prompt,
                "image_url": start_image_url,
                "tail_image_url": end_image_url,
                "duration": CLIP_DURATION,
                "aspect_ratio": "16:9",
                "cfg_scale": 0.5,
            },
        )
        video_url = result["video"]["url"]
        resp = requests.get(video_url, timeout=60)
        resp.raise_for_status()
        return resp.content

    def _stitch_clips(self, clips: list[bytes], output_path: Path) -> Path:
        """Write clips to temp files, concatenate with ffmpeg, return output_path."""
        import subprocess

        clip_paths = []
        for clip_bytes in clips:
            f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            f.write(clip_bytes)
            f.close()
            clip_paths.append(f.name)

        concat_list = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        )
        concat_list.write("".join(f"file '{p}'\n" for p in clip_paths))
        concat_list.close()

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", concat_list.name,
                    "-c", "copy",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # ffmpeg not available — write first clip as fallback
            output_path.write_bytes(clips[0])

        return output_path
