# MyDataLabNotes

MyDataLabNotes is a collection of Jupyter notebooks exploring data structures,
algorithms, and numerical computing through worked examples and experiments.
The goal is to understand how something works, where its assumptions matter,
and what the results actually tell us.

## Investigations

**[How do we know an algorithm worked?](notebooks/001_how_do_we_know_an_algorithm_worked.ipynb)**

Insertion sort provides a small enough example to trace by hand, check against
an independent implementation, and test with generated inputs. A deliberately
broken version reveals how a convincing result can still be wrong. Binary
search adds another lesson: an algorithm needs its input assumptions to hold.

The notebook includes tests, plots, and recorded outputs. All examples use
synthetic data. Correctness and performance are examined separately; a fast
answer is not necessarily the right one.

**[The Same Value, Different Bytes](notebooks/002_the_same_value_different_bytes.ipynb)**

A C17 memory laboratory and an independent Python oracle examine integer
widths, byte order, native structure layout, and a portable binary packet. The
experiment records bounded memory operations, rebuilds earlier states from
that evidence, then removes or corrupts events to find the point where replay
stops being trustworthy. Memory does not secretly remember overwritten bytes;
the event record does the remembering.

## Run locally

Use Python 3.12, a C17 compiler, and
[uv](https://docs.astral.sh/uv/getting-started/installation/). GCC or Clang works
on Ubuntu. On Windows, use a shell where either GCC or Visual Studio's `cl` is
available on `PATH`.

```powershell
uv sync --locked --extra dev
uv run jupyter lab
```

Open either notebook and run its cells in order. You can also read the saved
figures and outputs directly on GitHub.

To run the tests and re-execute the notebook in fresh kernels:

```powershell
uv run python tools/validate.py
```

The command compiles and tests the native laboratory, checks the dependency
lock, runs Ruff and the Python test suite, repeats both notebook executions,
and compares their reproducible results. See the
[reproducibility guide](docs/REPRODUCIBILITY.md) for details and
[sources](docs/SOURCES.md) for the references behind the study.

## Limits

The tests cover stated contracts and specific finite input sets. They do not
amount to a proof for every possible input. Native object layouts belong to the
observed compiler and ABI; only the declared packet format is meant to be
portable. Timings describe the measured implementation and environment, not a
universal speed ranking.

## License

MyDataLabNotes is available under the [MIT License](LICENSE). Third-party
packages and cited works retain their own terms; see
[third-party notices](THIRD_PARTY_NOTICES.md) and [sources](docs/SOURCES.md).
