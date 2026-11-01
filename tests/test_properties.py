from __future__ import annotations

from bisect import bisect_left

from hypothesis import given, settings
from hypothesis import strategies as st

from mydatalabnotes.algorithms import binary_search_first, insertion_sort, sorting_contract

INT_LISTS = st.lists(st.integers(min_value=-1_000, max_value=1_000), max_size=80)


@settings(max_examples=300, derandomize=True, database=None)
@given(INT_LISTS)
def test_sorting_contract_and_reference_agree(values: list[int]) -> None:
    result = insertion_sort(values)
    assert result == sorted(values)
    assert sorting_contract(values, result)["all_postconditions"]


@settings(max_examples=200, derandomize=True, database=None)
@given(INT_LISTS, st.integers(min_value=-100, max_value=100))
def test_sort_translation_metamorphism(values: list[int], offset: int) -> None:
    translated = [value + offset for value in values]
    assert insertion_sort(translated) == [value + offset for value in insertion_sort(values)]


@settings(max_examples=300, derandomize=True, database=None)
@given(INT_LISTS, st.integers(min_value=-1_000, max_value=1_000))
def test_binary_search_matches_independent_bisect_oracle(
    values: list[int], target: int
) -> None:
    ordered = sorted(values)
    reference = bisect_left(ordered, target)
    expected = reference if reference < len(ordered) and ordered[reference] == target else -1
    assert binary_search_first(ordered, target) == expected
