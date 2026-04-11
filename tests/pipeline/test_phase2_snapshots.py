# tests/pipeline/test_phase2_snapshots.py
import pytest
from pathlib import Path
from pipeline.phase1_geometry import GeometryAnalyzer
from pipeline.phase2_snapshots import SnapshotRenderer
from pipeline.models import FrameSet


def test_render_produces_three_png_files(two_box_glb, tmp_path):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    master = analyzer.master_angle(named_meshes)
    vectors = analyzer.explosion_vectors(named_meshes, scalar=1.5)

    renderer = SnapshotRenderer()
    frame_set = renderer.render(named_meshes, vectors, master, output_dir=tmp_path, scalar=1.5)

    assert isinstance(frame_set, FrameSet)
    assert frame_set.frame_a.exists()
    assert frame_set.frame_b.exists()
    assert frame_set.frame_c.exists()
    assert frame_set.frame_a.suffix == ".png"


def test_render_metadata_fields(two_box_glb, tmp_path):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    master = analyzer.master_angle(named_meshes)
    vectors = analyzer.explosion_vectors(named_meshes, scalar=1.5)

    renderer = SnapshotRenderer()
    frame_set = renderer.render(named_meshes, vectors, master, output_dir=tmp_path, scalar=1.5)

    meta = frame_set.metadata
    assert meta.master_angle == master
    assert meta.explosion_scalar == 1.5
    assert meta.component_count == len(named_meshes)
    assert meta.camera_angles_deg == [0.0, 15.0, 30.0]
    assert len(meta.component_names) == len(named_meshes)


def test_render_images_are_valid_png(two_box_glb, tmp_path):
    from PIL import Image
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    master = analyzer.master_angle(named_meshes)
    vectors = analyzer.explosion_vectors(named_meshes, scalar=1.5)

    renderer = SnapshotRenderer()
    frame_set = renderer.render(named_meshes, vectors, master, output_dir=tmp_path, scalar=1.5)

    for frame_path in (frame_set.frame_a, frame_set.frame_b, frame_set.frame_c):
        img = Image.open(frame_path)
        assert img.size[0] > 0 and img.size[1] > 0
        assert img.format == "PNG"
