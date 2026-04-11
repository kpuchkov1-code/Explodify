# pipeline/phase2_snapshots.py
import math
from pathlib import Path
from typing import List

import numpy as np
import trimesh
from PIL import Image

from pipeline.models import FrameSet, NamedMesh, PipelineMetadata

# Default orbit range: 10° per step is safe for FAL/Kling interpolation.
# Maximum safe total orbit is 60° (15° per step × 4 steps).
DEFAULT_ORBIT_RANGE_DEG = 40.0
EXPLOSION_FRACTIONS = [0.0, 0.25, 0.5, 0.75, 1.0]
FRAME_NAMES = ["frame_a", "frame_b", "frame_c", "frame_d", "frame_e"]
RESOLUTION = (1024, 768)

_ANGLE_TO_CAM_DIR = {
    # Cardinal faces
    "top":          np.array([ 0.0,  1.0,  0.3]),
    "bottom":       np.array([ 0.0, -1.0,  0.3]),
    "left":         np.array([-1.0,  0.3,  0.3]),
    "right":        np.array([ 1.0,  0.3,  0.3]),
    "front":        np.array([ 0.3,  0.3,  1.0]),
    "back":         np.array([ 0.3,  0.3, -1.0]),
    # 45-degree diagonals
    "front-left":   np.array([-0.7,  0.3,  0.7]),
    "front-right":  np.array([ 0.7,  0.3,  0.7]),
    "top-front":    np.array([ 0.3,  0.7,  0.7]),
    "top-back":     np.array([ 0.3,  0.7, -0.7]),
    "top-left":     np.array([-0.7,  0.7,  0.3]),
    "top-right":    np.array([ 0.7,  0.7,  0.3]),
    "bottom-front": np.array([ 0.3, -0.7,  0.7]),
    "bottom-back":  np.array([ 0.3, -0.7, -0.7]),
}


VIDEO_FRAMES = 72          # frames for the assembled video (3s @ 24 fps)
VIDEO_RESOLUTION = (1920, 1080)  # render resolution for video frames


class SnapshotRenderer:
    """Phase 2: Render 5 PNG keyframes + 72-frame video sequence."""

    def render_video_frames(
        self,
        named_meshes: List[NamedMesh],
        explosion_vectors: dict,
        master_angle: str,
        output_dir: Path,
        num_frames: int = VIDEO_FRAMES,
        orbit_range_deg: float = DEFAULT_ORBIT_RANGE_DEG,
        rotation_offset_deg: float = 0.0,
    ) -> Path:
        """Render num_frames PNGs at VIDEO_RESOLUTION for ffmpeg assembly (Phase 3).

        Frames are named video_0000.png … video_NNNN.png.
        Explosion and orbit are linearly interpolated from 0 to 100% across all frames.

        Returns:
            output_dir path containing the frames.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        meshes = [nm.mesh for nm in named_meshes]
        cam_dir = _pick_camera_direction(meshes, master_angle)

        for i in range(num_frames):
            t = i / max(num_frames - 1, 1)   # 0.0 … 1.0
            fraction = t
            orbit_deg = orbit_range_deg * t

            exploded = self._apply_explosion(meshes, explosion_vectors, fraction)
            img = self._render_scene(
                exploded, cam_dir, orbit_deg,
                up_rotation_deg=rotation_offset_deg,
                resolution=VIDEO_RESOLUTION,
            )
            img.save(str(output_dir / f"video_{i:04d}.png"))

            if i % 18 == 0:
                print(f"[Phase 3 render] {i + 1}/{num_frames} frames")

        return output_dir

    def render(
        self,
        named_meshes: List[NamedMesh],
        explosion_vectors: dict,
        master_angle: str,
        output_dir: Path,
        scalar: float,
        source_format: str = "",
        orbit_range_deg: float = DEFAULT_ORBIT_RANGE_DEG,
        rotation_offset_deg: float = 0.0,
    ) -> FrameSet:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        meshes = [nm.mesh for nm in named_meshes]
        cam_dir = _pick_camera_direction(meshes, master_angle)

        # Distribute orbit evenly across frames: [0, r/4, r/2, 3r/4, r]
        n = len(FRAME_NAMES)
        camera_angles = [orbit_range_deg * i / (n - 1) for i in range(n)]

        frame_paths = []
        for fraction, orbit_deg, name in zip(
            EXPLOSION_FRACTIONS, camera_angles, FRAME_NAMES
        ):
            exploded = self._apply_explosion(meshes, explosion_vectors, fraction)
            img = self._render_scene(
                exploded, cam_dir, orbit_deg, up_rotation_deg=rotation_offset_deg,
            )
            out_path = output_dir / f"{name}.png"
            img.save(str(out_path))
            frame_paths.append(out_path)

        metadata = PipelineMetadata(
            master_angle=master_angle,
            explosion_scalar=scalar,
            component_count=len(named_meshes),
            camera_angles_deg=camera_angles,
            source_format=source_format,
            component_names=[nm.name for nm in named_meshes],
        )
        return FrameSet(
            frame_a=frame_paths[0],
            frame_b=frame_paths[1],
            frame_c=frame_paths[2],
            frame_d=frame_paths[3],
            frame_e=frame_paths[4],
            metadata=metadata,
        )

    def _apply_explosion(
        self,
        meshes: List[trimesh.Trimesh],
        explosion_vectors: dict,
        fraction: float,
    ) -> List[trimesh.Trimesh]:
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
        cam_dir: np.ndarray,
        orbit_deg: float,
        up_rotation_deg: float = 0.0,
        resolution: tuple[int, int] | None = None,
    ) -> Image.Image:
        import pyrender

        pr_scene = pyrender.Scene(
            bg_color=[0.0, 0.0, 0.0, 0.0],
            ambient_light=[0.35, 0.35, 0.35],
        )

        for idx, mesh in enumerate(meshes):
            mat = _extract_material(mesh, idx)
            pr_mesh = pyrender.Mesh.from_trimesh(mesh, material=mat, smooth=False)
            pr_scene.add(pr_mesh)

        all_verts = np.vstack([m.vertices for m in meshes])
        # Use assembly centroid (mean of component centroids) as camera target.
        # This focuses on the main part cluster rather than being pulled toward
        # extremes of long features like watch straps.
        center = np.mean([m.centroid for m in meshes], axis=0)

        base_dir = cam_dir / np.linalg.norm(cam_dir)
        orbit_rad = math.radians(orbit_deg)
        cos_o, sin_o = math.cos(orbit_rad), math.sin(orbit_rad)
        orbited = np.array([
            base_dir[0] * cos_o - base_dir[2] * sin_o,
            base_dir[1],
            base_dir[0] * sin_o + base_dir[2] * cos_o,
        ])
        orbited /= np.linalg.norm(orbited)

        # Camera distance is based on the 2D footprint in the camera view plane,
        # not the full 3D diagonal.  This prevents long straps from causing the
        # camera to be placed so far away that the watch case appears tiny.
        depth = all_verts @ orbited
        footprint = all_verts - np.outer(depth, orbited)
        scale = np.linalg.norm(footprint.max(axis=0) - footprint.min(axis=0))

        cam_pos = center + orbited * scale * 2.0
        up_hint = _compute_up_vector(orbited, up_rotation_deg)
        cam_pose = _look_at(cam_pos, center, up_hint=up_hint)

        res = resolution if resolution is not None else RESOLUTION
        cam = pyrender.PerspectiveCamera(
            yfov=np.pi / 4.0,
            aspectRatio=res[0] / res[1],
        )
        pr_scene.add(cam, pose=cam_pose)

        key_light = pyrender.DirectionalLight(color=[1.0, 0.97, 0.9], intensity=4.0)
        pr_scene.add(key_light, pose=cam_pose)
        fill_pos = center + np.array([-orbited[0], orbited[1] + 0.5, -orbited[2]]) * scale
        fill_pose = _look_at(fill_pos, center)
        fill_light = pyrender.DirectionalLight(color=[0.7, 0.8, 1.0], intensity=2.0)
        pr_scene.add(fill_light, pose=fill_pose)

        offscreen = pyrender.OffscreenRenderer(*res)
        try:
            color, _ = offscreen.render(
                pr_scene,
                flags=pyrender.RenderFlags.RGBA,
            )
            return Image.fromarray(color, mode="RGBA")
        finally:
            offscreen.delete()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def render_preview_frame(
    meshes: List[trimesh.Trimesh],
    cam_dir: np.ndarray,
    resolution: tuple[int, int] = (512, 384),
) -> Image.Image:
    """Render a single preview frame from the given camera direction.

    Used by orientation_preview to produce the 6-face orientation grid.
    No explosion applied — meshes are shown fully assembled.
    """
    renderer = SnapshotRenderer()
    return renderer._render_scene(
        meshes, cam_dir, orbit_deg=0.0, up_rotation_deg=0.0, resolution=resolution
    )


def _compute_up_vector(cam_dir: np.ndarray, rotation_deg: float) -> np.ndarray:
    """Compute camera up vector rotated around the viewing direction axis.

    A rotation_deg of 0 gives the natural world-up orientation.
    90 rotates the camera frame 90 degrees clockwise from the viewer's perspective.
    """
    axis = cam_dir / np.linalg.norm(cam_dir)
    world_up = np.array([0.0, 1.0, 0.0])
    if abs(np.dot(axis, world_up)) > 0.99:
        world_up = np.array([1.0, 0.0, 0.0])
    angle = math.radians(rotation_deg)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    # Rodrigues rotation formula: rotate world_up around axis
    rotated = (
        world_up * cos_a
        + np.cross(axis, world_up) * sin_a
        + axis * np.dot(axis, world_up) * (1.0 - cos_a)
    )
    norm = np.linalg.norm(rotated)
    if norm < 1e-8:
        return world_up
    return rotated / norm


def _pick_camera_direction(meshes: List[trimesh.Trimesh], master_angle: str) -> np.ndarray:
    """Return a camera unit direction vector based on the master_angle."""
    return _ANGLE_TO_CAM_DIR.get(master_angle, np.array([0.5, 0.4, 1.0]))


def _extract_material(mesh: trimesh.Trimesh, idx: int):
    """Extract a pyrender MetallicRoughnessMaterial from a trimesh visual."""
    import pyrender

    _FALLBACK_COLORS = [
        [0.85, 0.25, 0.25, 1.0],
        [0.25, 0.50, 0.85, 1.0],
        [0.25, 0.75, 0.35, 1.0],
        [0.85, 0.65, 0.15, 1.0],
        [0.55, 0.55, 0.55, 1.0],
        [0.25, 0.75, 0.75, 1.0],
    ]

    color = None

    # TextureVisuals with SimpleMaterial (OBJ/MTL)
    if hasattr(mesh, "visual"):
        vis = mesh.visual
        if hasattr(vis, "material"):
            mat = vis.material
            # SimpleMaterial.diffuse is an RGBA uint8 array [R,G,B,A]
            if hasattr(mat, "diffuse") and mat.diffuse is not None:
                d = np.asarray(mat.diffuse, dtype=float)
                if d.max() > 1.0:
                    d = d / 255.0
                color = d[:4].tolist() if len(d) >= 4 else [*d[:3].tolist(), 1.0]
            elif hasattr(mat, "main_color") and mat.main_color is not None:
                d = np.asarray(mat.main_color, dtype=float)
                if d.max() > 1.0:
                    d = d / 255.0
                color = d[:4].tolist() if len(d) >= 4 else [*d[:3].tolist(), 1.0]

        # ColorVisuals — per-face or per-vertex colors
        elif hasattr(vis, "vertex_colors") and vis.vertex_colors is not None:
            vc = np.asarray(vis.vertex_colors, dtype=float)
            if vc.max() > 1.0:
                vc = vc / 255.0
            mean_color = vc.mean(axis=0)
            color = mean_color[:4].tolist() if len(mean_color) >= 4 else [*mean_color[:3].tolist(), 1.0]

    if color is None:
        color = _FALLBACK_COLORS[idx % len(_FALLBACK_COLORS)]

    return pyrender.MetallicRoughnessMaterial(
        baseColorFactor=color,
        metallicFactor=0.3,
        roughnessFactor=0.5,
        alphaMode="OPAQUE",
    )


def _look_at(
    eye: np.ndarray,
    target: np.ndarray,
    up_hint: np.ndarray | None = None,
) -> np.ndarray:
    forward = target - eye
    forward /= np.linalg.norm(forward)
    if up_hint is not None:
        world_up = up_hint / np.linalg.norm(up_hint)
    else:
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
