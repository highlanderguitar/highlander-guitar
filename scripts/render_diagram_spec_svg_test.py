from highlander_render.diagram_spec_builder import build_minor_pent_guardrail_diagram_spec
from highlander_render.diagram_spec_svg_renderer import render_diagram_spec_svg


def main() -> None:
    spec = build_minor_pent_guardrail_diagram_spec("B")
    out = render_diagram_spec_svg(spec, "output/guardrail_spec_clean.svg")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()