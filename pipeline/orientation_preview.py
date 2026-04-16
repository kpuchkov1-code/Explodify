import base64
import io
from typing import List

from pipeline.models import NamedMesh
from pipeline.phase2_snapshots import _ANGLE_TO_CAM_DIR, render_preview_frame


def render_orientation_previews(named_meshes: List[NamedMesh]) -> dict[str, str]:
    """Render a preview PNG for each of the 6 cardinal faces.

    Returns a dict mapping face name to base64-encoded PNG data URI.
    """
    meshes = [nm.mesh for nm in named_meshes]
    images: dict[str, str] = {}

    for face, cam_dir in _ANGLE_TO_CAM_DIR.items():
        img = render_preview_frame(meshes, cam_dir, resolution=(512, 384))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        images[face] = f"data:image/png;base64,{encoded}"

    return images
