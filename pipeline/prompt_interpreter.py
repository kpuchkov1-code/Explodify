# pipeline/prompt_interpreter.py
"""Prompt interpreter for Phase 4 (Kling video-to-video edit).

Builds a structured prompt that balances two competing goals:

  1. GEOMETRIC FIDELITY — preserve every part's shape, silhouette, count,
     position, motion path, and timing frame-for-frame.
  2. MATERIAL REALISM — apply convincing PBR surfaces, lighting, and
     environment so the result looks like a real product photograph.

Kling o1 video-to-video edit is a style-transfer model: it can change
materials and lighting but tends to drift on geometry if the prompt
doesn't repeatedly anchor it.  The template therefore:

  - Opens and closes with geometry-lock language (bookending).
  - Uses concrete, measurable visual descriptions instead of vague
    adjectives ("0.3mm radial brush marks" not "nice metal finish").
  - Specifies negative constraints explicitly ("no bloom, no glow")
    because Kling's default aesthetic leans cinematic.
  - Keeps total prompt length under ~600 tokens to avoid truncation
    in the Kling tokeniser.

Usage:
    from pipeline.prompt_interpreter import build_fal_prompt

    prompt = build_fal_prompt(
        material_prompt="brushed aluminium body, matte black cap",
        style_prompt="warm amber tone",
        lighting="studio",
        backdrop="dark",
        component_names=["body", "cap", "lens", "spring"],
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Template sections
# ---------------------------------------------------------------------------

# Geometry lock — repeated at top and bottom to bookend the prompt.
# Kling weights early and late tokens most heavily.
_GEOMETRY_LOCK_OPEN = (
    "Photorealistic product-photography render of an exploded mechanical "
    "assembly. CRITICAL: preserve the exact silhouette, part count, "
    "spatial arrangement, motion trajectory, and timing of every "
    "component as shown in the source video. Do not add, remove, merge, "
    "split, warp, or reposition any part. Maintain hard edges and "
    "mechanical precision — no organic softening of corners or edges."
)

_GEOMETRY_LOCK_CLOSE = (
    "FINAL CHECK: the output must be frame-for-frame identical in "
    "geometry, part count, and motion to the input video. Any shape "
    "deviation, missing component, or added element is a failure."
)

# Lighting presets — concrete descriptions with measurable properties
_LIGHTING_PRESETS: dict[str, str] = {
    "studio": (
        "Three-point product-photography lighting. "
        "Key: large softbox upper-left at 45 degrees, diffused, intensity 1.0. "
        "Fill: rectangular softbox from right at 0.3 intensity, cool-neutral 5600K. "
        "Rim: narrow strip light from behind at 0.4 intensity to edge-separate "
        "components from the backdrop. All shadows soft with penumbra, no hard "
        "cast shadows. No specular bloom or glare."
    ),
    "warm": (
        "Warm product-photography lighting. "
        "Key: large softbox upper-left, warm 3800K, intensity 1.0. "
        "Fill: soft amber bounce from right at 0.25 intensity. "
        "Rim: gentle warm edge light from behind at 0.3 intensity. "
        "Shadows soft with warm undertones. No blown highlights."
    ),
    "cold": (
        "Cool clinical product lighting. "
        "Key: overhead panel light, daylight 6500K, intensity 1.0. "
        "Fill: neutral side panels at 0.4 intensity. "
        "Rim: cool blue-white edge light at 0.3 intensity. "
        "Crisp shadows, high contrast. Medical/technical device aesthetic."
    ),
    "natural": (
        "Natural indirect lighting from a large north-facing window. "
        "Even, soft illumination with minimal directional shadow. "
        "Neutral 5500K colour temperature. No artificial rim or accent lights."
    ),
}

# Backdrop presets
_BACKDROP_PRESETS: dict[str, str] = {
    "dark": (
        "Dark studio backdrop: near-black (#0a0a0a) with a subtle vertical "
        "gradient to dark grey at the base. Polished dark ground plane showing "
        "faint specular reflections of the nearest components only. "
        "No environment reflections on the backdrop itself."
    ),
    "white": (
        "Infinite white cyclorama background, no visible horizon or seam. "
        "Soft contact shadow directly beneath the assembly on the ground plane. "
        "No colour spill from the backdrop onto the components."
    ),
    "gradient": (
        "Smooth vertical gradient from dark charcoal (#1a1a1a) at top to "
        "mid-grey (#3a3a3a) at the base. Subtle ground plane with soft "
        "contact shadows. No visible horizon line."
    ),
}

# Default materials when user provides none
_DEFAULT_MATERIAL = (
    "Apply physically based materials to every component: "
    "metal parts get machined aluminium with fine concentric tooling marks "
    "(0.3mm spacing), subtle anodisation colour variation, and accurate "
    "Fresnel reflections at glancing angles. "
    "Plastic parts: smooth injection-moulded finish with slight subsurface "
    "scattering and faint parting-line seams. "
    "Rubber/elastomer parts: matte black with micro-texture grain. "
    "Glass elements: clear with realistic refraction (IOR 1.52) and "
    "anti-reflective coating hints. "
    "Fasteners (screws, bolts): zinc-plated steel with knurling detail."
)

# Rendering constraints — tells Kling what NOT to do
_NEGATIVE_CONSTRAINTS = (
    "Do NOT add any of the following: bloom, glow, lens flare, chromatic "
    "aberration, film grain, vignette, motion blur, depth-of-field bokeh, "
    "atmospheric haze, dust particles, smoke, sparks, reflections of "
    "objects not in the scene, text overlays, watermarks, or UI elements. "
    "Do NOT change the number of components. Do NOT merge adjacent parts "
    "into a single surface. Do NOT add bevels or fillets that are not in "
    "the source geometry."
)

# Camera lock
_CAMERA = (
    "Camera: replicate the source video exactly — same focal length, "
    "same orbit path, same speed, same timing. No zoom, no handheld "
    "shake, no rack focus, no dolly moves not present in the original."
)

# Technical quality
_QUALITY = (
    "Render quality: 8K product photography. All components tack-sharp "
    "edge to edge. Consistent exposure across all frames — no flicker "
    "or per-frame brightness variation. Colour-accurate — no colour "
    "grading shifts between frames. Clean anti-aliased edges on every "
    "component silhouette."
)

# Temporal consistency — prevents Kling from drifting between frames
_TEMPORAL = (
    "Temporal consistency: materials, lighting, and reflections must be "
    "stable across every frame. No shimmer, flicker, or material "
    "popping between frames. Surface properties must track with the "
    "geometry as parts move — specular highlights slide naturally "
    "across surfaces during motion, they do not jump or disappear."
)


# ---------------------------------------------------------------------------
# Structured prompt config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PromptConfig:
    """Parsed user inputs ready for template filling."""
    material_prompt: str = ""
    style_notes: str = ""
    lighting: str = "studio"
    backdrop: str = "dark"
    ground_shadow: bool = True
    component_names: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_fal_prompt(
    material_prompt: str = "",
    style_prompt: str = "",
    lighting: str = "studio",
    backdrop: str = "dark",
    ground_shadow: bool = True,
    component_names: list[str] | None = None,
) -> str:
    """Build a structured Kling o1 edit prompt from user inputs.

    Args:
        material_prompt:  Free-text material description from the user.
                          e.g. "brushed aluminium body, matte black cap"
        style_prompt:     Free-text style notes (mood, colour, extras).
        lighting:         Lighting preset key: "studio", "warm", "cold", "natural".
        backdrop:         Backdrop preset key: "dark", "white", "gradient".
        ground_shadow:    Whether to include ground-plane shadow language.
        component_names:  Optional list of mesh names from Phase 1, used to
                          ground the material description to specific parts.

    Returns:
        A single prompt string with clearly separated sections.
    """
    sections: list[str] = []

    # 1. Geometry lock — OPEN (highest priority, first tokens)
    sections.append(_GEOMETRY_LOCK_OPEN)

    # 2. Materials — user-specific or rich defaults
    sections.append(_build_material_section(material_prompt, component_names or []))

    # 3. Lighting
    lighting_key = lighting if lighting in _LIGHTING_PRESETS else "studio"
    sections.append(_LIGHTING_PRESETS[lighting_key])

    # 4. Environment / backdrop
    backdrop_key = backdrop if backdrop in _BACKDROP_PRESETS else "dark"
    env = _BACKDROP_PRESETS[backdrop_key]
    if not ground_shadow:
        env = env.replace("shadow", "").replace("reflection", "")
    sections.append(env)

    # 5. Free-text style notes (user's extras)
    if style_prompt.strip():
        sections.append(f"Additional style direction: {style_prompt.strip()}.")

    # 6. Negative constraints — what Kling must NOT add
    sections.append(_NEGATIVE_CONSTRAINTS)

    # 7. Camera lock
    sections.append(_CAMERA)

    # 8. Technical quality
    sections.append(_QUALITY)

    # 9. Temporal consistency
    sections.append(_TEMPORAL)

    # 10. Geometry lock — CLOSE (reinforcement, last tokens)
    sections.append(_GEOMETRY_LOCK_CLOSE)

    return " ".join(sections)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_material_section(
    material_prompt: str,
    component_names: list[str],
) -> str:
    """Build the material description section.

    If the user provided material text, use it directly with PBR
    grounding language.  If component names are available, prefix with
    a part inventory so Kling can map materials to specific geometry.
    """
    if not material_prompt.strip():
        return _DEFAULT_MATERIAL

    parts: list[str] = []

    # Give Kling a parts list so it can map materials to geometry
    if component_names:
        names = ", ".join(component_names[:12])
        parts.append(f"Assembly components: {names}.")

    parts.append(f"Materials: {material_prompt.strip()}.")
    parts.append(
        "Apply each material with physically based rendering properties: "
        "correct Fresnel reflections at glancing angles, appropriate surface "
        "roughness (smooth metals ~0.15, matte plastics ~0.6, rubber ~0.85), "
        "accurate index of refraction for transparent elements. "
        "Preserve micro-detail: tooling marks on machined surfaces, "
        "parting lines on injection-moulded plastics, knurling on fasteners."
    )

    return " ".join(parts)


def resolve_lighting_key(
    studio_lighting: bool,
    warm_tone: bool,
    cold_tone: bool,
) -> str:
    """Map frontend checkbox state to a lighting preset key."""
    if warm_tone:
        return "warm"
    if cold_tone:
        return "cold"
    if studio_lighting:
        return "studio"
    return "natural"


def resolve_backdrop_key(
    dark_backdrop: bool,
    white_backdrop: bool,
) -> str:
    """Map frontend checkbox state to a backdrop preset key."""
    if dark_backdrop:
        return "dark"
    if white_backdrop:
        return "white"
    return "gradient"
