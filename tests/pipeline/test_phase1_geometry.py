# tests/pipeline/test_phase1_geometry.py
import numpy as np
import pytest
from pipeline.models import NamedMesh, UnsupportedFormatError
from pipeline.phase1_geometry import GeometryAnalyzer


def test_load_returns_named_meshes(two_box_glb):
    analyzer = GeometryAnalyzer()
    result = analyzer.load(str(two_box_glb))
    assert isinstance(result, list)
    assert len(result) >= 2
    assert all(isinstance(nm, NamedMesh) for nm in result)
    assert all(nm.name for nm in result)


def test_load_nonexistent_file_raises():
    analyzer = GeometryAnalyzer()
    with pytest.raises(FileNotFoundError):
        analyzer.load("does_not_exist.glb")


def test_load_unsupported_format_raises(tmp_path):
    bad = tmp_path / "assembly.sldasm"
    bad.write_bytes(b"\x00" * 16)
    analyzer = GeometryAnalyzer()
    with pytest.raises(UnsupportedFormatError):
        analyzer.load(str(bad))


def test_master_angle_returns_valid_direction(two_box_glb):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    direction = analyzer.master_angle(named_meshes)
    assert direction in {"top", "bottom", "left", "right", "front", "back"}


def test_master_angle_hits_most_unique_meshes(two_box_glb):
    """For two boxes separated on the X axis the optimal direction must see
    both components.  Any view where both boxes appear side-by-side qualifies:
    top/bottom (XZ footprint), front/back (XY footprint).  Left/right aim
    along X so the farther box is occluded — those are incorrect answers."""
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    direction = analyzer.master_angle(named_meshes)
    assert direction in {"top", "bottom", "front", "back"}


def test_explosion_vectors_count_matches_meshes(two_box_glb):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    vectors = analyzer.explosion_vectors(named_meshes, scalar=1.5)
    assert len(vectors) == len(named_meshes)


def test_explosion_vectors_are_nonzero(two_box_glb):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    vectors = analyzer.explosion_vectors(named_meshes, scalar=1.5)
    for v in vectors.values():
        assert np.linalg.norm(v) > 1e-6


def test_explosion_vectors_point_outward(two_box_glb):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    vectors = analyzer.explosion_vectors(named_meshes, scalar=1.5)
    meshes = [nm.mesh for nm in named_meshes]
    assembly_centroid = np.mean([m.centroid for m in meshes], axis=0)
    for i, mesh in enumerate(meshes):
        direction = mesh.centroid - assembly_centroid
        assert np.dot(vectors[i], direction) > 0, f"Mesh {i} explosion vector points inward"


def test_explosion_vectors_scale_with_scalar(two_box_glb):
    analyzer = GeometryAnalyzer()
    named_meshes = analyzer.load(str(two_box_glb))
    v1 = analyzer.explosion_vectors(named_meshes, scalar=1.0)
    v2 = analyzer.explosion_vectors(named_meshes, scalar=2.0)
    for i in v1:
        ratio = np.linalg.norm(v2[i]) / np.linalg.norm(v1[i])
        assert abs(ratio - 2.0) < 1e-6
