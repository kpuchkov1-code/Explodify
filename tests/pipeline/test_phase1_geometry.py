# tests/pipeline/test_phase1_geometry.py
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
