from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".hypothesis",
    ".ipynb_checkpoints",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "output",
}


def test_mit_license_and_metadata_are_consistent() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "LICENSING_STATUS.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert license_text.startswith("MIT License\n\nCopyright (c) 2026 DavidoffichW")
    assert "MIT License" in status
    assert "mit license" in readme
    assert metadata["project"]["license"] == "MIT"


def test_public_text_contains_no_workspace_or_private_reference_paths() -> None:
    public_files = [
        ROOT / "README.md",
        ROOT / "docs" / "LICENSING_STATUS.md",
        ROOT / "THIRD_PARTY_NOTICES.md",
        *sorted((ROOT / "docs").glob("*.md")),
    ]
    forbidden = (r"[a-z]:\\users\\", r"[a-z]:\\projects\\github-portfolio", "ghp_docs")
    for path in public_files:
        text = path.read_text(encoding="utf-8").lower()
        assert not any(re.search(pattern, text) for pattern in forbidden), path.name


def test_candidate_contains_no_binary_or_private_data_files() -> None:
    forbidden_suffixes = {
        ".csv",
        ".xlsx",
        ".pdf",
        ".db",
        ".sqlite",
        ".zip",
        ".pt",
        ".onnx",
        ".exe",
        ".dll",
        ".obj",
        ".o",
        ".so",
    }
    forbidden = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in forbidden_suffixes
        and not EXCLUDED_PARTS.intersection(path.parts)
    ]
    assert not forbidden


def test_relative_markdown_links_resolve() -> None:
    markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
    missing: list[str] = []
    for path in markdown_files:
        for target in link_pattern.findall(path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            clean_target = target.split("#", 1)[0]
            if clean_target and not (path.parent / clean_target).resolve().exists():
                missing.append(f"{path.relative_to(ROOT)} -> {target}")
    assert not missing
