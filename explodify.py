"""
Explodify — CAD assembly to exploded-view animation.
Entry point / CLI.
"""
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Explodify: CAD to exploded-view animation")
    parser.add_argument("--input", required=True, help="Path to CAD/mesh file (.glb, .obj, .stl)")
    parser.add_argument("--explode", type=float, default=1.5, help="Explosion scalar multiplier")
    parser.add_argument("--output", default="output/exploded_view.mp4", help="Output video path")
    parser.add_argument("--frames-dir", default="output/frames", help="Directory for PNG frames")
    args = parser.parse_args()

    from pipeline.phase1_geometry import GeometryAnalyzer
    from pipeline.phase2_snapshots import SnapshotRenderer

    frames_dir = Path(args.frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"[Phase 1] Loading {args.input} ...")
    analyzer = GeometryAnalyzer()
    meshes = analyzer.load(args.input)
    print(f"[Phase 1] Found {len(meshes)} components")

    master = analyzer.master_angle(meshes)
    print(f"[Phase 1] Master angle: {master}")

    vectors = analyzer.explosion_vectors(meshes, scalar=args.explode)
    print("[Phase 1] Explosion vectors computed")

    print("[Phase 2] Rendering keyframes ...")
    renderer = SnapshotRenderer()
    frame_set = renderer.render(meshes, vectors, master, output_dir=frames_dir, scalar=args.explode)
    print(f"[Phase 2] Frames: {frame_set.frame_a}, {frame_set.frame_b}, {frame_set.frame_c}")

    print("[Phase 3+4] Stylization + video: not yet implemented (Kirill's side)")
    print(f"[Done] Frame set ready at: {frames_dir}")


if __name__ == "__main__":
    main()
