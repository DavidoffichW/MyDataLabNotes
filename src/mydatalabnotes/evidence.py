"""Evidence helpers shared by notebook execution and independent tests."""

from __future__ import annotations

import hashlib
import json
from itertools import product
from typing import Any


def exhaustive_integer_sequences(
    domain: tuple[int, ...], max_length: int
) -> list[tuple[int, ...]]:
    """Enumerate every sequence over a tiny declared domain."""
    if max_length < 0:
        raise ValueError("max_length must be non-negative")
    return [
        sequence
        for length in range(max_length + 1)
        for sequence in product(domain, repeat=length)
    ]


def canonical_json_sha256(value: Any) -> str:
    """Hash a JSON-compatible evidence object using a stated canonical form."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
