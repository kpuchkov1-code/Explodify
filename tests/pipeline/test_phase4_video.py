import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pipeline.phase4_video import FalVideoSynth
from pipeline.models import FrameSet, PipelineMetadata
from PIL import Image
import io


@pytest.fixture
def stylized_frame_set(tmp_path):
    for name in ("frame_a.png", "frame_b.png", "frame_c.png", "frame_d.png", "frame_e.png"):
        Image.new("RGB", (256, 256), color=(200, 200, 200)).save(tmp_path / name)
    return FrameSet(
        frame_a=tmp_path / "frame_a.png",
        frame_b=tmp_path / "frame_b.png",
        frame_c=tmp_path / "frame_c.png",
        frame_d=tmp_path / "frame_d.png",
        frame_e=tmp_path / "frame_e.png",
        metadata=PipelineMetadata(
            master_angle="front",
            explosion_scalar=1.5,
            component_count=2,
            camera_angles_deg=[0.0, 10.0, 20.0, 30.0, 40.0],
        ),
    )


def test_synthesize_produces_mp4(stylized_frame_set, tmp_path):
    """synthesize() should write an MP4 file and return its path."""
    output_path = tmp_path / "output.mp4"

    fake_video_bytes = b"\x00" * 1024  # minimal fake MP4 bytes

    with patch("pipeline.phase4_video.fal_client") as mock_fal:
        mock_result = {"video": {"url": "https://fake.fal.ai/clip.mp4"}}
        mock_fal.subscribe.return_value = mock_result

        with patch("pipeline.phase4_video.requests") as mock_requests:
            mock_resp = MagicMock()
            mock_resp.content = fake_video_bytes
            mock_requests.get.return_value = mock_resp

            synth = FalVideoSynth(fal_key="fake_key")
            result_path = synth.synthesize(stylized_frame_set, output_path=output_path)

    assert result_path == output_path
    assert output_path.exists()


def test_synthesize_calls_fal_four_times(stylized_frame_set, tmp_path):
    """Four fal.ai calls: clips A→B, B→C, C→D, D→E."""
    output_path = tmp_path / "output.mp4"
    fake_video_bytes = b"\x00" * 512

    with patch("pipeline.phase4_video.fal_client") as mock_fal:
        mock_fal.subscribe.return_value = {"video": {"url": "https://fake.fal.ai/clip.mp4"}}
        with patch("pipeline.phase4_video.requests") as mock_requests:
            mock_resp = MagicMock()
            mock_resp.content = fake_video_bytes
            mock_requests.get.return_value = mock_resp

            synth = FalVideoSynth(fal_key="fake_key")
            synth.synthesize(stylized_frame_set, output_path=output_path)

    assert mock_fal.subscribe.call_count == 4
