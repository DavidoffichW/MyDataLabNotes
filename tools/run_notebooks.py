"""Execute the R1 notebook in fresh kernels and compare deterministic evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any

import nbformat
import psutil
from nbclient import NotebookClient

NOTEBOOK = "001_how_do_we_know_an_algorithm_worked.ipynb"
VARIABLE_TAGS = {"environment", "measurement"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output-dir", type=Path)
    destination.add_argument("--in-place", action="store_true")
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def deterministic_digest(notebook: Any) -> str:
    cells: list[dict[str, Any]] = []
    for cell in notebook.cells:
        tags = set(cell.metadata.get("tags", []))
        if cell.cell_type != "code" or tags & VARIABLE_TAGS:
            continue
        outputs = []
        for output in cell.get("outputs", []):
            normalized = dict(output)
            normalized.pop("execution_count", None)
            normalized.pop("metadata", None)
            outputs.append(normalized)
        cells.append({"source": cell.source, "outputs": outputs})
    encoded = json.dumps(cells, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _rss_monitor(stop: threading.Event, peak: list[int]) -> None:
    process = psutil.Process(os.getpid())
    while not stop.wait(0.02):
        total = process.memory_info().rss
        for child in process.children(recursive=True):
            try:
                total += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        peak[0] = max(peak[0], total)


def execute_once(source: Path, root: Path) -> tuple[Any, dict[str, Any]]:
    notebook = nbformat.read(source, as_version=4)
    stop = threading.Event()
    peak = [psutil.Process().memory_info().rss]
    monitor = threading.Thread(target=_rss_monitor, args=(stop, peak), daemon=True)
    started = time.perf_counter()
    monitor.start()
    try:
        NotebookClient(
            notebook,
            timeout=300,
            kernel_name="python3",
            resources={"metadata": {"path": str(root)}},
        ).execute()
    finally:
        stop.set()
        monitor.join(timeout=2)
    elapsed = time.perf_counter() - started
    for cell in notebook.cells:
        cell.metadata.pop("execution", None)
        alt = cell.metadata.get("alt")
        if alt:
            for output in cell.get("outputs", []):
                if "image/png" in output.get("data", {}):
                    output.metadata.setdefault("image/png", {})["alt"] = alt
    return notebook, {
        "wall_seconds": round(elapsed, 3),
        "peak_rss_bytes": peak[0],
        "deterministic_digest": deterministic_digest(notebook),
    }


def main() -> int:
    args = parse_args()
    if args.repeat < 1:
        raise SystemExit("--repeat must be at least one")

    root = Path(__file__).resolve().parents[1]
    source = root / "notebooks" / NOTEBOOK
    output_dir = source.parent if args.in_place else args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / NOTEBOOK

    runs: list[dict[str, Any]] = []
    executed = None
    for run_number in range(1, args.repeat + 1):
        executed, observation = execute_once(source, root)
        observation["run"] = run_number
        runs.append(observation)
        print(
            f"run {run_number}: {observation['wall_seconds']:.3f}s, "
            f"peak RSS {observation['peak_rss_bytes'] / 2**20:.1f} MiB"
        )

    digests = {run["deterministic_digest"] for run in runs}
    if len(digests) != 1:
        raise SystemExit("deterministic evidence changed across fresh-kernel runs")

    if not args.in_place:
        shutil.copy2(source, destination)
    assert executed is not None
    nbformat.write(executed, destination)

    report = {
        "schema": "mydatalabnotes.notebook-run.v1",
        "notebook": NOTEBOOK,
        "repeat": args.repeat,
        "deterministic_match": True,
        "runs": runs,
    }
    if args.report:
        report_path = args.report.resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"deterministic evidence: {next(iter(digests))}")
    print(f"executed notebook: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
