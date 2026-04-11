# tests/pipeline/test_phase1_geometry.py
import numpy as np
import pytest
from pipeline.phase1_geometry import GeometryAnalyzer


def test_load_returns_list_of_meshes(two_box_glb):
    analyzer = GeometryAnalyzer()
    meshes = analyzer.load(str(two_box_glb))
    assert isinstance(meshes, list)
    assert len(meshes) >= 2


def test_load_nonexistent_file_raises():
    analyzer = GeometryAnalyzer()
    with pytest.raises(FileNotFoundError):
        analyzer.load("does_not_exist.glb")


def test_master_angle_returns_valid_direction(two_box_glb):
    analyzer = GeometryAnalyzer()
    meshes = analyzer.load(str(two_box_glb))
    direction = analyzer.master_angle(meshes)
    assert direction in {"top", "bottom", "left", "right", "front", "back"}


def test_master_angle_hits_most_unique_meshes(two_box_glb):
    """The master angle must see the most unique components simultaneously.
    For two boxes separated on X axis, front/back sees both side-by-side
    (each ray in the X-grid hits a different box). Left/right only return
    the nearer box as the first intersection per ray (single-hit cast)."""
    analyzer = GeometryAnalyzer()
    meshes = analyzer.load(str(two_box_glb))
    direction = analyzer.master_angle(meshes)
    assert direction in {"front", "back"}


def test_explosion_vectors_count_matches_meshes(two_box_glb):
    analyzer = GeometryAnalyzer()
    meshes = analyzer.load(str(two_box_glb))
    vectors = analyzer.explosion_vectors(meshes, scalar=1.5)
    assert len(vectors) == len(meshes)


def test_explosion_vectors_are_nonzero(two_box_glb):
    analyzer = GeometryAnalyzer()
    meshes = analyzer.load(str(two_box_glb))
    vectors = analyzer.explosion_vectors(meshes, scalar=1.5)
    for v in vectors.values():
        assert np.linalg.norm(v) > 1e-6


def test_explosion_vectors_point_outward(two_box_glb):
    """v = centroid_component - centroid_assembly, scaled by E.
    dot(v, centroid_component - centroid_assembly) must be > 0."""
    analyzer = GeometryAnalyzer()
    meshes = analyzer.load(str(two_box_glb))
    vectors = analyzer.explosion_vectors(meshes, scalar=1.5)
    assembly_centroid = np.mean([m.centroid for m in meshes], axis=0)
    for i, mesh in enumerate(meshes):
        direction = mesh.centroid - assembly_centroid
        dot = np.dot(vectors[i], direction)
        assert dot > 0, f"Mesh {i} explosion vector points inward"


def test_explosion_vectors_scale_with_scalar(two_box_glb):
    analyzer = GeometryAnalyzer()
    meshes = analyzer.load(str(two_box_glb))
    v1 = analyzer.explosion_vectors(meshes, scalar=1.0)
    v2 = analyzer.explosion_vectors(meshes, scalar=2.0)
    for i in v1:
        ratio = np.linalg.norm(v2[i]) / np.linalg.norm(v1[i])
        assert abs(ratio - 2.0) < 1e-6
