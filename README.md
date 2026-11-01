# MyDataLabNotes

Algorithms are easy to run. Knowing whether they worked is the interesting
part.

MyDataLabNotes is a notebook-first research series about data structures,
algorithms, representation, numerical methods, and the evidence needed to trust
computational results. R1 contains one complete investigation:

- [NB-001 — How do we know an algorithm worked?](notebooks/001_how_do_we_know_an_algorithm_worked.ipynb)

NB-001 starts with a contract, traces an invariant, compares independent
implementations, exhausts a tiny domain, generates reproducible cases, shrinks
an injected defect, checks metamorphic relations, and then shows why wall-clock
measurements are a different kind of evidence. Every dataset is synthetic.

NB-002 and NB-004 are planned but intentionally absent. One finished notebook
beats three half-finished ones.

The first notebook separates correctness from performance: contracts, oracles,
and finite tests address what an algorithm computes; timings describe a
particular implementation and environment. The same distinction will matter
in later data and ML studies, where speed alone cannot establish validity.

## Run it

The qualified environment is CPython 3.12. Install
[uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```powershell
uv sync --locked --extra dev
uv run jupyter lab
```

Open the linked notebook and run it from the first cell. The committed notebook
already contains compact outputs so it can be read on GitHub without a local
environment.

For the complete quick check:

```powershell
uv run python tools/validate.py
```

That command checks the lock, runs Ruff and the independent test suite, executes
NB-001 twice in fresh kernels, compares deterministic evidence, and validates
the resulting outputs. The quick profile targets less than 60 seconds and
1 GiB of peak process-tree RSS; the observed local result belongs in validation
evidence, not in a timeless performance promise.

See [Reproducing NB-001](docs/REPRODUCIBILITY.md) for output refresh and
measurement details, and [Sources](docs/SOURCES.md) for the reviewed reference
set.

## What this establishes

The experiments provide bounded evidence for the stated integer-sequence
contracts. They do not prove the interpreter, libraries, or hardware correct,
and they do not turn finite testing into a proof over unbounded inputs. The
notebook says where each claim stops.

## License

MyDataLabNotes is available under the [MIT License](LICENSE). Third-party
packages and cited works retain their own terms; see
[Third-party notices](THIRD_PARTY_NOTICES.md) and [Sources](docs/SOURCES.md).
