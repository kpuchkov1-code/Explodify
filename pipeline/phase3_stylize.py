# pipeline/phase3_stylize.py
import io
import os
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from pipeline.models import FrameSet

DEFAULT_STYLE_PROMPT = (
    "High-end industrial design render, Blender Cycles quality, "
    "dramatic studio lighting with soft shadows, brushed aluminum and polycarbonate materials, "
    "pure white background, photorealistic product photography style."
)

STRUCTURAL_CONSTRAINT = (
    "Preserve the exact structure, layout, and positions of all components. "
    "Do not add, remove, or rearrange parts."
)

MODEL = "gemini-2.0-flash-preview-image-generation"


def _build_gemini_prompt(style_prompt: str) -> str:
    """Combine the user's aesthetic with the non-negotiable structural constraint."""
    aesthetic = style_prompt.strip() if style_prompt.strip() else DEFAULT_STYLE_PROMPT
    return f"Transform this 3D render. {STRUCTURAL_CONSTRAINT} {aesthetic}"


class GeminiStylizer:
    """Phase 3: Stylize raw PNG snapshots into photorealistic renders via Gemini Flash."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ["GOOGLE_API_KEY"]
        self._client = genai.Client(api_key=self._api_key)

    def stylize(self, frame_set: FrameSet, output_dir: Path) -> FrameSet:
        """Apply Gemini image-to-image stylization to all 5 frames.

        The style prompt is read from frame_set.metadata.style_prompt.
        If empty, DEFAULT_STYLE_PROMPT is used.

        Args:
            frame_set: Raw FrameSet produced by Phase 2 (carries style_prompt in metadata).
            output_dir: Directory to write frame_a.png through frame_e.png.

        Returns:
            New FrameSet pointing to stylized PNG files, with same metadata.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        prompt = _build_gemini_prompt(frame_set.metadata.style_prompt)

        frame_map = [
            (frame_set.frame_a, "frame_a.png"),
            (frame_set.frame_b, "frame_b.png"),
            (frame_set.frame_c, "frame_c.png"),
            (frame_set.frame_d, "frame_d.png"),
            (frame_set.frame_e, "frame_e.png"),
        ]
        output_paths = []
        for src_path, out_name in frame_map:
            out_path = output_dir / out_name
            stylized = self._stylize_single(src_path, prompt)
            stylized.save(str(out_path))
            output_paths.append(out_path)

        return FrameSet(
            frame_a=output_paths[0],
            frame_b=output_paths[1],
            frame_c=output_paths[2],
            frame_d=output_paths[3],
            frame_e=output_paths[4],
            metadata=frame_set.metadata,
        )

    def _stylize_single(self, frame_path: Path, prompt: str) -> Image.Image:
        """Call Gemini to stylize one PNG using the given prompt. Returns PIL Image."""
        with open(frame_path, "rb") as f:
            image_bytes = f.read()

        response = self._client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and "image" in part.inline_data.mime_type:
                return Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")

        raise RuntimeError(f"Gemini returned no image for {frame_path.name}")
