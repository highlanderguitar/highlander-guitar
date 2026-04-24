from __future__ import annotations

from highlander_render.diagram_spec import (
    DiagramEdgeSpec,
    DiagramShapeWindowSpec,
    DiagramSpec,
    DiagramToneSpec,
)
from highlander_render.harmony_engine import (
    build_minor_pent_nodes_for_event,
    build_rectangle_windows_for_minor_pent,
    mark_structural_rectangle_nodes,
)


def build_minor_pent_guardrail_diagram_spec(
    super_root: str,
    chord_root: str | None = None,
    chord_quality: str = "min7",
    max_fret: int = 15,
) -> DiagramSpec:
    if chord_root is None:
        chord_root = super_root

    raw_nodes = build_minor_pent_nodes_for_event(
        chord_root=chord_root,
        chord_quality=chord_quality,
        super_root=super_root,
        max_fret=max_fret,
    )

    rectangles = build_rectangle_windows_for_minor_pent(
        super_root=super_root,
        max_fret=max_fret,
    )

    nodes = mark_structural_rectangle_nodes(raw_nodes, rectangles)

    tone_specs = [
        DiagramToneSpec(
            string_index=n.string_index,
            fret=n.fret,
            note_name=n.note_name,
            degree_label=n.degree_label,
            sequence_index=n.sequence_index,
            node_kind=n.node_kind,
            is_structural=n.is_structural,
        )
        for n in nodes
    ]

    shape_windows: list[DiagramShapeWindowSpec] = []

    for i, rect in enumerate(rectangles, start=1):
        fret_min = min(rect.low_left_fret, rect.high_left_fret)
        fret_max = max(rect.low_right_fret, rect.high_right_fret)
        is_warp = (rect.low_string_index, rect.high_string_index) == (3, 4)

        edges = [
            DiagramEdgeSpec(
                start_string_index=rect.low_string_index,
                end_string_index=rect.low_string_index,
                start_fret=rect.low_left_fret,
                end_fret=rect.low_right_fret,
                color_role="rectangle",
                side="low",
                is_warp=False,
            ),
            DiagramEdgeSpec(
                start_string_index=rect.high_string_index,
                end_string_index=rect.high_string_index,
                start_fret=rect.high_left_fret,
                end_fret=rect.high_right_fret,
                color_role="rectangle",
                side="high",
                is_warp=is_warp,
            ),
        ]

        tones = [
            t
            for t in tone_specs
            if (
                (
                    t.string_index == rect.low_string_index
                    and rect.low_left_fret <= t.fret <= rect.low_right_fret
                )
                or (
                    t.string_index == rect.high_string_index
                    and rect.high_left_fret <= t.fret <= rect.high_right_fret
                )
            )
        ]

        shape_windows.append(
            DiagramShapeWindowSpec(
                shape_id=i,
                fret_min=fret_min,
                fret_max=fret_max,
                low_string_index=rect.low_string_index,
                high_string_index=rect.high_string_index,
                low_left_fret=rect.low_left_fret,
                low_right_fret=rect.low_right_fret,
                high_left_fret=rect.high_left_fret,
                high_right_fret=rect.high_right_fret,
                tones=tones,
                edges=edges,
            )
        )

    return DiagramSpec(
        diagram_id=f"{super_root.lower()}_minor_pent_guardrails",
        title=f"{super_root} Minor Pentatonic Guardrails",
        diagram_type="minor_pent_guardrail",
        super_root=super_root,
        chord_root=chord_root,
        chord_quality=chord_quality,
        tones=tone_specs,
        shape_windows=shape_windows,
        metadata={
            "doctrine": "rectangle_stack_guardrails",
            "max_fret": max_fret,
            "source": "diagram_spec_builder",
        },
    )