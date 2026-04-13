# pipeline/prompt_interpreter.py
"""Prompt interpreter for Phase 4 (Kling o1 video-to-video edit).

Kling o1 controls fidelity entirely through the prompt — there is no
strength/guidance parameter.  The strategy here is:

  - Lead with a hard geometry-lock: Kling must preserve all motion and
    structure; it is only allowed to change surface appearance.
  - Describe the desired surface treatment concisely.
  - Close with a short reinforcement of the geometry lock.
  - Keep total length well under the ~2500 char limit.

Long, descriptive prompts hurt geometry fidelity on Kling o1 because the
model treats every word as an instruction to add something new.  Shorter,
imperative prompts that lead with "do not change X" outperform elaborate
scene descriptions.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Geometry lock
# ---------------------------------------------------------------------------

# Opening: the first tokens carry the most weight.
_GEOMETRY_LOCK_OPEN = (
    "SURFACE RESTYLE ONLY. "
    "Do not alter any geometry, part shape, part count, spatial layout, "
    "motion path, camera angle, or timing. "
    "Every component must remain in exactly the same position and move along "
    "exactly the same trajectory as in the source video."
)

# Closing: repeated at the end as a reinforcement anchor.
_GEOMETRY_LOCK_CLOSE = (
    "Output must be frame-for-frame identical in structure and motion to the input."
)


# ---------------------------------------------------------------------------
# Lighting presets — short and concrete
# ---------------------------------------------------------------------------

_LIGHTING_PRESETS: dict[str, str] = {
    "studio": (
        "Three-point studio lighting: large softbox key upper-left, "
        "cool-neutral fill from right, thin rim light from behind. "
        "Soft penumbra shadows. No specular bloom."
    ),
    "warm": (
        "Warm 3800K key light upper-left, amber fill from right, "
        "warm rim from behind. Soft warm-toned shadows."
    ),
    "cold": (
        "Cool 6500K overhead key, neutral side fill, blue-white rim. "
        "Crisp high-contrast shadows. Technical, clinical look."
    ),
    "natural": (
        "Soft even natural light, 5500K, minimal directional shadow. "
        "No artificial rim or accent lights."
    ),
}


# ---------------------------------------------------------------------------
# Backdrop presets — short and concrete
# ---------------------------------------------------------------------------

_BACKDROP_PRESETS: dict[str, str] = {
    "dark": "Near-black studio backdrop. Dark ground plane, faint specular reflections only.",
    "white": "Infinite white backdrop. Soft contact shadow beneath assembly.",
    "gradient": "Dark-to-grey vertical gradient backdrop. Subtle ground-plane shadows.",
}


# ---------------------------------------------------------------------------
# Default material when user provides none
# ---------------------------------------------------------------------------

_DEFAULT_MATERIAL = (
    "Physically based materials: machined aluminium with Fresnel highlights, "
    "matte injection-moulded plastic, rubber with micro-texture grain."
)


# ---------------------------------------------------------------------------
# Constraints — what NOT to add
# ---------------------------------------------------------------------------

# Pruned to the 5 most impactful terms; redundant geometry and cosmetic
# artifact entries are covered by the geometry lock above.
_CONSTRAINTS = (
    "No bloom, glow, lens flare, motion blur, or bokeh. "
    "Stable exposure and material properties across all frames — no flicker."
)


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
    component_materials: dict[str, str] | None = None,
) -> str:
    """Build a concise, geometry-preserving Kling o1 edit prompt.

    Kling responds best to short imperative prompts that lead with
    what must NOT change.  This function keeps the total under 700 chars.
    """
    sections: list[str] = []

    # 1. Geometry lock — OPEN (most important, first tokens)
    sections.append(_GEOMETRY_LOCK_OPEN)

    # 2. Surface materials
    sections.append(
        _build_material_section(
            material_prompt,
            component_names or [],
            component_materials,
        )
    )

    # 3. Lighting
    lighting_key = lighting if lighting in _LIGHTING_PRESETS else "studio"
    sections.append(_LIGHTING_PRESETS[lighting_key])

    # 4. Backdrop
    backdrop_key = backdrop if backdrop in _BACKDROP_PRESETS else "dark"
    env = _BACKDROP_PRESETS[backdrop_key]
    if not ground_shadow:
        env = env.replace("shadow", "").replace("reflection", "")
    sections.append(env)

    # 5. User style notes (optional)
    if style_prompt.strip():
        sections.append(f"Additional style: {style_prompt.strip()}.")

    # 6. Negative constraints
    sections.append(_CONSTRAINTS)

    # 7. Geometry lock — CLOSE (reinforcement, last tokens)
    sections.append(_GEOMETRY_LOCK_CLOSE)

    return " ".join(sections)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_material_section(
    material_prompt: str,
    component_names: list[str],
    component_materials: dict[str, str] | None = None,
) -> str:
    materials = component_materials or {}

    # Per-component materials take priority over the global prompt.
    per_component_entries = [
        f"{name}: {mat.strip()}."
        for name, mat in list(materials.items())[:8]
        if mat.strip()
    ]
    if per_component_entries:
        return " ".join(per_component_entries) + " Apply with correct PBR roughness and Fresnel reflections."

    # Fall back to global material prompt.
    if material_prompt.strip():
        parts: list[str] = []
        if component_names:
            names = ", ".join(component_names[:8])
            parts.append(f"Parts: {names}.")
        parts.append(f"Materials: {material_prompt.strip()}.")
        parts.append("Apply with correct PBR roughness and Fresnel reflections.")
        return " ".join(parts)

    return _DEFAULT_MATERIAL


def resolve_lighting_key(
    studio_lighting: bool,
    warm_tone: bool,
    cold_tone: bool,
) -> str:
    if warm_tone:
        return "warm"
    if cold_tone:
        return "cold"
    if studio_lighting:
        return "studio"
    return "natural"


def resolve_backdrop_key(dark_backdrop: bool, white_backdrop: bool) -> str:
    if dark_backdrop:
        return "dark"
    if white_backdrop:
        return "white"
    return "gradient"
