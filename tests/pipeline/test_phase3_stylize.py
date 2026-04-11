import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pipeline.phase3_stylize import GeminiStylizer
from pipeline.models import FrameSet, PipelineMetadata


@pytest.fixture
def mock_frame_set(tmp_path):
    """FrameSet with real (blank white) PNGs for testing without a real CAD file."""
    from PIL import Image
    for name in ("frame_a.png", "frame_b.png", "frame_c.png"):
        Image.new("RGB", (256, 256), color=(200, 200, 200)).save(tmp_path / name)
    return FrameSet(
        frame_a=tmp_path / "frame_a.png",
        frame_b=tmp_path / "frame_b.png",
        frame_c=tmp_path / "frame_c.png",
        metadata=PipelineMetadata(
            master_angle="front",
            explosion_scalar=1.5,
            component_count=2,
            camera_angles_deg=[0.0, 15.0, 30.0],
        ),
    )


@pytest.fixture
def fake_gemini_response():
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), color=(240, 240, 240)).save(buf, format="PNG")
    part = MagicMock()
    part.inline_data.data = buf.getvalue()
    part.inline_data.mime_type = "image/png"
    response = MagicMock()
    response.candidates[0].content.parts = [part]
    return response


def test_stylize_returns_frame_set_with_three_pngs(mock_frame_set, tmp_path, fake_gemini_response):
    """Stylize should return a FrameSet with 3 existing PNG files."""
    with patch("pipeline.phase3_stylize.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_gemini_response

        stylizer = GeminiStylizer(api_key="fake_key")
        result = stylizer.stylize(mock_frame_set, output_dir=tmp_path / "stylized")

    assert isinstance(result, FrameSet)
    assert result.frame_a.exists()
    assert result.frame_b.exists()
    assert result.frame_c.exists()


def test_stylize_uses_custom_style_prompt(mock_frame_set, tmp_path, fake_gemini_response):
    """The user's style prompt must appear in the Gemini API call."""
    mock_frame_set.metadata.style_prompt = "Neon cyberpunk aesthetic, dark background, glowing edges"

    with patch("pipeline.phase3_stylize.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_gemini_response

        stylizer = GeminiStylizer(api_key="fake_key")
        stylizer.stylize(mock_frame_set, output_dir=tmp_path / "custom")

    # Verify the custom prompt was passed to Gemini (appears in call args)
    call_args = mock_client.models.generate_content.call_args_list[0]
    contents = call_args.kwargs["contents"] if call_args.kwargs else call_args[1]["contents"]
    prompt_text = next(p.text for p in contents if hasattr(p, "text"))
    assert "Neon cyberpunk" in prompt_text
    assert "Preserve the exact structure" in prompt_text  # structural constraint always present


def test_stylize_uses_default_prompt_when_empty(mock_frame_set, tmp_path, fake_gemini_response):
    """Empty style_prompt falls back to DEFAULT_STYLE_PROMPT."""
    mock_frame_set.metadata.style_prompt = ""

    with patch("pipeline.phase3_stylize.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_gemini_response

        stylizer = GeminiStylizer(api_key="fake_key")
        stylizer.stylize(mock_frame_set, output_dir=tmp_path / "default")

    call_args = mock_client.models.generate_content.call_args_list[0]
    contents = call_args.kwargs["contents"] if call_args.kwargs else call_args[1]["contents"]
    prompt_text = next(p.text for p in contents if hasattr(p, "text"))
    assert "industrial design" in prompt_text  # from DEFAULT_STYLE_PROMPT


def test_stylize_preserves_metadata(mock_frame_set, tmp_path, fake_gemini_response):
    with patch("pipeline.phase3_stylize.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_gemini_response

        stylizer = GeminiStylizer(api_key="fake_key")
        result = stylizer.stylize(mock_frame_set, output_dir=tmp_path / "s2")

    assert result.metadata.master_angle == "front"
    assert result.metadata.component_count == 2
