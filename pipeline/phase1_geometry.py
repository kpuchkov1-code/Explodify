# pipeline/phase1_geometry.py
from pathlib import Path
from typing import List

import numpy as np
import trimesh


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

    def load(self, path: str) -> List[trimesh.Trimesh]:
        """Load a CAD/mesh file and return a flat list of component meshes.

        Args:
            path: Path to .glb, .obj, or .stl file.

        Returns:
            List of trimesh.Trimesh, one per component in the assembly.

        Raises:
            FileNotFoundError: If path does not exist.
        """
        if not Path(path).exists():
            raise FileNotFoundError(f"CAD file not found: {path}")

        loaded = trimesh.load(path, force="scene")

        if isinstance(loaded, trimesh.Scene):
            meshes = [
                geom for geom in loaded.geometry.values()
                if isinstance(geom, trimesh.Trimesh) and len(geom.faces) > 0
            ]
        elif isinstance(loaded, trimesh.Trimesh):
            meshes = [loaded]
        else:
            meshes = list(loaded.geometry.values())

        return meshes

    def master_angle(self, meshes: List[trimesh.Trimesh]) -> str:
        """Find the cardinal direction that hits the highest number of unique mesh IDs.

        Args:
            meshes: List of component meshes (from load()).

        Returns:
            Direction name: one of "top", "bottom", "left", "right", "front", "back".
        """
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

        assembly_centroid = np.mean([m.centroid for m in meshes], axis=0)

        # Compute assembly bounding box for grid scaling
        all_verts = np.vstack([m.vertices for m in meshes])
        bounds_min = all_verts.min(axis=0)
        bounds_max = all_verts.max(axis=0)
        extents = bounds_max - bounds_min
        max_extent = max(extents.max(), 0.1)

        best_direction = "front"
        best_count = -1

        for name, (offset, ray_dir) in self._DIRECTIONS.items():
            # Build two axes perpendicular to ray_dir for the ray grid
            # Choose a stable up vector not parallel to ray_dir
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

            # Scale offset to be far enough from the assembly
            scaled_offset = ray_dir * -max_extent * 4
            origins = assembly_centroid + scaled_offset + grid
            directions = np.tile(ray_dir, (25, 1))

            try:
                _, index_ray, index_tri = combined.ray.intersects_id(
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
        self, meshes: List[trimesh.Trimesh], scalar: float
    ) -> dict[int, np.ndarray]:
        """Compute outward explosion vector for each mesh component.

        v_i = (centroid_i - centroid_assembly) * scalar

        Args:
            meshes: List of component meshes.
            scalar: Explosion multiplier E.

        Returns:
            Dict mapping mesh index -> 3D numpy displacement vector.
        """
        assembly_centroid = np.mean([m.centroid for m in meshes], axis=0)
        return {
            i: (mesh.centroid - assembly_centroid) * scalar
            for i, mesh in enumerate(meshes)
        }
