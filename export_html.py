"""Export the notebook as a standalone HTML page with interactive charts.

A plain ``jupyter nbconvert --to html`` shows each chart's static PNG, because
nbconvert does not render Plotly's own output type. This swaps every Plotly
output for an embedded interactive chart first (Plotly's JavaScript loaded
once, from its CDN), then exports as usual. It exports the committed outputs;
it does not re-run anything.

    uv run python export_html.py              # code cells shown
    uv run python export_html.py --no-code    # prose, tables and charts only
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat
import plotly.io as pio
from nbconvert import HTMLExporter

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE / "positioning-for-inflation-surprises.ipynb"
PLOTLY_MIME = "application/vnd.plotly.v1+json"


def interactive_outputs(notebook) -> int:
    """Replace each Plotly output's PNG fallback with embedded interactive HTML."""
    converted = 0
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            if PLOTLY_MIME not in data:
                continue
            fig = pio.from_json(json.dumps(data[PLOTLY_MIME]))
            data["text/html"] = pio.to_html(
                fig,
                full_html=False,
                include_plotlyjs="cdn" if converted == 0 else False,
                config={"displaylogo": False},
            )
            data.pop("image/png", None)
            converted += 1
    return converted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-code", action="store_true", help="hide code cells and prompts")
    parser.add_argument("--out", type=Path, default=NOTEBOOK.with_suffix(".html"))
    args = parser.parse_args()

    notebook = nbformat.read(NOTEBOOK, as_version=4)
    charts = interactive_outputs(notebook)
    exporter = HTMLExporter(exclude_input=args.no_code, exclude_input_prompt=args.no_code,
                            exclude_output_prompt=args.no_code)
    html, _ = exporter.from_notebook_node(notebook)
    args.out.write_text(html, encoding="utf-8")
    print(f"{args.out.name}: {charts} interactive charts, {len(html) / 1e6:.1f}MB")


if __name__ == "__main__":
    main()
