"""Transparent algorithms for the first correctness investigation.

These are intentionally small. The notebook displays their source before it
uses them, and the tests exercise the same functions independently.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence


def _integer_list(values: Sequence[int]) -> list[int]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("values must be a finite sequence of integers")
    if any(type(value) is not int for value in values):
        raise TypeError("every value must be an integer")
    return list(values)


def insertion_sort(values: Sequence[int]) -> list[int]:
    """Return a stable, nondecreasing copy of a finite integer sequence."""
    result = _integer_list(values)
    for outer in range(1, len(result)):
        key = result[outer]
        cursor = outer - 1
        while cursor >= 0 and result[cursor] > key:
            result[cursor + 1] = result[cursor]
            cursor -= 1
        result[cursor + 1] = key
    return result


def insertion_sort_trace(values: Sequence[int]) -> tuple[list[int], list[dict[str, object]]]:
    """Return the sorted values and one state record per outer-loop iteration."""
    result = _integer_list(values)
    trace: list[dict[str, object]] = []
    for outer in range(1, len(result)):
        key = result[outer]
        cursor = outer - 1
        comparisons = 0
        shifts = 0
        while cursor >= 0:
            comparisons += 1
            if result[cursor] <= key:
                break
            result[cursor + 1] = result[cursor]
            cursor -= 1
            shifts += 1
        result[cursor + 1] = key
        trace.append(
            {
                "outer": outer,
                "key": key,
                "comparisons": comparisons,
                "shifts": shifts,
                "state": tuple(result),
                "sorted_prefix": tuple(result[: outer + 1]),
            }
        )
    return result, trace


def buggy_insertion_sort(values: Sequence[int]) -> list[int]:
    """Deliberately defective variant: index zero is never shifted."""
    result = _integer_list(values)
    for outer in range(1, len(result)):
        key = result[outer]
        cursor = outer - 1
        while cursor > 0 and result[cursor] > key:
            result[cursor + 1] = result[cursor]
            cursor -= 1
        result[cursor + 1] = key
    return result


def binary_search_first(values: Sequence[int], target: int) -> int:
    """Return the first matching index in sorted values, or -1 when absent."""
    sequence = _integer_list(values)
    if type(target) is not int:
        raise TypeError("target must be an integer")
    if any(left > right for left, right in zip(sequence, sequence[1:], strict=False)):
        raise ValueError("binary_search_first requires nondecreasing input")

    low, high = 0, len(sequence)
    while low < high:
        middle = (low + high) // 2
        if sequence[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low if low < len(sequence) and sequence[low] == target else -1


def sorting_contract(values: Sequence[int], result: Sequence[int]) -> dict[str, bool]:
    """Evaluate the observable postconditions of the sorting contract."""
    source = _integer_list(values)
    candidate = _integer_list(result)
    nondecreasing = all(
        left <= right for left, right in zip(candidate, candidate[1:], strict=False)
    )
    same_multiset = Counter(source) == Counter(candidate)
    return {
        "nondecreasing": nondecreasing,
        "same_multiset": same_multiset,
        "same_length": len(source) == len(candidate),
        "all_postconditions": nondecreasing and same_multiset,
    }
