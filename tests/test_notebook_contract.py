from __future__ import annotations

import ast
import re
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.ipynb"))


def test_only_nb001_is_implemented() -> None:
    assert [path.name for path in NOTEBOOKS] == [
        "001_how_do_we_know_an_algorithm_worked.ipynb"
    ]


def test_code_cells_are_short_and_progressive() -> None:
    notebook = nbformat.read(NOTEBOOKS[0], as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    lengths = [len(cell.source.splitlines()) for cell in code_cells]
    assert max(lengths) <= 30
    assert sum(lengths) / len(lengths) <= 12
    tree = ast.parse("\n\n".join(cell.source for cell in code_cells))
    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))


def test_research_narrative_contains_required_reasoning() -> None:
    notebook = nbformat.read(NOTEBOOKS[0], as_version=4)
    markdown = "\n".join(
        cell.source.lower() for cell in notebook.cells if cell.cell_type == "markdown"
    )
    required = {
        "research question",
        "precondition",
        "postcondition",
        "invariant",
        "evidence",
        "limitation",
        "what it does not establish",
        "synthesis",
    }
    assert not (required - {term for term in required if term in markdown})
    assert len(markdown.split()) >= 1_000


def test_notebook_has_compact_executed_outputs_without_errors() -> None:
    notebook = nbformat.read(NOTEBOOKS[0], as_version=4)
    outputs = [output for cell in notebook.cells for output in cell.get("outputs", [])]
    images = [output for output in outputs if "image/png" in output.get("data", {})]
    assert len(outputs) >= 18
    assert not [output for output in outputs if output.output_type == "error"]
    assert len(images) == 4
    assert all(image.metadata.get("image/png", {}).get("alt") for image in images)
    assert NOTEBOOKS[0].stat().st_size < 2_000_000


def test_private_paths_are_absent() -> None:
    text = NOTEBOOKS[0].read_text(encoding="utf-8").lower()
    forbidden = (r"[a-z]:\\users\\", r"[a-z]:\\projects\\", "mydatalabnotes_codex")
    assert not any(re.search(pattern, text) for pattern in forbidden)
