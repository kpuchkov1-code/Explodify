# pipeline/phase4_video.py
"""Phase 4: Apply photorealistic style to the assembled video via Kling o1 edit.

Strategy: pyrender produces geometrically exact motion (72 frames, Phase 2+3).
Kling o1 edit preserves that motion structure completely while applying
studio-quality materials, lighting, and environment.

The prompt is built upstream by pipeline.prompt_interpreter, which fills a
structured template from the user's material description, style toggles, and
free-text notes.  This module receives the final prompt string and handles
only the FAL API interaction (upload, submit, download).

Endpoint: fal-ai/kling-video/o1/standard/video-to-video/edit
  - Transforms style/setting/lighting while retaining original motion.
  - Required: prompt, video_url
"""
import asyncio
import os
from pathlib import Path

import fal_client
import httpx

FAL_KLING_EDIT = "fal-ai/kling-video/o1/video-to-video/edit"


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
        self._endpoint = FAL_KLING_EDIT

    async def edit(
        self,
        video_path: Path,
        prompt: str,
        output_path: Path,
    ) -> Path:
        """Upload raw video, apply Kling o1 style edit, write result.

        Args:
            video_path:  Path to the mp4 assembled in Phase 3.
            prompt:      Fully assembled prompt from prompt_interpreter.
            output_path: Destination for the styled mp4.

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
        print(f"[Phase 4] Uploaded -> {video_url}")

        print(f"[Phase 4] Submitting Kling o1 edit...")
        print(f"[Phase 4] Prompt: {prompt[:200]}...")

        # Blocking fal_client.subscribe call, run off the event loop.
        # duration="3" matches the 72-frame 24fps base video exactly.
        # Omitting it lets Kling default to 5s and stretch the motion.
        result = await asyncio.to_thread(
            fal_client.subscribe,
            self._endpoint,
            arguments={
                "prompt": prompt,
                "video_url": video_url,
                "duration": "3",
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
