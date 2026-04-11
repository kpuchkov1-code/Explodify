"""
Explodify — CAD assembly to exploded-view animation.
Entry point / CLI.

Supported input formats:
  STEP/STP  — preserves named assembly components (recommended for multi-part files)
  GLB/GLTF  — preserves named components
  OBJ, STL, PLY, 3MF — single mesh or basic multi-mesh

To use with SolidWorks, Fusion 360, Inventor, etc.:
  Export your assembly as STEP AP214 or AP242, then pass the .step file here.
"""
import argparse
import dataclasses
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Explodify: CAD assembly to exploded-view animation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to assembly file (.step, .stp, .glb, .obj, .stl, ...)",
    )
    parser.add_argument(
        "--explode", type=float, default=1.5,
        help="Explosion scalar multiplier (default: 1.5)",
    )
    parser.add_argument(
        "--output", default="output/exploded_view.mp4",
        help="Output video path",
    )
    parser.add_argument(
        "--frames-dir", default="output/frames",
        help="Directory for PNG frames",
    )
    parser.add_argument(
        "--style-prompt", default="",
        help='Aesthetic style prompt e.g. "Dark marble, dramatic rim lighting"',
    )
    args = parser.parse_args()

    from pipeline.phase1_geometry import GeometryAnalyzer
    from pipeline.phase2_snapshots import SnapshotRenderer
    from pipeline.models import UnsupportedFormatError

    frames_dir = Path(args.frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source_format = Path(args.input).suffix.lower()

    print(f"[Phase 1] Loading {args.input} ...")
    analyzer = GeometryAnalyzer()
    try:
        named_meshes = analyzer.load(args.input)
    except UnsupportedFormatError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[Phase 1] Found {len(named_meshes)} components:")
    for nm in named_meshes:
        print(f"          - {nm.name}  ({len(nm.mesh.faces)} faces)")

    named_meshes = analyzer.reorient(named_meshes)
    print("[Phase 1] Assembly reoriented (longest axis → vertical)")

    master = analyzer.master_angle(named_meshes)
    print(f"[Phase 1] Master angle: {master}")

    vectors = analyzer.explosion_vectors(named_meshes, scalar=args.explode)
    print(f"[Phase 1] Explosion vectors computed (scalar={args.explode})")

    print("[Phase 2] Rendering keyframes ...")
    renderer = SnapshotRenderer()
    frame_set = renderer.render(
        named_meshes, vectors, master,
        output_dir=frames_dir,
        scalar=args.explode,
        source_format=source_format,
    )
    # Inject style_prompt into metadata for Phase 3/4 consumption
    frame_set = dataclasses.replace(
        frame_set,
        metadata=dataclasses.replace(frame_set.metadata, style_prompt=args.style_prompt),
    )
    print(f"[Phase 2] frame_a: {frame_set.frame_a}")
    print(f"[Phase 2] frame_b: {frame_set.frame_b}")
    print(f"[Phase 2] frame_c: {frame_set.frame_c}")
    if args.style_prompt:
        print(f"[Phase 2] Style prompt: {args.style_prompt}")

    try:
        from pipeline.phase3_stylize import GeminiStylizer
        from pipeline.phase4_video import FalVideoSynth

        print("[Phase 3] Gemini stylization ...")
        stylizer = GeminiStylizer()
        stylized = stylizer.stylize(frame_set, output_dir=frames_dir / "stylized")
        print(f"[Phase 3] Stylized frames at {frames_dir}/stylized/")

        print("[Phase 4] fal.ai video synthesis ...")
        synth = FalVideoSynth()
        video_path = synth.synthesize(stylized, output_path=output_path)
        print(f"[Done] Video written to {video_path}")
    except (ImportError, KeyError) as e:
        print(f"[Phase 3+4] Skipped ({e}) — frame set ready at: {frames_dir}")


if __name__ == "__main__":
    main()
