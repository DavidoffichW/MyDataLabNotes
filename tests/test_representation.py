from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

import pytest

from mydatalabnotes.representation import (
    corrupt_after_byte,
    decode_packet,
    encode_packet,
    native_executable,
    native_packet,
    native_trace,
    omit_events,
    reconstruct_forward,
    reconstruct_reverse,
)

ROOT = Path(__file__).resolve().parents[1]


def test_python_packet_known_vector_and_round_trip() -> None:
    encoded = encode_packet(0x01020304, -2, 0x1122, 0xA5, bytes.fromhex("deadbeef"))
    assert encoded.hex() == "4d444c4e01a501020304fffffffe11220004deadbeef"
    assert decode_packet(encoded) == {
        "record_id": 0x01020304,
        "measurement_milli": -2,
        "sample_count": 0x1122,
        "flags": 0xA5,
        "payload": bytes.fromhex("deadbeef"),
    }


@pytest.mark.parametrize(
    "arguments",
    [(-1, 0, 0, 0, b"x"), (0, 2**31, 0, 0, b"x"), (0, 0, 0, 256, b"x")],
)
def test_packet_rejects_out_of_range_fields(arguments: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        encode_packet(*arguments)  # type: ignore[arg-type]


def test_packet_decoder_rejects_empty_and_inconsistent_payloads() -> None:
    empty = struct.pack(">4sBBIiHH", b"MDLN", 1, 0, 1, 2, 3, 0)
    with pytest.raises(ValueError, match="declared range"):
        decode_packet(empty)
    encoded = encode_packet(1, 2, 3, 4, b"x")
    with pytest.raises(ValueError, match="inconsistent"):
        decode_packet(encoded + b"trailing")


def test_native_and_python_packet_encoders_agree() -> None:
    packet = {
        "record_id": 0x01020304,
        "measurement_milli": -2,
        "sample_count": 0x1122,
        "flags": 0xA5,
        "payload": bytes.fromhex("deadbeef"),
    }
    expected = encode_packet(**packet).hex()
    assert native_packet(ROOT, packet)["portable_hex"] == expected


def test_complete_trace_reconstructs_forward_and_reverse() -> None:
    events = native_trace(
        ROOT,
        7,
        12,
        3,
        ["write:0:01020304", "modify:1:aabb", "copy:0:4:8", "snapshot", "release"],
    )
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
    assert all(row["reference_matches"] for row in reconstruct_forward(events))
    assert all(row["reference_matches"] for row in reconstruct_reverse(events))


def test_sequence_gap_is_detected_and_checkpoint_recovers_later_state() -> None:
    events = native_trace(
        ROOT,
        9,
        12,
        3,
        ["write:0:01020304", "modify:1:aabb", "copy:0:4:8", "snapshot", "release"],
    )
    diagnostics = reconstruct_forward(omit_events(events, {2}))
    assert any("sequence gap" in row["notes"] for row in diagnostics)
    assert any(row["status"] == "checkpoint-recovered" for row in diagnostics)
    assert diagnostics[-1]["reference_matches"]


def test_corrupted_event_is_detected_without_becoming_authority() -> None:
    events = native_trace(
        ROOT,
        11,
        8,
        0,
        ["write:0:01020304", "modify:1:aabb", "release"],
    )
    diagnostics = reconstruct_forward(corrupt_after_byte(events, 2))
    assert any(not row["fingerprint_matches"] for row in diagnostics)
    assert any(row["status"] in {"corruption-detected", "unverified"} for row in diagnostics)


def test_native_cli_rejects_an_out_of_bounds_operation() -> None:
    result = subprocess.run(
        [str(native_executable(ROOT)), "trace", "1", "8", "2", "write:8:ff"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode != 0
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert events[0]["operation"] == "allocate"
    assert events[-1]["operation"] == "release"
