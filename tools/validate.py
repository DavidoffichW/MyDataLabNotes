"""Run the quick R1 validation profile."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def uv_executable() -> str:
    discovered = shutil.which("uv")
    if discovered and "pyenv" not in discovered.lower():
        return discovered
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        winget_uv = Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "uv.exe"
        if winget_uv.exists():
            return str(winget_uv)
    return discovered or "uv"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    python = sys.executable
    started = time.perf_counter()
    environment = {
        **os.environ,
        "MPLBACKEND": "Agg",
        "PATH": str(Path(python).parent) + os.pathsep + os.environ.get("PATH", ""),
        "PYTHONHASHSEED": "0",
    }

    commands = [
        [uv_executable(), "lock", "--check"],
        [python, "-m", "ruff", "check", "."],
        [python, "-m", "pytest", "-q"],
        [
            python,
            "tools/run_notebooks.py",
            "--output-dir",
            "build/executed",
            "--repeat",
            "2",
            "--report",
            "build/validation/notebook_run.json",
        ],
        [
            python,
            "tools/check_executed_notebook.py",
            "build/executed/001_how_do_we_know_an_algorithm_worked.ipynb",
        ],
    ]
    for command in commands:
        print(f"\n> {' '.join(command)}", flush=True)
        subprocess.run(command, cwd=root, env=environment, check=True)
    print(f"\nquick validation passed in {time.perf_counter() - started:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
