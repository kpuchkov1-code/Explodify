# pipeline/phase2_snapshots.py
import math
from pathlib import Path
from typing import List

import numpy as np
import trimesh
from PIL import Image

from pipeline.models import FrameSet, NamedMesh, PipelineMetadata

# Camera orbit angles per frame (degrees)
CAMERA_ANGLES_DEG = [0.0, 15.0, 30.0]
# Explosion fractions per frame
EXPLOSION_FRACTIONS = [0.0, 0.5, 1.0]
FRAME_NAMES = ["frame_a", "frame_b", "frame_c"]
RESOLUTION = (1024, 768)

# Direction -> base camera unit vector (camera looks at origin from this side)
_ANGLE_TO_CAM_DIR = {
    "top":    np.array([ 0.0,  1.0,  0.2]),
    "bottom": np.array([ 0.0, -1.0,  0.2]),
    "left":   np.array([-1.0,  0.2,  0.5]),
    "right":  np.array([ 1.0,  0.2,  0.5]),
    "front":  np.array([ 0.3,  0.3,  1.0]),
    "back":   np.array([ 0.3,  0.3, -1.0]),
}


class SnapshotRenderer:
    """Phase 2: Render 3 PNG keyframes at 0%, 50%, 100% explosion."""

    def render(
        self,
        named_meshes: List[NamedMesh],
        explosion_vectors: dict,
        master_angle: str,
        output_dir: Path,
        scalar: float,
        source_format: str = "",
    ) -> FrameSet:
        """Render 3 PNG snapshots and return a FrameSet.

        Args:
            named_meshes: Component meshes from GeometryAnalyzer.load().
            explosion_vectors: Per-mesh displacement vectors.
            master_angle: Optimal direction name from GeometryAnalyzer.master_angle().
            output_dir: Directory to write frame_a.png, frame_b.png, frame_c.png.
            scalar: Explosion scalar stored in metadata.
            source_format: File extension of the input (stored in metadata).

        Returns:
            FrameSet with paths to 3 PNGs and PipelineMetadata.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        meshes = [nm.mesh for nm in named_meshes]

        frame_paths = []
        for fraction, orbit_deg, name in zip(
            EXPLOSION_FRACTIONS, CAMERA_ANGLES_DEG, FRAME_NAMES
        ):
            exploded = self._apply_explosion(meshes, explosion_vectors, fraction)
            img = self._render_scene(exploded, master_angle, orbit_deg)
            out_path = output_dir / f"{name}.png"
            img.save(str(out_path))
            frame_paths.append(out_path)

        metadata = PipelineMetadata(
            master_angle=master_angle,
            explosion_scalar=scalar,
            component_count=len(named_meshes),
            camera_angles_deg=CAMERA_ANGLES_DEG,
            source_format=source_format,
            component_names=[nm.name for nm in named_meshes],
        )
        return FrameSet(
            frame_a=frame_paths[0],
            frame_b=frame_paths[1],
            frame_c=frame_paths[2],
            metadata=metadata,
        )

    def _apply_explosion(
        self,
        meshes: List[trimesh.Trimesh],
        explosion_vectors: dict,
        fraction: float,
    ) -> List[trimesh.Trimesh]:
        """Return copies of meshes translated by fraction * explosion_vector."""
        result = []
        for i, mesh in enumerate(meshes):
            copy = mesh.copy()
            if i in explosion_vectors:
                copy.apply_translation(explosion_vectors[i] * fraction)
            result.append(copy)
        return result

    def _render_scene(
        self,
        meshes: List[trimesh.Trimesh],
        master_angle: str,
        orbit_deg: float,
    ) -> Image.Image:
        """Render meshes to a PIL Image using pyrender OffscreenRenderer."""
        import pyrender

        pr_scene = pyrender.Scene(bg_color=[0.15, 0.15, 0.18, 1.0], ambient_light=[0.3, 0.3, 0.3])

        # Add each mesh with a distinct colour if it has none
        default_colors = [
            [0.85, 0.25, 0.25, 1.0],
            [0.25, 0.45, 0.85, 1.0],
            [0.25, 0.75, 0.35, 1.0],
            [0.85, 0.65, 0.15, 1.0],
            [0.65, 0.25, 0.85, 1.0],
            [0.25, 0.75, 0.75, 1.0],
        ]
        for idx, mesh in enumerate(meshes):
            try:
                pr_mesh = pyrender.Mesh.from_trimesh(mesh, smooth=False)
            except Exception:
                color = default_colors[idx % len(default_colors)]
                mat = pyrender.MetallicRoughnessMaterial(
                    baseColorFactor=color, metallicFactor=0.3, roughnessFactor=0.6
                )
                pr_mesh = pyrender.Mesh.from_trimesh(mesh, material=mat, smooth=False)
            pr_scene.add(pr_mesh)

        # Compute scene bounds for camera placement
        all_verts = np.vstack([m.vertices for m in meshes])
        center = (all_verts.max(axis=0) + all_verts.min(axis=0)) / 2
        scale = np.linalg.norm(all_verts.max(axis=0) - all_verts.min(axis=0))

        # Base camera direction from master_angle, then apply horizontal orbit
        base_dir = _ANGLE_TO_CAM_DIR.get(master_angle, np.array([0.5, 0.4, 1.0]))
        base_dir = base_dir / np.linalg.norm(base_dir)

        orbit_rad = math.radians(orbit_deg)
        cos_o, sin_o = math.cos(orbit_rad), math.sin(orbit_rad)
        orbited = np.array([
            base_dir[0] * cos_o - base_dir[2] * sin_o,
            base_dir[1],
            base_dir[0] * sin_o + base_dir[2] * cos_o,
        ])
        orbited /= np.linalg.norm(orbited)

        cam_pos = center + orbited * scale * 2.0
        cam_pose = self._look_at(cam_pos, center)

        cam = pyrender.PerspectiveCamera(yfov=np.pi / 4.0, aspectRatio=RESOLUTION[0] / RESOLUTION[1])
        pr_scene.add(cam, pose=cam_pose)

        # Key light + fill light
        key_light = pyrender.DirectionalLight(color=[1.0, 0.97, 0.9], intensity=4.0)
        pr_scene.add(key_light, pose=cam_pose)
        fill_pos = center + np.array([-orbited[0], orbited[1] + 0.5, -orbited[2]]) * scale
        fill_pose = self._look_at(fill_pos, center)
        fill_light = pyrender.DirectionalLight(color=[0.6, 0.7, 1.0], intensity=2.0)
        pr_scene.add(fill_light, pose=fill_pose)

        renderer = pyrender.OffscreenRenderer(*RESOLUTION)
        try:
            color, _ = renderer.render(pr_scene)
            return Image.fromarray(color)
        finally:
            renderer.delete()

    @staticmethod
    def _look_at(eye: np.ndarray, target: np.ndarray) -> np.ndarray:
        """Build a camera pose matrix (4x4) looking from eye toward target."""
        forward = target - eye
        forward /= np.linalg.norm(forward)

        world_up = np.array([0.0, 1.0, 0.0])
        if abs(np.dot(forward, world_up)) > 0.99:
            world_up = np.array([1.0, 0.0, 0.0])

        right = np.cross(forward, world_up)
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)

        pose = np.eye(4)
        pose[:3, 0] = right
        pose[:3, 1] = up
        pose[:3, 2] = -forward
        pose[:3, 3] = eye
        return pose
