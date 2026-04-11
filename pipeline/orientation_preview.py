# pipeline/orientation_preview.py
"""Renders six orthographic face views of a mesh assembly for orientation selection."""
import base64
import math
from io import BytesIO
from typing import Dict, List

import numpy as np
from PIL import Image

from pipeline.models import NamedMesh

# Match the video's 16:9 aspect ratio so the picker preview and video first
# frame use the same camera frustum, preventing apparent orientation drift.
PREVIEW_RESOLUTION = (512, 288)

# Camera directions must match _ANGLE_TO_CAM_DIR in phase2_snapshots.py exactly,
# otherwise the orientation preview shows a different angle than the final render.
_FACE_CAM_DIRS: Dict[str, np.ndarray] = {
    "front":  np.array([ 0.3,  0.3,  1.0]),
    "back":   np.array([ 0.3,  0.3, -1.0]),
    "left":   np.array([-1.0,  0.3,  0.3]),
    "right":  np.array([ 1.0,  0.3,  0.3]),
    "top":    np.array([ 0.0,  1.0,  0.3]),
    "bottom": np.array([ 0.0, -1.0,  0.3]),
}

FACE_ORDER = ["front", "back", "left", "right", "top", "bottom"]


def render_orientation_previews(named_meshes: List[NamedMesh]) -> Dict[str, str]:
    """Render 6 face views and return a dict of face_name -> base64 PNG data URI.

    Each image is a plain CAD screengrab (no explosion, no stylization).
    """
    # Imported lazily so pyrender is not loaded until needed.
    from pipeline.phase2_snapshots import render_preview_frame

    meshes = [nm.mesh for nm in named_meshes]
    result: Dict[str, str] = {}

    for face in FACE_ORDER:
        cam_dir = _FACE_CAM_DIRS[face]
        img: Image.Image = render_preview_frame(
            meshes, cam_dir, resolution=PREVIEW_RESOLUTION
        )
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        result[face] = f"data:image/png;base64,{b64}"

    return result
