"""Build the NB-001 source notebook from reviewable cell definitions."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat


def md(text: str) -> dict:
    return nbformat.v4.new_markdown_cell(dedent(text).strip())


def code(text: str, *tags: str, alt: str | None = None) -> dict:
    metadata = {"tags": list(tags)} if tags else {}
    if alt:
        metadata["alt"] = alt
    return nbformat.v4.new_code_cell(dedent(text).strip(), metadata=metadata)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    destination = root / "notebooks" / "001_how_do_we_know_an_algorithm_worked.ipynb"

    cells = [
        md(
            """
            # NB-001 — How do we know an algorithm worked?

            A program can finish, print something plausible, and still be wrong. This
            investigation builds several kinds of evidence around two deliberately small
            algorithms: insertion sort is the main object of study, while first-match
            binary search shows why preconditions matter.

            **Research question.** What combination of specification, invariant,
            independent oracle, generated cases, and measurement gives defensible evidence
            that an implementation satisfies its contract?

            The notebook uses only synthetic integer sequences. It does not attempt a
            sorting or searching survey; later notebooks own that work. Sources are cited by
            the identifiers in `docs/SOURCES.md`, especially CLRS for invariants and
            correctness [S005], Hypothesis for property-based search [S064], and Python and
            pyperf documentation for measurement limits [S061, S063].
            """
        ),
        code(
            """
            import gc
            import inspect
            import platform
            import time
            import tracemalloc
            from bisect import bisect_left
            from importlib.metadata import version
            """,
            "silent",
        ),
        code(
            """

            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd
            from hypothesis import find, settings
            from hypothesis import strategies as st
            from IPython import get_ipython
            from IPython.display import Code, display

            from mydatalabnotes.algorithms import (
                binary_search_first,
                buggy_insertion_sort,
                insertion_sort,
                insertion_sort_trace,
                sorting_contract,
            )
            from mydatalabnotes.evidence import (
                canonical_json_sha256,
                exhaustive_integer_sequences,
            )
            """,
            "silent",
        ),
        code(
            """
            SEED = 20261101
            rng = np.random.default_rng(SEED)
            get_ipython().run_line_magic("matplotlib", "inline")
            pd.set_option("display.max_colwidth", 80)
            plt.style.use("seaborn-v0_8-whitegrid")
            """,
            "silent",
        ),
        code(
            """
            environment = pd.Series({
                "python": platform.python_version(),
                "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
                "numpy": version("numpy"),
                "pandas": version("pandas"),
                "matplotlib": version("matplotlib"),
                "hypothesis": version("hypothesis"),
                "seed": SEED,
            }, name="recorded environment")
            environment.to_frame()
            """,
            "environment",
        ),
        md(
            """
            The version table is evidence about this execution, not a claim that every
            version produces byte-identical output. The seed fixes the NumPy generator used
            below for this recorded implementation [S062]. Hypothesis is separately run with
            a deterministic profile and no example database.

            ## 1. Correctness needs a contract

            For a finite input sequence $x$, an algorithm is **partially correct** when:

            $$
            P(x) \\land \\text{termination} \\implies Q(x, y),
            $$

            where $P$ is the precondition and $Q$ the postcondition. **Total
            correctness** additionally establishes termination for inputs satisfying
            $P$. Operational correctness also includes the representation, exception, and
            resource behavior promised by the interface. A fast result outside the contract
            is not a correct result.
            """
        ),
        code(
            """
            contract = pd.DataFrame([
                ("Input", "A finite Python sequence whose elements are integers"),
                ("Output", "A new list; the input object is not mutated"),
                ("Order", "result[i] <= result[i + 1] for every valid i"),
                ("Content", "result and input have the same integer multiset"),
                ("Termination", "The finite outer index advances; the inner index decreases"),
                ("Invalid input", "Raise TypeError rather than silently coerce values"),
            ], columns=["contract part", "NB-001 requirement"])
            contract
            """
        ),
        md(
            """
            “Looks sorted” is only one postcondition. A routine that returns an empty list is
            nondecreasing but loses every input value. That is why the order and multiset
            clauses are checked independently. Stability is not part of this integer-only
            experiment's public contract; later sorting work can introduce tagged records
            and test it explicitly.

            ## 2. Trace one implementation and its invariant

            Insertion sort is useful here because its state is small enough to inspect. At
            the start of outer iteration $i$, the prefix before $i$ is sorted and is a
            permutation of the original prefix. The step inserts one key into that prefix.
            This is a loop invariant in the standard initialization–maintenance–termination
            proof pattern [S005].
            """
        ),
        code(
            """
            display(Code(inspect.getsource(insertion_sort), language="python"))
            """
        ),
        code(
            """
            hand_input = [5, 2, 4, 2]
            hand_result, hand_trace = insertion_sort_trace(hand_input)
            trace_frame = pd.DataFrame(hand_trace)
            trace_frame
            """
        ),
        code(
            """
            states = [tuple(hand_input), *trace_frame["state"]]
            fig, ax = plt.subplots(figsize=(7.5, 3.2))
            image = ax.imshow(np.array(states), cmap="RdPu", aspect="auto")
            for row, state in enumerate(states):
                for column, value in enumerate(state):
                    ax.text(column, row, value, ha="center", va="center", color="black")
            ax.set(xlabel="position", ylabel="state", yticks=range(len(states)))
            ax.set_yticklabels(["input", *[f"i={i}" for i in trace_frame["outer"]]])
            fig.colorbar(image, ax=ax, label="integer value")
            fig.tight_layout()
            display(fig)
            plt.close(fig)
            """
            ,
            alt="Heatmap of four insertion-sort states for values 5, 2, 4, 2",
        ),
        md(
            """
            The table and state image expose every outer transition. Duplicate `2` values
            remain present, and the shaded prefix grows from the left without requiring us
            to infer hidden state. For this input, the last state is nondecreasing, but the
            postconditions still need explicit checks.
            """
        ),
        code(
            """
            hand_evidence = pd.Series(
                sorting_contract(hand_input, hand_result), name="observed postconditions"
            )
            hand_evidence.to_frame()
            """
        ),
        md(
            """
            Every observed postcondition is true for the hand example. This is useful
            evidence and a readable trace, but it does not establish correctness for all
            valid sequences.

            ## 3. Boundary cases and independent oracles

            We next separate examples chosen for meaning from generated cases chosen for
            coverage. Python's `sorted` is an independent implementation oracle for these
            integer inputs; it is not a proof of our code, but disagreement is decisive
            evidence that at least one implementation or contract interpretation is wrong.
            """
        ),
        code(
            """
            boundary_inputs = [[], [7], [2, 2, 2], [-3, 0, -3], [1, 2, 3], [3, 2, 1]]
            boundary_rows = [
                {"input": values, "result": insertion_sort(values),
                 "reference": sorted(values),
                 "contract": sorting_contract(
                     values, insertion_sort(values)
                 )["all_postconditions"]}
                for values in boundary_inputs
            ]
            pd.DataFrame(boundary_rows)
            """
        ),
        code(
            """
            invalid_inputs = [[1.0], [True], [1, None], "321"]
            invalid_rows = []
            for values in invalid_inputs:
                try:
                    insertion_sort(values)
                    outcome = "accepted"
                except Exception as error:
                    outcome = f"{type(error).__name__}: {error}"
                invalid_rows.append({"input": repr(values), "observed": outcome})
            pd.DataFrame(invalid_rows)
            """
        ),
        code(
            """
            tiny_cases = exhaustive_integer_sequences((-1, 0, 1), max_length=6)
            tiny_failures = [
                values for values in tiny_cases if insertion_sort(values) != sorted(values)
            ]
            pd.Series({
                "exhaustive cases": len(tiny_cases),
                "domain": "{-1, 0, 1}",
                "maximum length": 6,
                "failures": len(tiny_failures),
            }, name="finite-domain evidence").to_frame()
            """
        ),
        md(
            """
            The empty input, duplicates, negative values, sorted and reverse-ordered cases
            satisfy the same contract. Invalid values fail visibly instead of being coerced.
            Exhaustive agreement covers all 1,093 sequences in the declared tiny domain. It
            is complete evidence for that finite domain only; integers of other magnitudes
            and longer sequences remain outside this enumeration.

            ## 4. Preconditions are observable behavior

            First-match binary search demonstrates a different failure mode. Its guarantee
            depends on nondecreasing, random-access input. If that precondition is omitted,
            a returned index can look plausible while having no valid interpretation.
            """
        ),
        code(
            """
            display(Code(inspect.getsource(binary_search_first), language="python"))
            """
        ),
        code(
            """
            search_cases = [([], 2), ([1], 1), ([1, 1, 2, 5], 1), ([1, 3, 5], 4)]
            search_rows = []
            for values, target in search_cases:
                reference = bisect_left(values, target)
                expected = (
                    reference
                    if reference < len(values) and values[reference] == target
                    else -1
                )
                search_rows.append({
                    "values": values, "target": target,
                    "observed": binary_search_first(values, target), "reference": expected,
                })
            pd.DataFrame(search_rows)
            """
        ),
        code(
            """
            try:
                binary_search_first([3, 1, 2], 1)
                precondition_outcome = "unexpectedly accepted"
            except ValueError as error:
                precondition_outcome = f"controlled rejection: {error}"
            pd.Series({"unsorted input": [3, 1, 2], "outcome": precondition_outcome})
            """
        ),
        md(
            """
            The duplicate case returns the first matching index, and the absent case returns
            `-1`, matching the `bisect_left`-based oracle. The unsorted sequence is rejected
            before search. Rejecting an invalid domain is part of correctness; quietly
            searching it would weaken the contract.

            ## 5. Can the tests expose a plausible defect?

            A validation method that passes correct code is not enough. It should also fail
            code with a realistic defect. The next variant changes `cursor >= 0` to
            `cursor > 0`, so the smallest element cannot move past position zero.
            """
        ),
        code(
            """
            display(Code(inspect.getsource(buggy_insertion_sort), language="python"))
            """
        ),
        code(
            """
            defect_rng = np.random.default_rng(SEED)
            randomized_counterexample = None
            for _attempt in range(1, 501):
                length = int(defect_rng.integers(0, 9))
                candidate = defect_rng.integers(-5, 6, size=length).tolist()
                if buggy_insertion_sort(candidate) != sorted(candidate):
                    randomized_counterexample = candidate
                    attempt = _attempt
                    break
            pd.Series({
                "deterministic randomized cases examined": attempt,
                "first counterexample": randomized_counterexample,
            })
            """
        ),
        code(
            """
            integer_lists = st.lists(st.integers(-3, 3), min_size=0, max_size=6)
            minimal_counterexample = find(
                integer_lists,
                lambda values: buggy_insertion_sort(values) != sorted(values),
                settings=settings(
                    max_examples=2_000, derandomize=True, database=None, deadline=None
                ),
            )
            print(f"Minimal counterexample: {minimal_counterexample}")
            """
        ),
        code(
            """
            defect_comparison = pd.DataFrame({
                "implementation": [
                    "reference sorted", "correct insertion", "defective insertion"
                ],
                "result": [
                    sorted(minimal_counterexample),
                    insertion_sort(minimal_counterexample),
                    buggy_insertion_sort(minimal_counterexample),
                ],
            })
            defect_comparison
            """
        ),
        code(
            """
            defect_cases = exhaustive_integer_sequences((-1, 0, 1), max_length=5)
            defect_rates = []
            for length in range(6):
                cases = [values for values in defect_cases if len(values) == length]
                failures = sum(
                    buggy_insertion_sort(values) != sorted(values) for values in cases
                )
                defect_rates.append(
                    {"length": length, "cases": len(cases), "failures": failures}
                )
            defect_frame = pd.DataFrame(defect_rates)
            defect_frame["failure rate"] = defect_frame["failures"] / defect_frame["cases"]
            defect_frame
            """
        ),
        code(
            """
            fig, ax = plt.subplots(figsize=(7, 3.5))
            ax.bar(defect_frame["length"], defect_frame["failure rate"], color="#9d174d")
            ax.set(xlabel="sequence length", ylabel="observed failure rate", ylim=(0, 1))
            ax.set_title("Off-by-one defect over the complete tiny domain")
            fig.tight_layout()
            display(fig)
            plt.close(fig)
            """
            ,
            alt="Bar chart of the defective implementation failure rate by sequence length",
        ),
        md(
            """
            The seeded search finds a reproducible failure, while Hypothesis shrinks the
            failure to a smaller counterexample [S064]. The exhaustive plot explains why a
            handful of happy-path examples could miss the defect: some inputs still happen
            to work. Property-based generation is a search strategy, not a proof of an
            arbitrary program (R0 claim C029).

            ## 6. Metamorphic relations add checks when exact answers are inconvenient

            For integer sorting, adding the same offset to every input should add that
            offset to every sorted output without changing order. Sorting an already sorted
            result should also leave it unchanged. These relations compare executions
            without needing a new expected list for every case.
            """
        ),
        code(
            """
            metamorphic_rng = np.random.default_rng(SEED + 1)
            metamorphic_rows = []
            for case_id in range(200):
                values = metamorphic_rng.integers(-100, 101, size=20).tolist()
                offset = int(metamorphic_rng.integers(-20, 21))
                result = insertion_sort(values)
                translated = insertion_sort([value + offset for value in values])
                metamorphic_rows.append({
                    "case": case_id,
                    "translation": translated == [value + offset for value in result],
                    "idempotence": insertion_sort(result) == result,
                })
            metamorphic_frame = pd.DataFrame(metamorphic_rows)
            """,
            "silent",
        ),
        code(
            """
            pd.Series({
                "metamorphic cases": len(metamorphic_frame),
                "translation failures": int((~metamorphic_frame["translation"]).sum()),
                "idempotence failures": int((~metamorphic_frame["idempotence"]).sum()),
            }, name="metamorphic evidence").to_frame()
            """
        ),
        md(
            """
            Both relations hold for the 200 generated cases. They complement the exact
            oracle, but they are not sufficient by themselves: a function that always
            returned an empty list would satisfy both relations. Evidence quality comes
            from independent and differently fallible checks, not from the number of green
            rows.

            ## 7. Deterministic work and variable measurements

            Correctness results above are deterministic for the declared inputs. Wall-clock
            measurements are observations influenced by the interpreter, operating system,
            caches, and other activity [S061, S063]. We therefore compare operation counts
            separately from repeated elapsed-time batches.
            """
        ),
        code(
            """
            count_rows = []
            for size in [8, 16, 32, 64, 128]:
                values = list(range(size, 0, -1))
                _, trace = insertion_sort_trace(values)
                count_rows.append({
                    "n": size,
                    "comparisons": sum(step["comparisons"] for step in trace),
                    "shifts": sum(step["shifts"] for step in trace),
                    "n squared": size**2,
                })
            count_frame = pd.DataFrame(count_rows)
            count_frame
            """
        ),
        code(
            """
            fig, ax = plt.subplots(figsize=(7, 3.5))
            ax.plot(count_frame["n"], count_frame["comparisons"], "o-", label="comparisons")
            ax.plot(count_frame["n"], count_frame["shifts"], "s-", label="shifts")
            ax.plot(count_frame["n"], count_frame["n squared"], "--", label=r"$n^2$ guide")
            ax.set(xlabel="input length n", ylabel="count", title="Reverse-input work")
            ax.legend()
            fig.tight_layout()
            display(fig)
            plt.close(fig)
            """
            ,
            alt="Comparison and shift counts for reverse inputs alongside an n-squared guide",
        ),
        code(
            """
            workloads = {
                "ordered": list(range(96)),
                "seeded random": np.random.default_rng(SEED).integers(-500, 501, 96).tolist(),
                "reversed": list(range(95, -1, -1)),
            }
            timing_rng = np.random.default_rng(SEED + 2)
            timing_rows = []
            for batch in range(25):
                for name in timing_rng.permutation(list(workloads)):
                    gc.disable()
                    started = time.perf_counter_ns()
                    for _ in range(40):
                        insertion_sort(workloads[name])
                    elapsed = (time.perf_counter_ns() - started) / 40_000_000
                    gc.enable()
                    timing_rows.append(
                        {"batch": batch, "workload": name, "milliseconds": elapsed}
                    )
            timing_frame = pd.DataFrame(timing_rows)
            """,
            "measurement",
            "silent",
        ),
        code(
            """
            timing_summary = timing_frame.groupby("workload")["milliseconds"].agg(
                batches="count", median="median", minimum="min", maximum="max"
            )
            timing_summary.round(4)
            """,
            "measurement",
        ),
        code(
            """
            names = list(workloads)
            samples = [
                timing_frame.loc[timing_frame["workload"] == name, "milliseconds"]
                for name in names
            ]
            fig, ax = plt.subplots(figsize=(7, 3.8))
            ax.boxplot(samples, tick_labels=names, showfliers=True)
            ax.set(ylabel="milliseconds per call", title="Repeated batches on fixed inputs")
            fig.tight_layout()
            display(fig)
            plt.close(fig)
            """,
            "measurement",
            alt="Box plots of repeated insertion-sort timings for three fixed workloads",
        ),
        code(
            """
            tracemalloc.start()
            insertion_sort(workloads["reversed"] * 8)
            current_bytes, peak_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            pd.Series({
                "current traced bytes": current_bytes,
                "peak traced bytes": peak_bytes,
                "scope": "Python allocations visible to tracemalloc; not process RSS",
            }, name="bounded allocation observation").to_frame()
            """,
            "measurement",
        ),
        md(
            """
            The reverse-input comparison and shift counts are exact for this implementation
            and input family. The elapsed-time batches vary even though their inputs and
            outputs are fixed. The timing figure therefore describes this recorded process,
            not a universal ranking or production forecast. The allocation observation is
            similarly narrow: `tracemalloc` does not report every native or process-level
            allocation. The external notebook runner records wall time and peak process-tree
            RSS for the complete fresh-kernel execution.

            ## 8. Evidence ledger
            """
        ),
        code(
            """
            ledger = pd.DataFrame([
                ("Hand trace", "Invariant and transitions are visible", "One input"),
                ("Boundary examples", "Named edge cases meet the contract", "Not exhaustive"),
                ("Independent oracle", "Two implementations agree", "Shared error possible"),
                ("Exhaustive tiny domain", "All 1,093 cases agree", "Finite domain only"),
                ("Seeded random", "Reproducible broad sampling", "Rare defects may remain"),
                ("Property search", "Finds and shrinks a real defect", "Search is not proof"),
                ("Metamorphic relations", "Two cross-run relations hold", "Relations are weak"),
                ("Timing batches", "Shows measured variability", "No scaling proof"),
            ], columns=["evidence", "what it establishes", "what it does not establish"])
            ledger
            """
        ),
        code(
            """
            manifest = pd.Series({
                "notebook_id": "NB-001",
                "schema": "mydatalabnotes.experiment.v1",
                "profile": "quick",
                "seed": SEED,
                "synthetic_domain": "finite integer sequences",
                "tiny_domain_sha256": canonical_json_sha256(tiny_cases),
                "oracle": "Python sorted / bisect_left",
                "timer": "time.perf_counter_ns",
                "memory": "tracemalloc in notebook; process-tree RSS in runner",
                "correctness_tolerance": "exact integer equality",
            }, name="experiment manifest")
            manifest.to_frame()
            """,
            "environment",
        ),
        md(
            """
            ## Synthesis: what the evidence establishes — and what it does not establish

            The experiments establish that the reviewed implementation satisfies its stated
            sorting contract for every sequence in the tiny exhaustive domain, all named
            boundary cases, and the deterministic generated cases used here. The loop trace
            is consistent with the sorted-prefix invariant. Independent reference checks,
            metamorphic relations, and the ability to expose and minimize an injected defect
            make the evidence more credible than a single example or a green execution log.

            The central limitation is scope. These results do **not** prove the Python
            interpreter, reference implementations, hardware,
            or notebook runner correct. They do not establish correctness for unbounded
            inputs, non-integer types, concurrent mutation, or resource exhaustion. Nor do
            the timing observations predict another machine or make insertion sort a good
            large-input choice. A mathematical proof and empirical testing answer different
            questions; good engineering uses both while naming their assumptions.

            NB-002 and NB-004 remain planned and unimplemented. This notebook is the complete
            R1 boundary for the current assignment.
            """
        ),
    ]

    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
            "mydatalabnotes": {
                "notebook_id": "NB-001",
                "schema": "mydatalabnotes.notebook.v1",
                "profile": "quick",
            },
        },
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, destination)
    print(f"built {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
