# Reproducing the notebook

The qualified profile is CPython 3.12 on Windows and Ubuntu. `pyproject.toml`
keeps direct dependency declarations readable; `uv.lock` records the exact
resolved environment used for validation.

```powershell
uv sync --locked --extra dev
uv run python tools/validate.py
```

The validation command runs the lock check, Ruff, independent tests, and two
fresh-kernel executions. The notebook runner writes disposable copies and its
resource report under `build/`. Deterministic output cells must have the same
evidence digest in both executions. Environment and timing cells are excluded
from that identity because they report observations that can legitimately
change.

To inspect the notebook interactively:

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
