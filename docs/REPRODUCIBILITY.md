# Reproducing the notebooks

The qualified profile is CPython 3.12 with a C17 compiler on Windows and
Ubuntu. `pyproject.toml` keeps direct dependency declarations readable;
`uv.lock` records the exact resolved Python environment used for validation.
The compiler and flags are reported separately because native object layout is
an environment observation, not part of the portable packet identity.

```powershell
uv sync --locked --extra dev
uv run python tools/validate.py
```

The validation command compiles the checked-in C sources, runs native unit
tests, checks the lock, runs Ruff and independent Python tests, and executes
both notebooks twice in fresh kernels. Disposable copies and resource reports
go under `build/`. Deterministic output cells must have the same evidence digest
in both executions. Environment and timing cells are excluded from that
identity because they report observations that can legitimately change.

To build only the native laboratory:

```powershell
uv run python tools/build_native.py
```

The helper selects `cl`, `gcc`, or `clang` from `PATH`, passes that compiler's
C17 and strict-warning flags, and invokes it without shell interpolation. Set
`CC` to an executable name or absolute path to choose a compiler explicitly.
The executable and test binary stay in the ignored `build/native/` directory.
The [memory laboratory protocol](MEMORY_LAB_PROTOCOL.md) documents the packet
and event formats.

To inspect the notebooks interactively:

```powershell
uv run jupyter lab
```

To refresh the compact outputs committed in the notebook:

```powershell
uv run python tools/run_notebooks.py --in-place --repeat 2
```

The default validation path is intentionally small. Heavier experiments should
use separate commands, declared inputs, and explicit resource ceilings rather
than slowing down the ordinary correctness check.

For a deeper replay check without changing the scientific workload, run ten
fresh kernels instead of the two used by the quick profile:

```powershell
uv run python tools/run_notebooks.py `
  --output-dir build/deeper-replay `
  --repeat 10 `
  --report build/validation/deeper-replay.json
```

This optional command checks repeatability more often; it does not make the
finite experiments into a proof or qualify a new performance profile.
