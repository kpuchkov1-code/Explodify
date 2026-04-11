# pipeline/format_loader.py
from pathlib import Path
from typing import List

import trimesh

from pipeline.models import (
    ALL_SUPPORTED_FORMATS,
    CASCADIO_FORMATS,
    NamedMesh,
    UnsupportedFormatError,
    UNSUPPORTED_FORMAT_HELP,
)

# Magic bytes for format detection when extension is missing or wrong
_MAGIC = {
    b"glTF": ".glb",
    b"PK\x03\x04": ".3mf",   # ZIP-based (3MF, also OBJ zips)
    b"solid ": ".stl",        # ASCII STL
}


def load_assembly(path: str) -> List[NamedMesh]:
    """Load a CAD assembly file and return named component meshes.

    Supports STEP (.step/.stp) and mesh formats (GLB, OBJ, STL, PLY, 3MF).
    STEP files are converted via cascadio (OpenCASCADE) which preserves
    the assembly tree and per-part names.

    Args:
        path: Path to the assembly file.

    Returns:
        List of NamedMesh, one per non-empty component in the assembly.
        Single-mesh files return a list with one entry named "mesh_0".

    Raises:
        FileNotFoundError: If the path does not exist.
        UnsupportedFormatError: If the format is not supported.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    fmt = _detect_format(p)
    if fmt not in ALL_SUPPORTED_FORMATS:
        raise UnsupportedFormatError(
            f"Unsupported format '{fmt}' for file: {path}\n\n{UNSUPPORTED_FORMAT_HELP}"
        )

    loaded = trimesh.load(str(p), force="scene")
    return _scene_to_named_meshes(loaded, fmt)


def _detect_format(p: Path) -> str:
    """Determine format by extension, falling back to magic-byte sniffing."""
    ext = p.suffix.lower()
    if ext in ALL_SUPPORTED_FORMATS:
        return ext

    # No recognised extension — sniff the first 8 bytes
    with p.open("rb") as f:
        header = f.read(8)
    for magic, detected_ext in _MAGIC.items():
        if header.startswith(magic):
            return detected_ext

    return ext  # return as-is; UnsupportedFormatError will fire if unknown


def _scene_to_named_meshes(scene: trimesh.Scene, fmt: str) -> List[NamedMesh]:
    """Extract non-empty trimesh.Trimesh objects from a loaded scene."""
    if isinstance(scene, trimesh.Trimesh):
        # Single mesh — wrap it
        if len(scene.faces) == 0:
            raise ValueError("Loaded file contains no geometry.")
        return [NamedMesh(name="mesh_0", mesh=scene)]

    if not isinstance(scene, trimesh.Scene):
        raise ValueError(f"Unexpected trimesh result type: {type(scene)}")

    meshes = [
        NamedMesh(name=name, mesh=geom)
        for name, geom in scene.geometry.items()
        if isinstance(geom, trimesh.Trimesh) and len(geom.faces) > 0
    ]

    if not meshes:
        raise ValueError(
            f"No geometry found in file. "
            f"If this is a STEP assembly, ensure it contains solid bodies "
            f"(not just sketch geometry or empty components)."
        )

    return meshes
