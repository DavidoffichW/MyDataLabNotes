from __future__ import annotations

from bisect import bisect_left

import pytest

from mydatalabnotes.algorithms import (
    binary_search_first,
    buggy_insertion_sort,
    insertion_sort,
    insertion_sort_trace,
    sorting_contract,
)
from mydatalabnotes.evidence import exhaustive_integer_sequences


@pytest.mark.parametrize(
    "values",
    [[], [4], [2, 2, 1], [-3, 0, -3], [1, 2, 3], [3, 2, 1]],
)
def test_insertion_sort_boundary_cases(values: list[int]) -> None:
    result = insertion_sort(values)
    assert result == sorted(values)
    assert sorting_contract(values, result)["all_postconditions"]
    assert values != result or values == sorted(values)


def test_insertion_sort_matches_reference_for_exhaustive_tiny_domain() -> None:
    cases = exhaustive_integer_sequences((-1, 0, 1), max_length=6)
    for values in cases:
        assert insertion_sort(values) == sorted(values)
    assert len(cases) == 1_093


def test_trace_ends_at_same_result_and_preserves_sorted_prefixes() -> None:
    result, trace = insertion_sort_trace([4, 1, 3, 1])
    assert result == [1, 1, 3, 4]
    assert tuple(result) == trace[-1]["state"]
    assert all(list(step["sorted_prefix"]) == sorted(step["sorted_prefix"]) for step in trace)


def test_deliberate_defect_has_a_small_counterexample() -> None:
    assert buggy_insertion_sort([1, 0]) == [1, 0]
    assert buggy_insertion_sort([1, 0]) != insertion_sort([1, 0])


@pytest.mark.parametrize(
    ("values", "target"),
    [([], 1), ([1], 1), ([1], 0), ([1, 1, 2], 1), ([-2, 0, 4], 3)],
)
def test_binary_search_first_matches_bisect_reference(values: list[int], target: int) -> None:
    index = bisect_left(values, target)
    expected = index if index < len(values) and values[index] == target else -1
    assert binary_search_first(values, target) == expected


def test_binary_search_rejects_a_broken_precondition() -> None:
    with pytest.raises(ValueError, match="nondecreasing"):
        binary_search_first([2, 1], 1)


@pytest.mark.parametrize("values", [[1.0], [True], "123", [1, None]])
def test_algorithms_reject_values_outside_the_integer_sequence_contract(values: object) -> None:
    with pytest.raises(TypeError):
        insertion_sort(values)  # type: ignore[arg-type]
