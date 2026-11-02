"""Independent Python contracts for the C17 representation and memory laboratory."""

from __future__ import annotations

import json
import os
import struct
import subprocess
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

PACKET_MAGIC = b"MDLN"
PACKET_VERSION = 1
PACKET_HEADER = struct.Struct(">4sBBIiHH")
MAX_PAYLOAD = 32
MAX_LAB_BYTES = 256


def encode_packet(
    record_id: int,
    measurement_milli: int,
    sample_count: int,
    flags: int,
    payload: bytes,
) -> bytes:
    """Encode one packet with explicit widths and network byte order."""
    ranges = {
        "record_id": (record_id, 0, 2**32 - 1),
        "measurement_milli": (measurement_milli, -(2**31), 2**31 - 1),
        "sample_count": (sample_count, 0, 2**16 - 1),
        "flags": (flags, 0, 2**8 - 1),
    }
    for name, (value, minimum, maximum) in ranges.items():
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"{name} is outside its declared integer range")
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= MAX_PAYLOAD:
        raise ValueError(f"payload must contain 1 to {MAX_PAYLOAD} bytes")
    return (
        PACKET_HEADER.pack(
            PACKET_MAGIC,
            PACKET_VERSION,
            flags,
            record_id,
            measurement_milli,
            sample_count,
            len(payload),
        )
        + payload
    )


def decode_packet(encoded: bytes) -> dict[str, int | bytes]:
    """Decode and validate the portable packet contract."""
    if len(encoded) < PACKET_HEADER.size:
        raise ValueError("packet is shorter than its fixed header")
    magic, version, flags, record_id, measurement, count, payload_length = (
        PACKET_HEADER.unpack_from(encoded)
    )
    if magic != PACKET_MAGIC or version != PACKET_VERSION:
        raise ValueError("packet magic or version is unsupported")
    if not 1 <= payload_length <= MAX_PAYLOAD:
        raise ValueError("packet payload length is outside the declared range")
    if len(encoded) != PACKET_HEADER.size + payload_length:
        raise ValueError("packet payload length is inconsistent")
    return {
        "record_id": record_id,
        "measurement_milli": measurement,
        "sample_count": count,
        "flags": flags,
        "payload": encoded[PACKET_HEADER.size :],
    }


def native_executable(root: Path) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    executable = root / "build" / "native" / f"memory_lab{suffix}"
    if not executable.is_file():
        raise FileNotFoundError("build the C17 laboratory with tools/build_native.py")
    return executable


def run_native(root: Path, arguments: list[str]) -> str:
    """Run the checked-in laboratory without a shell or source-string compilation."""
    result = subprocess.run(
        [str(native_executable(root)), *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
        timeout=15,
    )
    return result.stdout


def native_layout(root: Path) -> dict[str, Any]:
    return json.loads(run_native(root, ["layout"]))


def native_packet(root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    arguments = [
        "packet",
        str(packet["record_id"]),
        str(packet["measurement_milli"]),
        str(packet["sample_count"]),
        str(packet["flags"]),
        bytes(packet["payload"]).hex(),
    ]
    return json.loads(run_native(root, arguments))


def native_trace(
    root: Path,
    allocation_id: int,
    capacity: int,
    checkpoint_interval: int,
    operations: Iterable[str],
) -> list[dict[str, Any]]:
    if not 1 <= capacity <= MAX_LAB_BYTES:
        raise ValueError(f"capacity must be between 1 and {MAX_LAB_BYTES}")
    arguments = [
        "trace",
        str(allocation_id),
        str(capacity),
        str(checkpoint_interval),
        *list(operations),
    ]
    return [json.loads(line) for line in run_native(root, arguments).splitlines()]


def fnv1a64(data: bytes) -> str:
    value = 0xCBF29CE484222325
    for byte in data:
        value ^= byte
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{value:016x}"


def _segment(event: dict[str, Any], field: str) -> bytes:
    return bytes.fromhex(event[field])


def reconstruct_forward(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replay recorded evidence without using reference snapshots as input."""
    state: bytearray | None = None
    trusted = True
    expected_sequence = 1
    diagnostics: list[dict[str, Any]] = []
    for event in events:
        notes: list[str] = []
        sequence = int(event["seq"])
        if sequence != expected_sequence:
            notes.append(f"sequence gap: expected {expected_sequence}")
            trusted = False
        operation = event["operation"]
        before = _segment(event, "before_hex")
        after = _segment(event, "after_hex")
        offset = int(event["offset"])
        if operation == "allocate":
            if state is not None:
                notes.append("allocation began while state was live")
                trusted = False
            state = bytearray(after)
        elif operation == "release":
            if state is None or bytes(state) != before:
                notes.append("release evidence does not match current state")
                trusted = False
            state = None
        elif operation != "snapshot":
            if state is None or offset + len(before) > len(state):
                notes.append("mutation has no valid live target")
                trusted = False
            else:
                if bytes(state[offset : offset + len(before)]) != before:
                    notes.append("before bytes do not match current state")
                    trusted = False
                state[offset : offset + len(before)] = after

        checkpoint = _segment(event, "checkpoint_hex")
        status = "ok" if trusted and not notes else "unverified"
        if checkpoint and (state is None or bytes(state) != checkpoint or not trusted):
            state = bytearray(checkpoint)
            trusted = True
            status = "checkpoint-recovered"
            notes.append("state restored from recorded checkpoint")

        observed = b"" if state is None else bytes(state)
        fingerprint_matches = fnv1a64(observed) == event["state_fingerprint"]
        reference_matches = observed.hex() == event["reference_state_hex"]
        if trusted and not fingerprint_matches:
            status = "corruption-detected"
            notes.append("state fingerprint mismatch")
            trusted = False
        if trusted and not reference_matches:
            status = "reference-mismatch"
            notes.append("reconstruction differs from instrumented reference")
            trusted = False
        diagnostics.append(
            {
                "seq": sequence,
                "operation": operation,
                "status": status,
                "trusted": trusted,
                "state_hex": observed.hex(),
                "reference_matches": reference_matches,
                "fingerprint_matches": fingerprint_matches,
                "notes": "; ".join(notes),
            }
        )
        expected_sequence = sequence + 1
    return diagnostics


def reconstruct_reverse(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Undo a complete history using the recorded before bytes."""
    state: bytearray | None = None
    diagnostics: list[dict[str, Any]] = []
    for index in range(len(events) - 1, -1, -1):
        event = events[index]
        operation = event["operation"]
        before = _segment(event, "before_hex")
        after = _segment(event, "after_hex")
        offset = int(event["offset"])
        notes: list[str] = []
        if operation == "release":
            if state is not None:
                notes.append("release reversal expected no live state")
            state = bytearray(before)
        elif operation == "allocate":
            if state is None or bytes(state) != after:
                notes.append("allocation evidence does not match reconstructed state")
            state = None
        elif operation != "snapshot":
            if state is None or offset + len(after) > len(state):
                notes.append("reverse mutation has no valid live target")
            else:
                if bytes(state[offset : offset + len(after)]) != after:
                    notes.append("after bytes do not match current reverse state")
                state[offset : offset + len(after)] = before
        expected = "" if index == 0 else events[index - 1]["reference_state_hex"]
        observed = "" if state is None else bytes(state).hex()
        diagnostics.append(
            {
                "seq": event["seq"],
                "operation": operation,
                "status": "ok" if not notes and observed == expected else "mismatch",
                "pre_state_hex": observed,
                "reference_matches": observed == expected,
                "notes": "; ".join(notes),
            }
        )
    return diagnostics


def omit_events(events: list[dict[str, Any]], sequences: set[int]) -> list[dict[str, Any]]:
    return [deepcopy(event) for event in events if int(event["seq"]) not in sequences]


def corrupt_after_byte(events: list[dict[str, Any]], sequence: int) -> list[dict[str, Any]]:
    corrupted = deepcopy(events)
    for event in corrupted:
        if int(event["seq"]) == sequence:
            value = bytearray.fromhex(event["after_hex"])
            if not value:
                raise ValueError("selected event has no after bytes to corrupt")
            value[0] ^= 0x01
            event["after_hex"] = value.hex()
            return corrupted
    raise ValueError("selected sequence does not exist")
