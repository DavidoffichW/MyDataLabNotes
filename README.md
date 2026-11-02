# MyDataLabNotes

MyDataLabNotes is a collection of Jupyter notebooks exploring data structures,
algorithms, and numerical computing through worked examples and experiments.
The goal is to understand how something works, where its assumptions matter,
and what the results actually tell us.

## Start with an experiment

**[How do we know an algorithm worked?](notebooks/001_how_do_we_know_an_algorithm_worked.ipynb)**

Insertion sort provides a small enough example to trace by hand, check against
an independent implementation, and test with generated inputs. A deliberately
broken version reveals how a convincing result can still be wrong. Binary
search adds another lesson: an algorithm needs its input assumptions to hold.

The notebook includes tests, plots, and recorded outputs. All examples use
synthetic data. Correctness and performance are examined separately; a fast
answer is not necessarily the right one.

## Run locally

Use Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/):

```powershell
uv sync --locked --extra dev
uv run jupyter lab
```

Open the notebook and run its cells in order. You can also read its saved
figures and outputs directly on GitHub.

To run the tests and re-execute the notebook in fresh kernels:

```powershell
uv run python tools/validate.py
```

The command checks the dependency lock, runs Ruff and the test suite, repeats
the notebook execution, and compares its reproducible results. See the
[reproducibility guide](docs/REPRODUCIBILITY.md) for details and
[sources](docs/SOURCES.md) for the references behind the study.

## Limits

The tests cover stated contracts and specific finite input sets. They do not
amount to a proof for every possible input. Timings describe the measured
implementation and environment, not a universal speed ranking.

## License

MyDataLabNotes is available under the [MIT License](LICENSE). Third-party
packages and cited works retain their own terms; see
[third-party notices](THIRD_PARTY_NOTICES.md) and [sources](docs/SOURCES.md).
