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
    b"PK\x03\x04": ".3mf",
    b"solid ": ".stl",
}

_MAX_COMPONENTS = 100

_TOO_MANY_COMPONENTS_HELP = """
This file contains {count} components, which exceeds the limit of {limit}.

This usually means the STEP was exported as a single body without an assembly
tree (every face becomes its own compound). Re-export with assembly structure:

  SolidWorks:   File -> Save As -> STEP AP214, check "Export as assembly"
  Fusion 360:   File -> Export -> STEP, ensure components are not merged
  Onshape:      Export -> STEP, select "Export each part as a separate body"
"""


def load_assembly(path: str) -> List[NamedMesh]:
    """Load a CAD assembly file and return named component meshes.

    Supports STEP (.step/.stp) and mesh formats (GLB, OBJ, STL, PLY, 3MF).

    Args:
        path: Path to the assembly file.

    Returns:
        List of NamedMesh, one per component in the assembly.

    Raises:
        FileNotFoundError: If the path does not exist.
        UnsupportedFormatError: If the format is not supported or has too many components.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    fmt = _detect_format(p)
    if fmt not in ALL_SUPPORTED_FORMATS:
        raise UnsupportedFormatError(
            f"Unsupported format '{fmt}' for file: {path}\n\n{UNSUPPORTED_FORMAT_HELP}"
        )

    if fmt in CASCADIO_FORMATS:
        loaded = _load_step(p)
    else:
        loaded = trimesh.load(str(p), force="scene")

    named = _scene_to_named_meshes(loaded)

    if len(named) > _MAX_COMPONENTS:
        raise UnsupportedFormatError(
            _TOO_MANY_COMPONENTS_HELP.format(count=len(named), limit=_MAX_COMPONENTS)
        )

    return named


def _load_step(p: Path) -> trimesh.Scene:
    """Convert STEP to GLB via cascadio then load with trimesh."""
    import cascadio, tempfile, os

    with tempfile.TemporaryDirectory() as tmp:
        glb_path = os.path.join(tmp, "converted.glb")
        ret = cascadio.step_to_glb(
            str(p), glb_path,
            tol_linear=0.1,
            tol_angular=0.5,
            merge_primitives=False,
        )
        if ret != 0:
            raise RuntimeError(f"cascadio failed (code {ret}) converting {p}")
        return trimesh.load(glb_path, force="scene")


def _detect_format(p: Path) -> str:
    """Determine format by extension, falling back to magic-byte sniffing."""
    ext = p.suffix.lower()
    if ext in ALL_SUPPORTED_FORMATS:
        return ext

    with p.open("rb") as f:
        header = f.read(8)
    for magic, detected_ext in _MAGIC.items():
        if header.startswith(magic):
            return detected_ext

    return ext


def _scene_to_named_meshes(scene) -> List[NamedMesh]:
    """Extract non-empty trimesh.Trimesh objects from a loaded scene."""
    if isinstance(scene, trimesh.Trimesh):
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
            "No geometry found in file. "
            "If this is a STEP assembly, ensure it contains solid bodies "
            "(not just sketch geometry or empty components)."
        )

    return meshes
