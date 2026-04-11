# tests/pipeline/test_format_loader.py
import pytest
from pathlib import Path
from pipeline.format_loader import load_assembly
from pipeline.models import NamedMesh, UnsupportedFormatError


def test_load_glb_returns_named_meshes(two_box_glb):
    result = load_assembly(str(two_box_glb))
    assert len(result) >= 2
    assert all(isinstance(nm, NamedMesh) for nm in result)
    assert all(nm.name for nm in result)
    assert all(len(nm.mesh.faces) > 0 for nm in result)


def test_load_preserves_component_names(two_box_glb):
    result = load_assembly(str(two_box_glb))
    names = [nm.name for nm in result]
    # GLB fixture has box_a and box_b
    assert "box_a" in names or "box_b" in names


def test_load_nonexistent_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_assembly(str(tmp_path / "nope.step"))


def test_load_sldasm_raises_unsupported(tmp_path):
    bad = tmp_path / "assembly.sldasm"
    bad.write_bytes(b"\xe4\xc9Ij" + b"\x00" * 12)
    with pytest.raises(UnsupportedFormatError) as exc_info:
        load_assembly(str(bad))
    assert "STEP" in str(exc_info.value)


def test_load_unknown_extension_raises(tmp_path):
    bad = tmp_path / "assembly.xyz123"
    bad.write_bytes(b"\x00" * 16)
    with pytest.raises(UnsupportedFormatError):
        load_assembly(str(bad))
