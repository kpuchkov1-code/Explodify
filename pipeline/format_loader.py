# pipeline/format_loader.py
from pathlib import Path
from typing import List

import trimesh

from pipeline.models import (
    ALL_SUPPORTED_FORMATS,
    CASCADIO_FORMATS,
    TRIMESH_FORMATS,
    ZIP_FORMATS,
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
    elif fmt in ZIP_FORMATS:
        loaded = _load_zip(p)
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


def _load_zip(p: Path) -> trimesh.Scene:
    """Extract a zip archive and load the primary mesh file from it.

    Prefers OBJ (so MTL/texture siblings are co-located in the temp dir),
    then falls back to other trimesh-supported formats in priority order.
    Raises UnsupportedFormatError if no usable mesh file is found inside.
    """
    import tempfile, zipfile

    PRIORITY = [".obj", ".glb", ".gltf", ".stl", ".ply", ".off", ".3mf"]

    with zipfile.ZipFile(p, "r") as zf:
        names = zf.namelist()

    # Filter to supported mesh extensions, ignoring macOS __MACOSX cruft.
    candidates = [
        n for n in names
        if Path(n).suffix.lower() in TRIMESH_FORMATS
        and not n.startswith("__MACOSX")
        and not Path(n).name.startswith(".")
    ]

    if not candidates:
        raise UnsupportedFormatError(
            f"No supported mesh file found inside {p.name}. "
            f"Expected one of: {', '.join(sorted(TRIMESH_FORMATS))}"
        )

    # Pick by priority; fall back to first candidate if none matches.
    chosen = next(
        (c for ext in PRIORITY for c in candidates if Path(c).suffix.lower() == ext),
        candidates[0],
    )

    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(p, "r") as zf:
            zf.extractall(tmp)
        # Resolve the chosen file inside the extraction directory.
        mesh_path = Path(tmp) / chosen
        return trimesh.load(str(mesh_path), force="scene")


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
        return [NamedMesh(name="Part 1", mesh=scene)]

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

    return _sanitize_names(meshes)


import re as _re

_AUTO_NAME_PATTERN = _re.compile(
    r'^(color_|group_\d+_|mesh_\d*|obj_\d+)[-\d]*$',
    _re.IGNORECASE,
)


def _sanitize_names(meshes: List[NamedMesh]) -> List[NamedMesh]:
    """Replace auto-generated hash/index names with human-readable Part N labels.

    Trimesh keys OBJ geometry by the usemtl material name, which is often an
    auto-generated hash (e.g. 'color_-1040146473').  Replace these with
    'Part 1', 'Part 2', ... so the UI shows something useful.
    """
    all_auto = all(_AUTO_NAME_PATTERN.match(m.name) for m in meshes)
    if not all_auto:
        return meshes
    return [
        NamedMesh(name=f"Part {i + 1}", mesh=m.mesh)
        for i, m in enumerate(meshes)
    ]
