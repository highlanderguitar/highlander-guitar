from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

GuardrailRole = Literal["rectangle", "stack"]
GuardrailColor = Literal["red", "blue"]
GuardrailSegmentKind = Literal["rail", "cap"]


@dataclass(frozen=True)
class GuardrailPoint:
    """
    Logical fretboard coordinate.

    string_index:
        0 = low E, 1 = A, 2 = D, 3 = G, 4 = B, 5 = high E

    fret:
        Fret-line coordinate, not note-center coordinate.
        Guardrail polygons live on fret lines.
    """
    string_index: int
    fret: int


@dataclass(frozen=True)
class GuardrailSegment:
    """
    One drawable topology segment.

    This is NOT a guessed connector.
    This is an explicit piece of rectangle/stack geometry.
    """
    color: GuardrailColor
    role: GuardrailRole
    edge_kind: GuardrailSegmentKind
    start: GuardrailPoint
    end: GuardrailPoint
    cell_id: str = ""
    source: str = "cell"


@dataclass(frozen=True)
class GuardrailCell:
    """
    A topology cell.

    Rectangle:
        2 strings x 3 frets

    Stack:
        3 strings x 2 frets

    The renderer should eventually draw segments from these cells instead of
    guessing connectors from vertical spans.
    """
    role: GuardrailRole
    color: GuardrailColor
    cell_id: str
    anchor_string: int
    anchor_fret: int
    points: tuple[GuardrailPoint, ...]
    segments: tuple[GuardrailSegment, ...]
    label: str = ""


@dataclass(frozen=True)
class GuardrailGeometry:
    """
    Canonical guardrail geometry for renderers.

    Cells preserve the rectangle/stack doctrine. Segments are the flattened,
    render-ready geometry that every renderer should consume.
    """
    root: str
    scale_name: str
    max_fret: int
    cells: tuple[GuardrailCell, ...] = field(default_factory=tuple)
    segments: tuple[GuardrailSegment, ...] = field(default_factory=tuple)


def crosses_g_b(source_string: int, target_string: int) -> bool:
    return (
        (source_string == 3 and target_string == 4)
        or (source_string == 4 and target_string == 3)
    )


def adjacent_warped_fret(source_string: int, target_string: int, fret: int) -> int:
    """
    Guitar standard-tuning warp.

    G -> B raises target fret by 1.
    B -> G lowers target fret by 1.
    """
    if source_string == 3 and target_string == 4:
        return fret + 1
    if source_string == 4 and target_string == 3:
        return fret - 1
    return fret


def make_segment(
    color: GuardrailColor,
    role: GuardrailRole,
    edge_kind: GuardrailSegmentKind,
    s1: int,
    f1: int,
    s2: int,
    f2: int,
    cell_id: str = "",
    source: str = "cell",
) -> GuardrailSegment:
    return GuardrailSegment(
        color=color,
        role=role,
        edge_kind=edge_kind,
        start=GuardrailPoint(s1, f1),
        end=GuardrailPoint(s2, f2),
        cell_id=cell_id,
        source=source,
    )


def make_rectangle_cell(
    low_string: int,
    left_fret: int,
    right_fret: int,
) -> GuardrailCell:
    """
    Build a red rectangle cell.

    Uses adjacent strings.
    Applies B-string warp to the upper string side.
    """
    high_string = low_string + 1
    cell_id = f"rectangle:{low_string}:{left_fret}:{right_fret}"

    high_left = adjacent_warped_fret(low_string, high_string, left_fret)
    high_right = adjacent_warped_fret(low_string, high_string, right_fret)

    points = (
        GuardrailPoint(low_string, left_fret),
        GuardrailPoint(low_string, right_fret),
        GuardrailPoint(high_string, high_right),
        GuardrailPoint(high_string, high_left),
    )

    segments = (
        make_segment("red", "rectangle", "rail", low_string, left_fret, low_string, right_fret, cell_id),
        make_segment("red", "rectangle", "rail", high_string, high_left, high_string, high_right, cell_id),
        make_segment("red", "rectangle", "cap", low_string, left_fret, high_string, high_left, cell_id),
        make_segment("red", "rectangle", "cap", low_string, right_fret, high_string, high_right, cell_id),
    )

    return GuardrailCell(
        role="rectangle",
        color="red",
        cell_id=cell_id,
        anchor_string=low_string,
        anchor_fret=left_fret,
        points=points,
        segments=segments,
        label="rectangle",
    )


def make_stack_cell(
    low_string: int,
    lower_fret: int,
    upper_fret: int,
) -> GuardrailCell:
    """
    Build a blue stack cell.

    Stack is a 3-string x 2-fret cell.

    The cell is built one adjacent string-crossing at a time so G->B warp can
    happen naturally instead of jumping across two strings.
    """
    mid_string = low_string + 1
    high_string = low_string + 2
    cell_id = f"stack:{low_string}:{lower_fret}:{upper_fret}"

    mid_lower = adjacent_warped_fret(low_string, mid_string, lower_fret)
    mid_upper = adjacent_warped_fret(low_string, mid_string, upper_fret)

    high_lower = adjacent_warped_fret(mid_string, high_string, mid_lower)
    high_upper = adjacent_warped_fret(mid_string, high_string, mid_upper)

    points = (
        GuardrailPoint(low_string, lower_fret),
        GuardrailPoint(low_string, upper_fret),
        GuardrailPoint(mid_string, mid_upper),
        GuardrailPoint(mid_string, mid_lower),
        GuardrailPoint(high_string, high_upper),
        GuardrailPoint(high_string, high_lower),
    )

    segments = (
        # vertical sides
        make_segment("blue", "stack", "rail", low_string, lower_fret, low_string, upper_fret, cell_id),
        make_segment("blue", "stack", "rail", high_string, high_lower, high_string, high_upper, cell_id),

        # one-string-at-a-time caps/path edges
        make_segment("blue", "stack", "cap", low_string, lower_fret, mid_string, mid_lower, cell_id),
        make_segment("blue", "stack", "cap", mid_string, mid_lower, high_string, high_lower, cell_id),
        make_segment("blue", "stack", "cap", low_string, upper_fret, mid_string, mid_upper, cell_id),
        make_segment("blue", "stack", "cap", mid_string, mid_upper, high_string, high_upper, cell_id),
    )

    return GuardrailCell(
        role="stack",
        color="blue",
        cell_id=cell_id,
        anchor_string=low_string,
        anchor_fret=lower_fret,
        points=points,
        segments=segments,
        label="stack",
    )
