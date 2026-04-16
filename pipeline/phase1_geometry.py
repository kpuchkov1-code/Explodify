# pipeline/phase1_geometry.py
from pathlib import Path
from typing import List

import numpy as np
import trimesh

from pipeline.format_loader import load_assembly
from pipeline.models import NamedMesh


class GeometryAnalyzer:
    """Phase 1: Load a CAD file and compute explosion vectors."""

    def load(self, path: str) -> List[NamedMesh]:
        """Load a CAD/mesh file and return a list of named component meshes.

        Delegates to format_loader which handles STEP, GLB, OBJ, STL, etc.

        Args:
            path: Path to .step, .stp, .glb, .obj, .stl, or other supported file.

        Returns:
            List of NamedMesh with one entry per non-empty assembly component.

        Raises:
            FileNotFoundError: If path does not exist.
            UnsupportedFormatError: If the format is not supported.
        """
        return load_assembly(path)

    def reorient(self, named_meshes: List[NamedMesh]) -> List[NamedMesh]:
        """Rotate the assembly so its longest bounding-box axis aligns with Y (up).

        Tinkercad and some CAD exporters place models lying on their side.
        This rotates the whole assembly 90° so the longest dimension stands
        vertically, giving the renderer a natural upright orientation.

        Args:
            named_meshes: Component meshes (from load()).

        Returns:
            New list of NamedMesh with meshes rotated in place.  Returns the
            original list unchanged if the longest axis is already Y.
        """
        meshes = [nm.mesh for nm in named_meshes]
        all_verts = np.vstack([m.vertices for m in meshes])
        extents = all_verts.max(axis=0) - all_verts.min(axis=0)  # [X_ext, Y_ext, Z_ext]
        longest = int(np.argmax(extents))

        if longest == 1:
            return named_meshes  # already upright

        if longest == 2:  # Z longest — rotate -90 deg around X
            angle, axis = -np.pi / 2, np.array([1.0, 0.0, 0.0])
        else:             # X longest — rotate  90 deg around Z
            angle, axis = np.pi / 2, np.array([0.0, 0.0, 1.0])

        R = trimesh.transformations.rotation_matrix(angle, axis)
        return [
            NamedMesh(name=nm.name, mesh=nm.mesh.copy().apply_transform(R))
            for nm in named_meshes
        ]

    def axis_directions(self, named_meshes: List[NamedMesh]) -> dict:
        """Return unit vectors for the longest and shortest bounding-box axes.

        Used by the /preview endpoint to expose axis information to the frontend
        for the interactive Three.js orientation viewer.

        Returns:
            Dict with 'longest' and 'shortest' keys, each a [x, y, z] list.
        """
        meshes = [nm.mesh for nm in named_meshes]
        all_verts = np.vstack([m.vertices for m in meshes])
        extents = all_verts.max(axis=0) - all_verts.min(axis=0)
        axis_order = np.argsort(extents)
        shortest_idx = int(axis_order[0])
        longest_idx = int(axis_order[2])

        unit = np.eye(3)
        return {
            "longest": unit[longest_idx].tolist(),
            "shortest": unit[shortest_idx].tolist(),
        }

    def dual_axis_explosion_vectors(
        self, named_meshes: List[NamedMesh], scalar: float
    ) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray]]:
        """Compute two explosion variants: along the longest and shortest axes.

        Returns:
            (longest_axis_vectors, shortest_axis_vectors)
        """
        meshes = [nm.mesh for nm in named_meshes]
        all_verts = np.vstack([m.vertices for m in meshes])
        extents = all_verts.max(axis=0) - all_verts.min(axis=0)
        axis_order = np.argsort(extents)
        shortest_idx = int(axis_order[0])
        longest_idx = int(axis_order[2])

        assembly_centroid = np.mean([m.centroid for m in meshes], axis=0)
        boost = 1.25

        def _axis_vectors(axis_idx: int) -> dict[int, np.ndarray]:
            result: dict[int, np.ndarray] = {}
            for i, mesh in enumerate(meshes):
                diff = mesh.centroid - assembly_centroid
                projected = np.zeros(3)
                projected[axis_idx] = diff[axis_idx] * scalar * boost
                if abs(projected[axis_idx]) < 1e-6:
                    projected[axis_idx] = (
                        scalar * boost * 0.3
                        * (1.0 if i % 2 == 0 else -1.0)
                    )
                result[i] = projected
            return result

        return _axis_vectors(longest_idx), _axis_vectors(shortest_idx)
