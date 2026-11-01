"""Check that the executed NB-001 copy contains readable experimental evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()

    notebook = nbformat.read(args.notebook, as_version=4)
    outputs = [output for cell in notebook.cells for output in cell.get("outputs", [])]
    errors = [output for output in outputs if output.output_type == "error"]
    if errors:
        raise SystemExit(f"notebook contains {len(errors)} error outputs")

    missing = []
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code" or "silent" in cell.metadata.get("tags", []):
            continue
        if not cell.get("outputs"):
            missing.append(index)
    if missing:
        raise SystemExit(f"evidence cells without outputs: {missing}")
    if len(outputs) < 18:
        raise SystemExit(f"expected at least 18 compact outputs, found {len(outputs)}")

    text = "\n".join(
        str(output.get("text", ""))
        + str(output.get("data", {}).get("text/plain", ""))
        for output in outputs
    )
    required = {
        "all_postconditions",
        "minimal counterexample",
        "deterministic randomized cases",
        "metamorphic cases",
    }
    absent = sorted(token for token in required if token not in text.lower())
    if absent:
        raise SystemExit(f"missing expected evidence markers: {absent}")

    print(
        f"executed notebook check passed: {len(notebook.cells)} cells, "
        f"{len(outputs)} outputs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
