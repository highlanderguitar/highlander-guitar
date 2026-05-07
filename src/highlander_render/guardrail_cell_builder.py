from __future__ import annotations

from .guardrail_cells import (
    GuardrailCell,
    adjacent_warped_fret,
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

    return cells


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