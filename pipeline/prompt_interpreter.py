# pipeline/prompt_interpreter.py
"""Prompt interpreter for Phase 4 (Kling o1 video-to-video edit).

Kling o1 controls fidelity entirely through the prompt — there is no
strength/guidance parameter.  The strategy here is:

  - Lead with a hard geometry-lock: Kling must preserve all motion and
    structure; it is only allowed to change surface appearance.
  - Describe materials concisely as "Component is material" pairs.
  - Append optional user style notes (lighting, mood, backdrop).
  - Close with a short reinforcement of the geometry lock.
  - Keep total length well under the ~2500 char limit.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Geometry lock
# ---------------------------------------------------------------------------

_GEOMETRY_LOCK_OPEN = (
    "SURFACE RESTYLE ONLY. "
    "Do not alter any geometry, part shape, part count, spatial layout, "
    "motion path, camera angle, or timing. "
    "Every component must remain in exactly the same position and move along "
    "exactly the same trajectory as in the source video."
)

_GEOMETRY_LOCK_CLOSE = (
    "Output must be frame-for-frame identical in structure and motion to the input."
)


# ---------------------------------------------------------------------------
# Default material when user provides none
# ---------------------------------------------------------------------------

_DEFAULT_MATERIAL = (
    "Physically based materials: machined aluminium with Fresnel highlights, "
    "matte injection-moulded plastic, rubber with micro-texture grain."
)


# ---------------------------------------------------------------------------
# Base render style — injected before materials and user notes so Kling
# anchors to the correct aesthetic reference before reading anything else.
# ---------------------------------------------------------------------------

_RENDER_STYLE = (
    "Render quality: professional product visualisation, Blender Cycles standard. "
    "Background: pure infinite void — solid colour or smooth gradient only, "
    "no physical backdrop, no environment geometry, no edges or seams visible at any zoom level. "
    "Lighting: clean area lights with soft shadow falloff, no ground shadow, no floor reflection. "
    "No lens flare, no bloom, no glow, no chromatic aberration, no post-processing artifacts."
)

# Closing constraints — bookend the prompt for reinforcement
_CONSTRAINTS = (
    "No lens flare, bloom, glow, motion blur, or bokeh of any kind. "
    "Infinite void background — no backdrop edges under any circumstance. "
    "Stable, flicker-free exposure and materials across all frames."
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_fal_prompt(
    rows: list[dict] | None = None,
    style_prompt: str = "",
) -> str:
    """Build a concise, geometry-preserving Kling o1 edit prompt.

    Args:
        rows: List of dicts with 'part' and 'material' keys.
        style_prompt: Free-form style notes (lighting, backdrop, mood).
    """
    sections: list[str] = [_GEOMETRY_LOCK_OPEN]
    sections.append(_RENDER_STYLE)
    sections.append(_build_rows_section(rows or []))
    if style_prompt.strip():
        sections.append(style_prompt.strip())
    sections.append(_CONSTRAINTS)
    sections.append(_GEOMETRY_LOCK_CLOSE)
    return " ".join(sections)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_rows_section(rows: list[dict]) -> str:
    """Serialise component/material rows into a concise prompt fragment.

    Filters rows with no material. Falls back to the default material
    description if no rows are filled.
    """
    filled = []
    for i, row in enumerate(rows[:20]):
        part = (row.get("part") or "").strip() or f"Part {i + 1}"
        material = (row.get("material") or "").strip()
        if material:
            filled.append(f"{part} is {material}")

    if not filled:
        return _DEFAULT_MATERIAL

    return "Components: " + ", ".join(filled) + "."
