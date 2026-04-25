from __future__ import annotations

from pathlib import Path
import svgwrite

from highlander_render.diagram_spec import DiagramSpec, DiagramShapeWindowSpec, DiagramToneSpec


DEFAULT_COLORS = {
    "background": "#111111",
    "panel": "#181818",
    "string": "#9A9A9A",
    "fret": "#666666",
    "nut": "#FFFFFF",
    "title": "#FFFFFF",
    "subtitle": "#CFCFCF",
    "rectangle": "#FF5A5A",
    "stack": "#5A8DFF",
    "chord": "#FFFFFF",
    "pink": "#FF5CA8",
    "structural": "#FFD166",
    "note_outline": "#FFFFFF",
    "note_text": "#000000",
}


def string_x(board_left: float, board_width: float, string_index: int) -> float:
    return board_left + (string_index / 5) * board_width


def fret_y(board_top: float, fret_min: int, fret_max: int, fret: int, board_height: float) -> float:
    span = max(1, fret_max - fret_min)
    return board_top + ((fret - fret_min) / span) * board_height


def tone_fill(tone: DiagramToneSpec, colors: dict[str, str]) -> str:
    if tone.node_kind == "chord":
        return colors["chord"]
    if tone.is_structural:
        return colors["structural"]
    return colors["pink"]


def draw_note(
    dwg: svgwrite.Drawing,
    x: float,
    y: float,
    label: str,
    fill: str,
    outline: str,
    text_fill: str,
) -> None:
    dwg.add(
        dwg.circle(
            center=(x, y),
            r=13,
            fill=fill,
            stroke=outline,
            stroke_width=2,
        )
    )
    dwg.add(
        dwg.text(
            label,
            insert=(x, y + 4),
            text_anchor="middle",
            font_size="9px",
            font_family="Arial",
            font_weight="bold",
            fill=text_fill,
        )
    )


def draw_shape_window(
    dwg: svgwrite.Drawing,
    window: DiagramShapeWindowSpec,
    x: float,
    y: float,
    colors: dict[str, str],
) -> None:
    panel_w = 190
    panel_h = 260
    board_left = x + 24
    board_top = y + 52
    board_w = 140
    board_h = 170

    dwg.add(
        dwg.rect(
            insert=(x, y),
            size=(panel_w, panel_h),
            rx=10,
            ry=10,
            fill=colors["panel"],
            stroke="#333333",
            stroke_width=1,
        )
    )

    dwg.add(
        dwg.text(
            f"Shape {window.shape_id}",
            insert=(x + 14, y + 24),
            fill=colors["title"],
            font_size="15px",
            font_family="Arial",
            font_weight="bold",
        )
    )

    dwg.add(
        dwg.text(
            f"frets {window.fret_min}-{window.fret_max}",
            insert=(x + 14, y + 42),
            fill=colors["subtitle"],
            font_size="11px",
            font_family="Arial",
        )
    )

    for s in range(6):
        sx = string_x(board_left, board_w, s)
        dwg.add(
            dwg.line(
                start=(sx, board_top),
                end=(sx, board_top + board_h),
                stroke=colors["string"],
                stroke_width=1.4,
            )
        )

    for fret in range(window.fret_min, window.fret_max + 1):
        fy = fret_y(board_top, window.fret_min, window.fret_max, fret, board_h)
        dwg.add(
            dwg.line(
                start=(board_left, fy),
                end=(board_left + board_w, fy),
                stroke=colors["nut"] if fret == 0 else colors["fret"],
                stroke_width=2.0 if fret == 0 else 1.0,
            )
        )

    for edge in window.edges:
        x1 = string_x(board_left, board_w, edge.start_string_index)
        y1 = fret_y(board_top, window.fret_min, window.fret_max, edge.start_fret, board_h)
        x2 = string_x(board_left, board_w, edge.end_string_index)
        y2 = fret_y(board_top, window.fret_min, window.fret_max, edge.end_fret, board_h)

        dwg.add(
            dwg.line(
                start=(x1, y1),
                end=(x2, y2),
                stroke=colors.get(edge.color_role, colors["rectangle"]),
                stroke_width=5,
                stroke_opacity=0.55,
                stroke_linecap="round",
            )
        )

    for tone in window.tones:
        tx = string_x(board_left, board_w, tone.string_index)
        ty = fret_y(board_top, window.fret_min, window.fret_max, tone.fret, board_h)

        draw_note(
            dwg=dwg,
            x=tx,
            y=ty,
            label=tone.degree_label,
            fill=tone_fill(tone, colors),
            outline=colors["note_outline"],
            text_fill=colors["note_text"],
        )


def render_diagram_spec_svg(
    spec: DiagramSpec,
    output_path: str | Path,
    colors: dict[str, str] | None = None,
) -> Path:
    colors = {**DEFAULT_COLORS, **(colors or {})}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    panel_w = 190
    gap = 22
    margin = 24
    width = margin * 2 + len(spec.shape_windows) * panel_w + (len(spec.shape_windows) - 1) * gap
    height = 340

    dwg = svgwrite.Drawing(
        filename=str(output_path),
        size=(f"{width}px", f"{height}px"),
        profile="full",
    )

    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill=colors["background"]))

    dwg.add(
        dwg.text(
            spec.title,
            insert=(margin, 28),
            fill=colors["title"],
            font_size="20px",
            font_family="Arial",
            font_weight="bold",
        )
    )

    dwg.add(
        dwg.text(
            f"{spec.diagram_type} | super_root={spec.super_root} | chord={spec.chord_root}{spec.chord_quality}",
            insert=(margin, 48),
            fill=colors["subtitle"],
            font_size="12px",
            font_family="Arial",
        )
    )

    x = margin
    y = 68

    for window in spec.shape_windows:
        draw_shape_window(dwg, window, x, y, colors)
        x += panel_w + gap

    dwg.save()
    return output_path