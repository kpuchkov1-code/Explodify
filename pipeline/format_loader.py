# pipeline/format_loader.py
from pathlib import Path
from typing import List

import numpy as np
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

# When a STEP/GLB has more fragments than this, cluster them into groups
_FRAGMENT_CLUSTER_THRESHOLD = 50
# Number of spatial clusters to produce when over the threshold
_N_CLUSTERS = 8


def load_assembly(path: str) -> List[NamedMesh]:
    """Load a CAD assembly file and return named component meshes.

    Supports STEP (.step/.stp) and mesh formats (GLB, OBJ, STL, PLY, 3MF).

    For STEP files: cascadio (OpenCASCADE) converts to GLB which preserves
    per-part names. If the STEP has no assembly structure (exported as a
    single body meshed into many face-level fragments), the fragments are
    spatially clustered into logical groups automatically.

    Args:
        path: Path to the assembly file.

    Returns:
        List of NamedMesh, one per component (or cluster) in the assembly.

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

    if fmt in CASCADIO_FORMATS:
        loaded = _load_step(p)
    else:
        loaded = trimesh.load(str(p), force="scene")

    named = _scene_to_named_meshes(loaded, fmt)

    if len(named) > _FRAGMENT_CLUSTER_THRESHOLD:
        named = _cluster_fragments(named)

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


def _scene_to_named_meshes(scene, fmt: str) -> List[NamedMesh]:
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


def _cluster_fragments(named: List[NamedMesh]) -> List[NamedMesh]:
    """Spatially cluster many small fragments into N logical components.

    Uses k-means on mesh centroids. Fragments within each cluster are
    concatenated into a single NamedMesh named 'part_0', 'part_1', etc.

    Args:
        named: List of NamedMesh with more than _FRAGMENT_CLUSTER_THRESHOLD entries.

    Returns:
        List of _N_CLUSTERS NamedMesh entries (or fewer if some clusters are empty).
    """
    from sklearn.cluster import KMeans

    centroids = np.array([nm.mesh.centroid for nm in named])
    n_clusters = min(_N_CLUSTERS, len(named))

    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = km.fit_predict(centroids)

    clusters: dict[int, list[trimesh.Trimesh]] = {}
    for i, nm in enumerate(named):
        clusters.setdefault(labels[i], []).append(nm.mesh)

    result = []
    for cluster_id in sorted(clusters.keys()):
        meshes = clusters[cluster_id]
        if not meshes:
            continue
        merged = trimesh.util.concatenate(meshes)
        result.append(NamedMesh(name=f"part_{cluster_id}", mesh=merged))

    return result
