# pipeline/phase4_video.py
"""Phase 4: Apply photorealistic style to the assembled video via Kling o1 edit.

Strategy: pyrender produces geometrically exact motion (72 frames, Phase 2+3).
Kling o1 edit preserves that motion structure completely while applying
studio-quality materials, lighting, and environment from the style prompt.
This avoids the hallucination problem seen when Kling has to generate motion
itself from sparse keyframes.

Endpoint: fal-ai/kling-video/o1/standard/video-to-video/edit
  - Transforms style/setting/lighting while retaining original motion.
  - Required: prompt, video_url
"""
import asyncio
import os
from pathlib import Path

import fal_client
import httpx

FAL_KLING_EDIT = "fal-ai/kling-video/o1/standard/video-to-video/edit"

_BASE_PROMPT = (
    "Photorealistic product photography render. "
    "Preserve all component motion, positions, and camera movement exactly. "
    "Apply high-quality physical materials with accurate reflections and specularity. "
    "Professional studio lighting setup. Sharp focus across all components. "
)

_DEFAULT_STYLE = (
    "Clean dark studio backdrop with subtle ground plane reflection. "
    "Soft key light from upper-left, cool fill from right. "
    "Each component rendered as machined aluminum or anodized metal. "
)


def _build_edit_prompt(style_prompt: str) -> str:
    """Combine the motion-preservation base with the user's aesthetic."""
    aesthetic = style_prompt.strip() if style_prompt.strip() else _DEFAULT_STYLE
    return _BASE_PROMPT + aesthetic


class KlingVideoEditor:
    """Phase 4: Upload assembled video → Kling o1 edit → download styled result."""

    def __init__(self, fal_key: str | None = None) -> None:
        key = fal_key or os.environ.get("FAL_KEY", "")
        if not key:
            raise ValueError(
                "FAL_KEY environment variable is required for Phase 4. "
                "Set it in your .env file."
            )
        os.environ["FAL_KEY"] = key

    async def edit(
        self,
        video_path: Path,
        style_prompt: str,
        output_path: Path,
    ) -> Path:
        """Upload raw video, apply Kling o1 style edit, write result.

        Args:
            video_path:   Path to the mp4 assembled in Phase 3.
            style_prompt: User-supplied aesthetic (lighting, materials, etc.).
            output_path:  Destination for the styled mp4.

        Returns:
            output_path after writing.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Upload to fal.ai storage (returns a hosted URL)
        print("[Phase 4] Uploading base video to fal.ai storage...")
        video_url = await asyncio.to_thread(
            fal_client.upload_file, str(video_path)
        )
        print(f"[Phase 4] Uploaded → {video_url}")

        prompt = _build_edit_prompt(style_prompt)
        print(f"[Phase 4] Submitting Kling o1 edit...")
        print(f"[Phase 4] Prompt: {prompt[:120]}...")

        # Blocking fal_client.subscribe call, run off the event loop
        result = await asyncio.to_thread(
            fal_client.subscribe,
            FAL_KLING_EDIT,
            arguments={
                "prompt": prompt,
                "video_url": video_url,
            },
        )

        output_url: str = result["video"]["url"]
        file_size = result["video"].get("file_size", 0)
        print(f"[Phase 4] Result ready ({file_size // 1024} KB) → {output_url}")

        # Download the styled video
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.get(output_url)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)

        print(f"[Phase 4] Styled video written → {output_path}")
        return output_path
