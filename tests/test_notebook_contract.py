from __future__ import annotations

import ast
import re
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.ipynb"))


def test_declared_notebooks_are_implemented() -> None:
    assert [path.name for path in NOTEBOOKS] == [
        "001_how_do_we_know_an_algorithm_worked.ipynb",
        "002_the_same_value_different_bytes.ipynb",
    ]


def test_code_cells_are_short_and_progressive() -> None:
    for path in NOTEBOOKS:
        notebook = nbformat.read(path, as_version=4)
        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        lengths = [len(cell.source.splitlines()) for cell in code_cells]
        assert max(lengths) <= 30, path.name
        assert sum(lengths) / len(lengths) <= 12, path.name
        tree = ast.parse("\n\n".join(cell.source for cell in code_cells))
        assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))


def test_research_narrative_contains_required_reasoning() -> None:
    required_by_notebook = {
        "001_how_do_we_know_an_algorithm_worked.ipynb": {
            "research question",
            "precondition",
            "postcondition",
            "invariant",
            "evidence",
            "limitation",
            "what it does not establish",
            "synthesis",
        },
        "002_the_same_value_different_bytes.ipynb": {
            "research question",
            "hypothesis",
            "object",
            "alignment",
            "endianness",
            "checkpoint",
            "reconstruction",
            "irretrievably lost",
            "synthesis",
        },
    }
    for path in NOTEBOOKS:
        notebook = nbformat.read(path, as_version=4)
        markdown = "\n".join(
            cell.source.lower() for cell in notebook.cells if cell.cell_type == "markdown"
        )
        required = required_by_notebook[path.name]
        assert not (required - {term for term in required if term in markdown}), path.name
        assert len(markdown.split()) >= 1_000, path.name


def test_notebook_has_compact_executed_outputs_without_errors() -> None:
    expectations = {
        "001_how_do_we_know_an_algorithm_worked.ipynb": (18, 4),
        "002_the_same_value_different_bytes.ipynb": (25, 7),
    }
    for path in NOTEBOOKS:
        notebook = nbformat.read(path, as_version=4)
        outputs = [output for cell in notebook.cells for output in cell.get("outputs", [])]
        images = [output for output in outputs if "image/png" in output.get("data", {})]
        minimum_outputs, expected_images = expectations[path.name]
        assert len(outputs) >= minimum_outputs, path.name
        assert not [output for output in outputs if output.output_type == "error"]
        assert len(images) == expected_images, path.name
        assert all(image.metadata.get("image/png", {}).get("alt") for image in images)
        assert path.stat().st_size < 3_000_000


def test_private_paths_are_absent() -> None:
    forbidden = (r"[a-z]:\\users\\", r"[a-z]:\\projects\\", "mydatalabnotes_codex")
    for path in NOTEBOOKS:
        text = path.read_text(encoding="utf-8").lower()
        assert not any(re.search(pattern, text) for pattern in forbidden), path.name
