"""Minimal renderer contract for the doctrine-only seed.

Real Play This renderers can replace this foundation stub while retaining the
database path and readiness validation.
"""


def render_plan() -> dict[str, str]:
    return {
        "format": "loop-card",
        "opening": "PLAY THIS",
        "body": "One short, dense play-along loop",
        "closing": "Named learner need",
    }
