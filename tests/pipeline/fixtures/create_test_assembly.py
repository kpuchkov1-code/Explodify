"""Run once to generate the test GLB fixture.

Usage: python tests/pipeline/fixtures/create_test_assembly.py
"""
import trimesh
import numpy as np
from pathlib import Path

OUTPUT = Path(__file__).parent / "two_box_assembly.glb"


def create_two_box_assembly() -> trimesh.Scene:
    """Two boxes separated on the X axis — clearly 2 distinct components."""
    box_a = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
    box_a.apply_translation([1.5, 0.0, 0.0])
    box_a.visual.face_colors = [200, 100, 100, 255]  # red

    box_b = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
    box_b.apply_translation([-1.5, 0.0, 0.0])
    box_b.visual.face_colors = [100, 100, 200, 255]  # blue

    return trimesh.Scene({"box_a": box_a, "box_b": box_b})


if __name__ == "__main__":
    scene = create_two_box_assembly()
    scene.export(str(OUTPUT))
    print(f"Fixture written to {OUTPUT}")
