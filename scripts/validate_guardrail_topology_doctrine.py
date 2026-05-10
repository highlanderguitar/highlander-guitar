from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from highlander_render.guardrail_cell_builder import build_minor_pent_guardrail_geometry
from highlander_render.harmony_engine import build_minor_pent_string_spans
from highlander_render.topology_doctrine import (
    DEFAULT_DOCTRINE_PATH,
    Doctrine,
    corridor_id_for_degrees,
    degree_for_position,
    degree_pair_key,
    expected_minor_pent_corridor_sequence,
    load_doctrine,
    pitch_class_to_degree_map,
)


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    details: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    root: str
    findings: list[Finding] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)

    def add_fact(self, message: str) -> None:
        self.facts.append(message)

    def add(self, severity: str, code: str, message: str, details: list[str] | None = None) -> None:
        self.findings.append(Finding(severity, code, message, details or []))

    @property
    def failures(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "FAIL"]

    @property
    def warnings(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "WARN"]


def span_degrees_for_string(
    spans: dict[int, list[tuple[str, int, int]]],
    string_index: int,
    pc_to_degree: dict[int, str],
) -> list[tuple[str, str, str, int, int]]:
    out: list[tuple[str, str, str, int, int]] = []
    for color, fret_a, fret_b in spans.get(string_index, []):
        out.append(
            (
                color,
                degree_for_position(string_index, fret_a, pc_to_degree),
                degree_for_position(string_index, fret_b, pc_to_degree),
                fret_a,
                fret_b,
            )
        )
    return out


def is_allowed_non_scale_span(
    doctrine: Doctrine,
    root: str,
    string_index: int,
    from_degree: str,
    to_degree: str,
    fret_a: int,
    fret_b: int,
) -> bool:
    for allowed in doctrine.allowed_non_scale_segments:
        if allowed.get("root") != root:
            continue
        if list(allowed.get("strings", [])) != [string_index, string_index]:
            continue
        if list(allowed.get("frets", [])) != [fret_a, fret_b]:
            continue
        if degree_pair_key(allowed.get("degree_pair", [])) != degree_pair_key((from_degree, to_degree)):
            continue
        return True
    return False


def validate_corridor_ownership(
    doctrine: Doctrine,
    root: str,
    report: ValidationReport,
) -> None:
    spans = build_minor_pent_string_spans(root)
    pc_to_degree = pitch_class_to_degree_map(root, doctrine)
    corridors_by_degrees = doctrine.corridors_by_degrees
    observed_by_corridor: dict[str, set[str]] = defaultdict(set)

    for string_index in sorted(spans):
        for color, from_degree, to_degree, fret_a, fret_b in span_degrees_for_string(
            spans,
            string_index,
            pc_to_degree,
        ):
            corridor = corridors_by_degrees.get((from_degree, to_degree))
            if corridor is None:
                if is_allowed_non_scale_span(doctrine, root, string_index, from_degree, to_degree, fret_a, fret_b):
                    report.add_fact(
                        f"Allowed non-scale clipped span accepted on string {string_index}, frets {fret_a}->{fret_b}."
                    )
                    continue
                report.add(
                    "FAIL",
                    "unknown_corridor",
                    f"Span {string_index}:{fret_a}->{fret_b} maps to undeclared corridor {from_degree}->{to_degree}.",
                )
                continue

            observed_by_corridor[corridor["id"]].add(color)
            if not corridor["visible"]:
                report.add(
                    "FAIL",
                    "omitted_corridor_visible",
                    f"Omitted corridor {corridor['id']} is visible on string {string_index}, frets {fret_a}->{fret_b}.",
                )
            if color != corridor["color"]:
                report.add(
                    "FAIL",
                    "corridor_color_mismatch",
                    f"{corridor['id']} expected {corridor['color']} but current span is {color}.",
                    [f"string={string_index} frets={fret_a}->{fret_b}"],
                )

    for corridor in doctrine.data["corridors"]:
        observed = observed_by_corridor.get(corridor["id"], set())
        if corridor["visible"] and not observed:
            report.add("FAIL", "visible_corridor_missing", f"Visible corridor {corridor['id']} was not observed.")
        if len(observed) > 1:
            report.add(
                "FAIL",
                "octave_ownership_inconsistent",
                f"{corridor['id']} has multiple colors across octave/string occurrences: {sorted(observed)}.",
            )

    report.add_fact(
        "Corridor ownership checked against current string spans for all visible minor-pent seed corridors."
    )


def validate_e_string_symmetry(
    doctrine: Doctrine,
    root: str,
    report: ValidationReport,
) -> None:
    spans = build_minor_pent_string_spans(root)
    pc_to_degree = pitch_class_to_degree_map(root, doctrine)
    rule = doctrine.data["e_string_symmetry"]
    low_e = int(rule["low_e_string"])
    high_e = int(rule["high_e_string"])
    low_pattern = [
        (color, from_degree, to_degree, fret_b - fret_a)
        for color, from_degree, to_degree, fret_a, fret_b in span_degrees_for_string(spans, low_e, pc_to_degree)
    ]
    high_pattern = [
        (color, from_degree, to_degree, fret_b - fret_a)
        for color, from_degree, to_degree, fret_a, fret_b in span_degrees_for_string(spans, high_e, pc_to_degree)
    ]

    if low_pattern != high_pattern:
        report.add(
            "FAIL",
            "e_string_symmetry_mismatch",
            "Low E and high E span ownership patterns differ.",
            [f"low_e={low_pattern}", f"high_e={high_pattern}"],
        )
    else:
        report.add_fact(f"E-string symmetry passed for strings {low_e} and {high_e}.")


def validate_b_string_warp(
    doctrine: Doctrine,
    root: str,
    report: ValidationReport,
) -> None:
    geometry = build_minor_pent_guardrail_geometry(root)
    rule = doctrine.data["b_string_warp"]
    g_string = int(rule["g_string"])
    b_string = int(rule["b_string"])
    g_to_b_delta = int(rule["g_to_b_delta"])
    b_to_g_delta = int(rule["b_to_g_delta"])
    checked = 0

    for segment in geometry.segments:
        s1 = segment.start.string_index
        s2 = segment.end.string_index
        f1 = segment.start.fret
        f2 = segment.end.fret

        if {s1, s2} != {g_string, b_string}:
            continue

        checked += 1
        if s1 == g_string and s2 == b_string:
            expected = f1 + g_to_b_delta
            if f2 != expected:
                report.add(
                    "FAIL",
                    "invalid_g_b_warp",
                    f"Expected G/B warp {g_string}:{f1} -> {b_string}:{expected}, got {s1}:{f1} -> {s2}:{f2}.",
                    [segment.cell_id],
                )
        elif s1 == b_string and s2 == g_string:
            expected = f1 + b_to_g_delta
            if f2 != expected:
                report.add(
                    "FAIL",
                    "invalid_b_g_warp",
                    f"Expected B/G warp {b_string}:{f1} -> {g_string}:{expected}, got {s1}:{f1} -> {s2}:{f2}.",
                    [segment.cell_id],
                )

        if f1 == f2:
            report.add(
                "FAIL",
                "same_fret_g_b_shortcut",
                f"Invalid same-fret G/B shortcut found: {s1}:{f1} -> {s2}:{f2}.",
                [segment.cell_id],
            )

    report.add_fact(f"B-string warp checked on {checked} G/B crossing segment(s).")


def segment_degree_pair(segment: Any, pc_to_degree: dict[int, str]) -> tuple[str, str]:
    return degree_pair_key(
        (
            degree_for_position(segment.start.string_index, segment.start.fret, pc_to_degree),
            degree_for_position(segment.end.string_index, segment.end.fret, pc_to_degree),
        )
    )


def validate_shared_edges(
    doctrine: Doctrine,
    root: str,
    report: ValidationReport,
) -> None:
    geometry = build_minor_pent_guardrail_geometry(root)
    pc_to_degree = pitch_class_to_degree_map(root, doctrine)
    observed: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: {"roles": set(), "colors": set()})

    for segment in geometry.segments:
        pair = segment_degree_pair(segment, pc_to_degree)
        observed[pair]["roles"].add(segment.role)
        observed[pair]["colors"].add(segment.color)

    for pair, shared in doctrine.shared_degree_pairs.items():
        roles = observed[pair]["roles"]
        colors = observed[pair]["colors"]
        missing_roles = set(shared["owners"]) - roles
        missing_colors = set(shared["colors"]) - colors
        if missing_roles or missing_colors:
            report.add(
                "FAIL",
                "shared_edge_missing_owner",
                f"Shared edge {shared['id']} is missing required semantic ownership.",
                [
                    f"observed_roles={sorted(roles)} required_roles={shared['owners']}",
                    f"observed_colors={sorted(colors)} required_colors={shared['colors']}",
                ],
            )

    report.add_fact("Shared edge semantic ownership checked against flattened GuardrailGeometry segments.")


def validate_global_ownership_consistency(
    doctrine: Doctrine,
    root: str,
    report: ValidationReport,
) -> None:
    if not doctrine.data.get("global_ownership_consistency", {}).get("enabled", False):
        return

    geometry = build_minor_pent_guardrail_geometry(root)
    pc_to_degree = pitch_class_to_degree_map(root, doctrine)
    shared_pairs = set(doctrine.shared_degree_pairs)
    observed: dict[tuple[str, str], dict[str, list[str]]] = defaultdict(lambda: {"roles": [], "cell_ids": []})

    for cell in geometry.cells:
        cell_degrees = sorted(
            {
                degree_for_position(point.string_index, point.fret, pc_to_degree)
                for point in cell.points
                if degree_for_position(point.string_index, point.fret, pc_to_degree) != "non_scale"
            }
        )
        for i, from_degree in enumerate(cell_degrees):
            for to_degree in cell_degrees[i + 1:]:
                pair = degree_pair_key((from_degree, to_degree))
                observed[pair]["roles"].append(cell.role)
                observed[pair]["cell_ids"].append(cell.cell_id)

    for pair, data in sorted(observed.items()):
        if pair in shared_pairs:
            continue

        roles = sorted(set(data["roles"]))
        if len(roles) > 1:
            report.add(
                "FAIL",
                "global_corridor_ownership_inconsistent",
                f"Pitch-class corridor {pair[0]}<->{pair[1]} has multiple ownership roles: {roles}.",
                [
                    "This is a global doctrine violation unless the pair is declared as a shared edge or explicit exception.",
                    f"claiming_cells={data['cell_ids']}",
                ],
            )

    report.add_fact("Global ownership consistency checked for all observed pitch-class degree pairs in cells.")


def validate_octave_sequence(
    doctrine: Doctrine,
    root: str,
    report: ValidationReport,
) -> None:
    spans = build_minor_pent_string_spans(root)
    pc_to_degree = pitch_class_to_degree_map(root, doctrine)
    expected_sequence = expected_minor_pent_corridor_sequence(doctrine)

    for string_index in sorted(spans):
        observed = [
            (from_degree, to_degree, fret_a, fret_b)
            for _, from_degree, to_degree, fret_a, fret_b in span_degrees_for_string(spans, string_index, pc_to_degree)
        ]
        for from_degree, to_degree, fret_a, fret_b in observed:
            if is_allowed_non_scale_span(doctrine, root, string_index, from_degree, to_degree, fret_a, fret_b):
                continue
            pair = (from_degree, to_degree)
            if pair not in expected_sequence:
                report.add(
                    "FAIL",
                    "octave_sequence_unknown",
                    f"String {string_index} contains non-seed corridor {corridor_id_for_degrees(*pair)}.",
                )

    report.add_fact("Octave propagation checked by reducing all visible spans to canonical degree corridors.")


def render_report(report: ValidationReport) -> str:
    lines = [
        f"# Guardrail Topology Doctrine Report: {report.root} minor pent",
        "",
        f"Status: {'FAIL' if report.failures else 'PASS'}",
        f"Failures: {len(report.failures)}",
        f"Warnings: {len(report.warnings)}",
        "",
        "## Facts",
        "",
    ]
    lines.extend(f"- {fact}" for fact in report.facts)
    lines.extend(["", "## Findings", ""])

    if not report.findings:
        lines.append("- No findings.")
    else:
        for finding in report.findings:
            lines.append(f"- {finding.severity} `{finding.code}`: {finding.message}")
            for detail in finding.details:
                lines.append(f"  - {detail}")

    lines.append("")
    return "\n".join(lines)


def validate(root: str, doctrine_path: Path, report_path: Path) -> ValidationReport:
    doctrine = load_doctrine(doctrine_path)
    report = ValidationReport(root=root)

    validate_corridor_ownership(doctrine, root, report)
    validate_octave_sequence(doctrine, root, report)
    validate_e_string_symmetry(doctrine, root, report)
    validate_b_string_warp(doctrine, root, report)
    validate_shared_edges(doctrine, root, report)
    validate_global_ownership_consistency(doctrine, root, report)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(report), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate current guardrail geometry against topology doctrine fixtures.")
    parser.add_argument("--root", default="B", help="Minor pentatonic root to validate.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_DOCTRINE_PATH)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "output" / "b_minor_topology_doctrine_report.md",
    )
    args = parser.parse_args()

    report = validate(args.root, args.fixture, args.report)
    print(render_report(report))
    print(f"Wrote: {args.report}")
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
