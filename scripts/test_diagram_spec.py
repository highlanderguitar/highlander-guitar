from highlander_render.diagram_spec_builder import build_minor_pent_guardrail_diagram_spec


def main() -> None:
    spec = build_minor_pent_guardrail_diagram_spec("B")

    print(spec.title)
    print("tones:", len(spec.tones))
    print("shape_windows:", len(spec.shape_windows))

    for window in spec.shape_windows[:5]:
        print(
            f"Shape {window.shape_id}: "
            f"frets {window.fret_min}-{window.fret_max}, "
            f"tones={len(window.tones)}, "
            f"edges={len(window.edges)}"
        )


if __name__ == "__main__":
    main()