"""Build and test the checked-in C17 memory laboratory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def compiler_command() -> tuple[str, str]:
    requested = os.environ.get("CC")
    if requested:
        discovered = shutil.which(requested)
        if not discovered:
            raise RuntimeError(f"CC does not resolve to an executable: {requested}")
        name = Path(discovered).name.lower()
        return discovered, "msvc" if name in {"cl", "cl.exe"} else "unix"
    candidates = ("cl", "gcc", "clang") if os.name == "nt" else ("cc", "gcc", "clang")
    for candidate in candidates:
        discovered = shutil.which(candidate)
        if discovered:
            return discovered, "msvc" if candidate == "cl" else "unix"
    raise RuntimeError("No C17 compiler was found. Set CC to cl, gcc, or clang.")


def compile_target(
    compiler: str,
    family: str,
    root: Path,
    output: Path,
    sources: list[Path],
) -> list[str]:
    include = root / "native" / "include"
    if family == "msvc":
        command = [
            compiler,
            "/nologo",
            "/TC",
            "/std:c17",
            "/W4",
            "/WX",
            "/O2",
            "/D_CRT_SECURE_NO_WARNINGS",
            f"/I{include}",
            *[str(source) for source in sources],
            f"/Fe:{output.name}",
        ]
    else:
        command = [
            compiler,
            "-std=c17",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            "-O2",
            "-I",
            str(include),
            *[str(source) for source in sources],
            "-o",
            str(output),
        ]
    subprocess.run(command, cwd=output.parent, check=True)
    return command


def build(root: Path) -> dict[str, object]:
    compiler, family = compiler_command()
    destination = root / "build" / "native"
    destination.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if os.name == "nt" else ""
    executable = destination / f"memory_lab{suffix}"
    tests = destination / f"test_memory_lab{suffix}"
    library = root / "native" / "src" / "memory_lab.c"
    executable_command = compile_target(
        compiler,
        family,
        root,
        executable,
        [library, root / "native" / "src" / "main.c"],
    )
    test_command = compile_target(
        compiler,
        family,
        root,
        tests,
        [library, root / "native" / "tests" / "test_memory_lab.c"],
    )
    test_result = subprocess.run(
        [str(tests)], cwd=root, text=True, capture_output=True, check=True, timeout=15
    )
    layout = json.loads(
        subprocess.run(
            [str(executable), "layout"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
            timeout=15,
        ).stdout
    )
    return {
        "schema": "mydatalabnotes.native-build.v1",
        "compiler": compiler,
        "compiler_family": family,
        "executable": str(executable.relative_to(root)),
        "test_executable": str(tests.relative_to(root)),
        "executable_command": executable_command,
        "test_command": test_command,
        "test_output": test_result.stdout.strip(),
        "layout": layout,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = build(root)
    if args.report:
        destination = args.report if args.report.is_absolute() else root / args.report
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["test_output"])
    print(json.dumps(report["layout"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
