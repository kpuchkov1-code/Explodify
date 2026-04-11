"""
Explodify — CAD assembly to exploded-view animation.
Entry point / CLI.
"""
import argparse
import dataclasses
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Explodify: CAD to exploded-view animation")
    parser.add_argument("--input", required=True, help="Path to CAD/mesh file (.glb, .obj, .stl)")
    parser.add_argument("--explode", type=float, default=1.5, help="Explosion scalar multiplier")
    parser.add_argument("--output", default="output/exploded_view.mp4", help="Output video path")
    parser.add_argument("--frames-dir", default="output/frames", help="Directory for PNG frames")
    parser.add_argument(
        "--style-prompt", default="",
        help='Aesthetic style prompt e.g. "Dark marble, dramatic rim lighting"'
    )
    args = parser.parse_args()

    frames_dir = Path(args.frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    from pipeline.phase1_geometry import GeometryAnalyzer
    from pipeline.phase2_snapshots import SnapshotRenderer
    from pipeline.phase3_stylize import GeminiStylizer
    from pipeline.phase4_video import FalVideoSynth

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
    # Inject style_prompt into metadata (Phase 2 doesn't accept it directly yet)
    frame_set = dataclasses.replace(
        frame_set,
        metadata=dataclasses.replace(frame_set.metadata, style_prompt=args.style_prompt),
    )
    print(f"[Phase 2] Frames: {frame_set.frame_a}, {frame_set.frame_b}, {frame_set.frame_c}")
    if args.style_prompt:
        print(f"[Phase 2] Style prompt: {args.style_prompt}")

    print("[Phase 3] Gemini stylization ...")
    stylizer = GeminiStylizer()
    stylized = stylizer.stylize(frame_set, output_dir=frames_dir / "stylized")
    print(f"[Phase 3] Stylized frames at {frames_dir}/stylized/")

    print("[Phase 4] fal.ai video synthesis ...")
    synth = FalVideoSynth()
    video_path = synth.synthesize(stylized, output_path=output_path)
    print(f"[Done] Video written to {video_path}")


if __name__ == "__main__":
    main()
