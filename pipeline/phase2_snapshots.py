# pipeline/phase2_snapshots.py
import math
from pathlib import Path
from typing import List

import numpy as np
import trimesh
from PIL import Image

from pipeline.models import NamedMesh

DEFAULT_ORBIT_RANGE_DEG = 40.0


def _smoothstep(t: float) -> float:
    """Cubic ease-in-out: 3t^2 - 2t^3.  Maps 0->0 and 1->1 with zero derivative at endpoints."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


_ANGLE_TO_CAM_DIR = {
    # Cardinal faces
    "top":          np.array([ 0.0,  1.0,  0.3]),
    "bottom":       np.array([ 0.0, -1.0,  0.3]),
    "left":         np.array([-1.0,  0.3,  0.3]),
    "right":        np.array([ 1.0,  0.3,  0.3]),
    "front":        np.array([ 0.3,  0.3,  1.0]),
    "back":         np.array([ 0.3,  0.3, -1.0]),
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
        camera_zoom: float = 1.0,
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
            eased = _smoothstep(t)
            fraction = eased
            orbit_deg = orbit_range_deg * eased

            exploded = self._apply_explosion(meshes, explosion_vectors, fraction)
            img = self._render_scene(
                exploded, cam_dir, orbit_deg,
                up_rotation_deg=rotation_offset_deg,
                resolution=VIDEO_RESOLUTION,
                camera_zoom=camera_zoom,
            )
            img.save(str(output_dir / f"video_{i:04d}.png"))

            if i % 18 == 0:
                print(f"[Phase 3 render] {i + 1}/{num_frames} frames")

        return output_dir

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
        camera_zoom: float = 1.0,
    ) -> Image.Image:
        import pyrender

        pr_scene = pyrender.Scene(
            bg_color=[0.0, 0.0, 0.0, 0.0],
            ambient_light=[0.35, 0.35, 0.35],
        )

        # Compute camera viewing axis first so we can rotate the geometry
        # around it BEFORE building pyrender meshes. pyrender.Mesh.from_trimesh
        # snapshots the vertex data at construction time, so mutating the
        # source trimesh afterwards has no visual effect.
        center = np.mean([m.centroid for m in meshes], axis=0)
        base_dir = cam_dir / np.linalg.norm(cam_dir)

        # Turntable orbit: rotate camera direction around world Y axis.
        # This keeps the sweep horizontal regardless of viewing angle
        # (front, top, left, etc.).
        y_axis = np.array([0.0, 1.0, 0.0])
        orbit_mat = trimesh.transformations.rotation_matrix(
            math.radians(orbit_deg), y_axis,
        )
        orbited = (orbit_mat[:3, :3] @ base_dir)
        orbited /= np.linalg.norm(orbited)

        # Apply rotation offset by rotating all geometry around the camera
        # viewing axis.  Negate the angle so positive degrees = clockwise in
        # screen space, matching CSS `rotate(Xdeg)`.  trimesh follows the
        # right-hand rule (positive = CCW when looking along axis toward
        # camera), which is the opposite of CSS convention.
        if abs(up_rotation_deg) > 0.01:
            rot_axis = orbited / np.linalg.norm(orbited)
            rot_matrix = trimesh.transformations.rotation_matrix(
                math.radians(-up_rotation_deg), rot_axis, center,
            )
            meshes = [m.copy() for m in meshes]
            for m in meshes:
                m.apply_transform(rot_matrix)
            center = np.mean([m.centroid for m in meshes], axis=0)

        for idx, mesh in enumerate(meshes):
            mat = _extract_material(mesh, idx)
            pr_mesh = pyrender.Mesh.from_trimesh(mesh, material=mat, smooth=False)
            pr_scene.add(pr_mesh)

        all_verts = np.vstack([m.vertices for m in meshes])

        # Camera distance: fit all geometry in frame using the vertical FoV.
        # Project vertices onto the camera plane (remove depth component) to get
        # the 2D footprint, then compute the distance required to contain the
        # footprint's bounding diagonal within the vertical field of view.
        # PADDING keeps parts away from the frame edges (25% breathing room).
        # camera_zoom < 1.0 pulls the camera further back (zoom out);
        # camera_zoom > 1.0 moves it closer (zoom in).
        PADDING = 1.25
        half_yfov = np.pi / 4.0 / 2.0  # yfov = pi/4; half-angle at pi/8
        depth = all_verts @ orbited
        footprint = all_verts - np.outer(depth, orbited)
        scale = np.linalg.norm(footprint.max(axis=0) - footprint.min(axis=0))
        cam_dist = (scale / 2.0) / math.tan(half_yfov) * PADDING / max(camera_zoom, 0.1)

        cam_pos = center + orbited * cam_dist
        cam_pose = _look_at(cam_pos, center)

        res = resolution if resolution is not None else (1024, 768)
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
