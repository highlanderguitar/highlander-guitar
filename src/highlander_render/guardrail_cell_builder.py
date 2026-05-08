from __future__ import annotations

from .guardrail_cells import (
    GuardrailCell,
    GuardrailGeometry,
    GuardrailPoint,
    GuardrailSegment,
    adjacent_warped_fret,
    make_segment,
    make_rectangle_cell,
    make_stack_cell,
)

NUM_STRINGS = 6
NUM_FRETS = 15


def _span_set_for_color(
    spans: dict[int, list[tuple[str, int, int]]],
    color: str,
) -> dict[int, set[tuple[int, int]]]:
    out: dict[int, set[tuple[int, int]]] = {s: set() for s in range(NUM_STRINGS)}

    for string_index, string_spans in spans.items():
        if not 0 <= string_index < NUM_STRINGS:
            continue

        for span_color, fret_a, fret_b in string_spans:
            if span_color != color:
                continue
            a, b = sorted((fret_a, fret_b))
            out[string_index].add((a, b))

    return out


def _has_containing_span(
    span_map: dict[int, set[tuple[int, int]]],
    string_index: int,
    fret_a: int,
    fret_b: int,
) -> bool:
    a, b = sorted((fret_a, fret_b))
    for span_a, span_b in span_map.get(string_index, set()):
        if span_a <= a and b <= span_b:
            return True
    return False


def _has_exact_span(
    span_map: dict[int, set[tuple[int, int]]],
    string_index: int,
    fret_a: int,
    fret_b: int,
) -> bool:
    a, b = sorted((fret_a, fret_b))
    return (a, b) in span_map.get(string_index, set())


def build_rectangle_cells_from_spans(
    spans: dict[int, list[tuple[str, int, int]]],
) -> list[GuardrailCell]:
    """
    Build red rectangle/parallelogram cells from red spans.

    Rectangle doctrine:
        - red
        - 3 frets x 2 adjacent strings
        - G->B warp allowed
        - high-string side may be contained inside a longer red span
    """
    red_spans = _span_set_for_color(spans, "red")
    cells: list[GuardrailCell] = []
    seen: set[tuple[int, int, int, int]] = set()

    for low_string in range(NUM_STRINGS - 1):
        high_string = low_string + 1

        for left_fret, right_fret in sorted(red_spans.get(low_string, set())):
            candidate = make_rectangle_cell(low_string, left_fret, right_fret)

            high_vertical = candidate.segments[1]
            high_left = high_vertical.start.fret
            high_right = high_vertical.end.fret

            low_width = right_fret - left_fret
            high_width = abs(high_right - high_left)

            if low_width != 3 and high_width != 3:
                # Allows the B-min first-position G-side 0->2 containing-span case
                # only when the warped high side supplies the full 3-fret edge.
                continue

            if not _has_containing_span(red_spans, high_string, high_left, high_right):
                continue

            key = (low_string, left_fret, right_fret, high_string)
            if key in seen:
                continue
            seen.add(key)

            cells.append(candidate)

    open_g_b_cell = _build_open_g_b_rectangle_cell(red_spans)
    if open_g_b_cell is not None:
        cells.append(open_g_b_cell)

    return cells


def _build_open_g_b_rectangle_cell(
    red_spans: dict[int, set[tuple[int, int]]],
) -> GuardrailCell | None:
    """
    Build the nut-clipped G/B red rectangle.

    In B minor pentatonic the theoretical warped rectangle starts one fret
    before the nut on the G string and lands on fret 0 of the B string. The
    visible geometry is therefore clipped by the nut: G 0->2, B 0->3, and the
    lower warped cap G2->B3. We intentionally do not draw a fake same-fret
    G0->B0 cap.
    """
    g_string = 3
    b_string = 4

    if not _has_containing_span(red_spans, g_string, 0, 2):
        return None
    if not _has_containing_span(red_spans, b_string, 0, 3):
        return None

    cell_id = "rectangle:3:open:0:3"
    points = (
        GuardrailPoint(g_string, 0),
        GuardrailPoint(g_string, 2),
        GuardrailPoint(b_string, 3),
        GuardrailPoint(b_string, 0),
    )
    segments = (
        make_segment("red", "rectangle", "rail", g_string, 0, g_string, 2, cell_id),
        make_segment("red", "rectangle", "rail", b_string, 0, b_string, 3, cell_id),
        make_segment("red", "rectangle", "cap", g_string, 2, b_string, 3, cell_id),
    )

    return GuardrailCell(
        role="rectangle",
        color="red",
        cell_id=cell_id,
        anchor_string=g_string,
        anchor_fret=0,
        points=points,
        segments=segments,
        label="rectangle_open_clip",
    )


def build_stack_cells_from_spans(
    spans: dict[int, list[tuple[str, int, int]]],
) -> list[GuardrailCell]:
    """
    Build blue stack cells from topology, not endpoint guesses.

    Stack doctrine:
        - blue
        - 2 frets x 3 adjacent strings
        - outer rails are real blue spans
        - caps/path edges cross one adjacent string at a time
        - G->B warp is applied between adjacent strings only
        - no orphan B<->high-E caps
        - no inferred caps from random endpoints
    """
    blue_spans = _span_set_for_color(spans, "blue")
    cells: list[GuardrailCell] = []
    seen: set[tuple[int, int, int]] = set()

    for low_string in range(NUM_STRINGS - 2):
        mid_string = low_string + 1
        high_string = low_string + 2

        for lower_fret, upper_fret in sorted(blue_spans.get(low_string, set())):
            if upper_fret - lower_fret != 2:
                continue

            mid_lower = adjacent_warped_fret(low_string, mid_string, lower_fret)
            mid_upper = adjacent_warped_fret(low_string, mid_string, upper_fret)

            high_lower = adjacent_warped_fret(mid_string, high_string, mid_lower)
            high_upper = adjacent_warped_fret(mid_string, high_string, mid_upper)

            if not _has_exact_span(
                blue_spans,
                high_string,
                high_lower,
                high_upper,
            ):
                continue

            key = (low_string, lower_fret, upper_fret)
            if key in seen:
                continue
            seen.add(key)

            cells.append(make_stack_cell(low_string, lower_fret, upper_fret))

    return cells


def build_guardrail_cells_from_spans(
    spans: dict[int, list[tuple[str, int, int]]],
) -> list[GuardrailCell]:
    return [
        *build_rectangle_cells_from_spans(spans),
        *build_stack_cells_from_spans(spans),
    ]


def _segment_key(segment: GuardrailSegment) -> tuple[str, str, str, int, int, int, int]:
    return (
        segment.color,
        segment.role,
        segment.edge_kind,
        segment.start.string_index,
        segment.start.fret,
        segment.end.string_index,
        segment.end.fret,
    )


def flatten_guardrail_segments(cells: list[GuardrailCell]) -> tuple[GuardrailSegment, ...]:
    """
    Flatten cells into render-ready segments while preserving doctrine.

    Identical segments may be shared by neighboring cells. They should be drawn
    once, but they remain traceable to the cell that first introduced them.
    """
    segments: list[GuardrailSegment] = []
    seen: set[tuple[str, str, str, int, int, int, int]] = set()

    for cell in cells:
        for segment in cell.segments:
            key = _segment_key(segment)
            if key in seen:
                continue
            seen.add(key)
            segments.append(segment)

    return tuple(segments)


def build_minor_pent_guardrail_geometry(
    root: str,
    spelling: str = "sharps",
    max_fret: int = NUM_FRETS,
) -> GuardrailGeometry:
    """
    Build the canonical minor-pentatonic rectangle/stack guardrail geometry.

    The current implementation still uses the established span classifier as
    input, but renderers consume only the returned GuardrailGeometry segments.
    """
    from .harmony_engine import build_minor_pent_string_spans

    spans = build_minor_pent_string_spans(root, spelling=spelling, max_fret=max_fret)
    cells = build_guardrail_cells_from_spans(spans)
    segments = flatten_guardrail_segments(cells)

    return GuardrailGeometry(
        root=root,
        scale_name="minor_pentatonic",
        max_fret=max_fret,
        cells=tuple(cells),
        segments=segments,
    )
