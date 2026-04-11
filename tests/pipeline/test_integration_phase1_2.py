# tests/pipeline/test_integration_phase1_2.py
from pipeline.phase1_geometry import GeometryAnalyzer
from pipeline.phase2_snapshots import SnapshotRenderer
from pipeline.models import FrameSet


def test_phase1_to_phase2_full_pipeline(two_box_glb, tmp_path):
    """Full Phase 1 + Phase 2 integration: CAD file -> 3 PNG frames."""
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    master = analyzer.master_angle(named_meshes)
    vectors = analyzer.explosion_vectors(named_meshes, scalar=1.5)

    renderer = SnapshotRenderer()
    frame_set = renderer.render(
        named_meshes, vectors, master,
        output_dir=tmp_path, scalar=1.5, source_format=".glb",
    )

    assert isinstance(frame_set, FrameSet)
    frame_set.validate()

    assert frame_set.metadata.master_angle in {
        "top", "bottom", "left", "right", "front", "back"
    }
    assert frame_set.metadata.component_count >= 2
    assert frame_set.metadata.camera_angles_deg == [0.0, 15.0, 30.0]
    assert frame_set.metadata.source_format == ".glb"
    assert len(frame_set.metadata.component_names) >= 2

    print(f"\nMaster angle: {frame_set.metadata.master_angle}")
    print(f"Components: {frame_set.metadata.component_names}")
    print(f"Frames: {frame_set.frame_a}, {frame_set.frame_b}, {frame_set.frame_c}")
