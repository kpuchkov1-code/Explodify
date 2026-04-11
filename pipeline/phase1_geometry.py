# pipeline/phase1_geometry.py
from pathlib import Path
from typing import List

import numpy as np
import trimesh

from pipeline.format_loader import load_assembly
from pipeline.models import NamedMesh


class GeometryAnalyzer:
    """Phase 1: Load a CAD file and compute optimal viewing angle + explosion vectors."""

    # Cardinal direction definitions: name -> (origin offset, ray direction)
    _DIRECTIONS = {
        "top":    (np.array([0,  10, 0], dtype=float), np.array([ 0, -1,  0], dtype=float)),
        "bottom": (np.array([0, -10, 0], dtype=float), np.array([ 0,  1,  0], dtype=float)),
        "left":   (np.array([-10, 0, 0], dtype=float), np.array([ 1,  0,  0], dtype=float)),
        "right":  (np.array([ 10, 0, 0], dtype=float), np.array([-1,  0,  0], dtype=float)),
        "front":  (np.array([0,  0, 10], dtype=float), np.array([ 0,  0, -1], dtype=float)),
        "back":   (np.array([0,  0,-10], dtype=float), np.array([ 0,  0,  1], dtype=float)),
    }

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

    def master_angle(self, named_meshes: List[NamedMesh]) -> str:
        """Find the cardinal direction that hits the highest number of unique components.

        Args:
            named_meshes: Component meshes (from load()).

        Returns:
            Direction name: one of "top", "bottom", "left", "right", "front", "back".
        """
        meshes = [nm.mesh for nm in named_meshes]

        all_vertices = []
        all_faces = []
        face_to_mesh = []
        vertex_offset = 0

        for idx, mesh in enumerate(meshes):
            all_vertices.append(mesh.vertices)
            all_faces.append(mesh.faces + vertex_offset)
            face_to_mesh.extend([idx] * len(mesh.faces))
            vertex_offset += len(mesh.vertices)

        combined = trimesh.Trimesh(
            vertices=np.vstack(all_vertices),
            faces=np.vstack(all_faces),
            process=False,
        )
        face_to_mesh = np.array(face_to_mesh)

        all_verts = np.vstack(all_vertices)
        bounds_min = all_verts.min(axis=0)
        bounds_max = all_verts.max(axis=0)
        max_extent = max((bounds_max - bounds_min).max(), 0.1)

        assembly_centroid = np.mean([m.centroid for m in meshes], axis=0)

        best_direction = "front"
        best_count = -1

        for name, (offset, ray_dir) in self._DIRECTIONS.items():
            up = np.array([0.0, 1.0, 0.0])
            if abs(np.dot(ray_dir, up)) > 0.9:
                up = np.array([1.0, 0.0, 0.0])
            axis_u = np.cross(ray_dir, up)
            axis_u /= np.linalg.norm(axis_u)
            axis_v = np.cross(ray_dir, axis_u)
            axis_v /= np.linalg.norm(axis_v)

            span = max_extent * 0.6
            grid = np.array(
                [[du * axis_u + dv * axis_v
                  for du in np.linspace(-span, span, 5)]
                 for dv in np.linspace(-span, span, 5)],
                dtype=float,
            ).reshape(25, 3)

            scaled_offset = ray_dir * -max_extent * 4
            origins = assembly_centroid + scaled_offset + grid
            directions = np.tile(ray_dir, (25, 1))

            try:
                _, _index_ray, index_tri = combined.ray.intersects_id(
                    ray_origins=origins,
                    ray_directions=directions,
                    multiple_hits=False,
                )
            except Exception:
                continue

            unique_meshes_hit = len(set(face_to_mesh[index_tri]))
            if unique_meshes_hit > best_count:
                best_count = unique_meshes_hit
                best_direction = name

        return best_direction

    def explosion_vectors(
        self, named_meshes: List[NamedMesh], scalar: float
    ) -> dict[int, np.ndarray]:
        """Compute outward explosion vector for each mesh component.

        v_i = (centroid_i - centroid_assembly) * scalar

        Args:
            named_meshes: Component meshes (from load()).
            scalar: Explosion multiplier E.

        Returns:
            Dict mapping mesh index -> 3D numpy displacement vector.
        """
        meshes = [nm.mesh for nm in named_meshes]
        assembly_centroid = np.mean([m.centroid for m in meshes], axis=0)
        return {
            i: (mesh.centroid - assembly_centroid) * scalar
            for i, mesh in enumerate(meshes)
        }
