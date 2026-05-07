from __future__ import annotations

from .guardrail_cells import GuardrailCell, make_rectangle_cell, make_stack_cell


def _span_set_for_color(
    spans: dict[int, list[tuple[str, int, int]]],
    color: str,
) -> dict[int, set[tuple[int, int]]]:
    out: dict[int, set[tuple[int, int]]] = {s: set() for s in range(6)}

    for string_index, string_spans in spans.items():
        for span_color, fret_a, fret_b in string_spans:
            if span_color != color:
                continue
            a, b = sorted((fret_a, fret_b))
            out[string_index].add((a, b))

    return out


def build_rectangle_cells_from_spans(
    spans: dict[int, list[tuple[str, int, int]]],
) -> list[GuardrailCell]:
    """
    Build red 3x2 rectangle cells from red string spans.

    This is intentionally conservative:
    - adjacent strings only
    - matching 3-fret red spans only
    - B-string warp handled inside make_rectangle_cell()
    """
    red_spans = _span_set_for_color(spans, "red")
    cells: list[GuardrailCell] = []

    for low_string in range(5):
        high_string = low_string + 1

        for left_fret, right_fret in sorted(red_spans.get(low_string, set())):
            if right_fret - left_fret != 3:
                continue

            candidate = make_rectangle_cell(low_string, left_fret, right_fret)

            high_vertical = candidate.segments[1]
            high_left = high_vertical.start.fret
            high_right = high_vertical.end.fret
            a, b = sorted((high_left, high_right))

            if (a, b) in red_spans.get(high_string, set()):
                cells.append(candidate)

    return cells


def build_stack_cells_from_spans(
    spans: dict[int, list[tuple[str, int, int]]],
) -> list[GuardrailCell]:
    """
    Build blue 2x3 stack cells from blue string spans.

    Conservative first pass:
    - three adjacent strings
    - matching 2-fret blue outer rails
    - B-string warp handled inside make_stack_cell()
    """
    blue_spans = _span_set_for_color(spans, "blue")
    cells: list[GuardrailCell] = []

    for low_string in range(4):
        for lower_fret, upper_fret in sorted(blue_spans.get(low_string, set())):
            if upper_fret - lower_fret != 2:
                continue

            candidate = make_stack_cell(low_string, lower_fret, upper_fret)

            high_vertical = candidate.segments[1]
            high_lower = high_vertical.start.fret
            high_upper = high_vertical.end.fret
            a, b = sorted((high_lower, high_upper))

            high_string = low_string + 2
            if (a, b) in blue_spans.get(high_string, set()):
                cells.append(candidate)

    return cells


def build_guardrail_cells_from_spans(
    spans: dict[int, list[tuple[str, int, int]]],
) -> list[GuardrailCell]:
    return [
        *build_rectangle_cells_from_spans(spans),
        *build_stack_cells_from_spans(spans),
    ]