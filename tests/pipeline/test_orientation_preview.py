# tests/pipeline/test_orientation_preview.py
import base64
import pytest
from pipeline.orientation_preview import render_orientation_previews, FACE_ORDER
from pipeline.phase1_geometry import GeometryAnalyzer


def test_returns_all_six_faces(two_box_glb):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    images = render_orientation_previews(named_meshes)

    assert set(images.keys()) == set(FACE_ORDER)


def test_images_are_valid_base64_png(two_box_glb):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    images = render_orientation_previews(named_meshes)

    for face, data_uri in images.items():
        assert data_uri.startswith("data:image/png;base64,"), f"{face} has wrong prefix"
        b64_part = data_uri.split(",", 1)[1]
        raw = base64.b64decode(b64_part)
        # PNG magic bytes
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"{face} is not a valid PNG"


def test_images_are_non_empty(two_box_glb):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    images = render_orientation_previews(named_meshes)

    for face, data_uri in images.items():
        b64_part = data_uri.split(",", 1)[1]
        raw = base64.b64decode(b64_part)
        assert len(raw) > 1000, f"{face} image suspiciously small ({len(raw)} bytes)"


def test_different_faces_produce_different_images(two_box_glb):
    """Each of the 6 face views should be visually distinct (different raw bytes)."""
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    images = render_orientation_previews(named_meshes)

    unique_images = set(images.values())
    assert len(unique_images) > 1, "All 6 face views produced identical images"
