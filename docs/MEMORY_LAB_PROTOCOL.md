# Memory laboratory protocol

The native laboratory is a small C17 executable used by *The Same Value,
Different Bytes*. It observes one host-specific structure, encodes one portable
packet, and runs bounded memory operations. Python starts the checked-in
executable with an argument list and reads JSON Lines from standard output.
No source text is compiled from notebook input.

## Portable packet

Version 1 is independent of C structure padding and host byte order:

| Offset | Width | Field | Encoding |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `MDLN` |
| 4 | 1 | version | unsigned, value 1 |
| 5 | 1 | flags | unsigned 8-bit |
| 6 | 4 | record ID | unsigned 32-bit, big-endian |
| 10 | 4 | measurement | signed 32-bit, big-endian, milli-units |
| 14 | 2 | sample count | unsigned 16-bit, big-endian |
| 16 | 2 | payload length | unsigned 16-bit, big-endian |
| 18 | 1–32 | payload | opaque bytes |

The decoder rejects the wrong magic or version, truncated or trailing bytes,
and payload lengths outside the contract. C and Python implement the encoding
independently and share only the documented format and test vectors.

## Memory events

One run owns at most one live allocation of at most 256 bytes and accepts at
most 64 requested operations. Each event contains:

- the schema version, monotonic sequence number, and logical allocation ID;
- operation, destination offset and length, and source offset for a copy;
- the destination bytes before and after the operation;
- an optional full checkpoint;
- a full reference snapshot used only to evaluate reconstruction;
- live/released state and an FNV-1a state fingerprint.

Raw addresses are never event identities. `write` and `modify` copy bounded
input bytes. `copy` uses `memmove` after checking both ranges. `snapshot` reads
only live storage. `release` records the live bytes before clearing the owned
buffer, calling `free`, and marking the allocation unavailable; no later event
dereferences it.

Checkpoints are recorded after allocation, at the chosen periodic interval,
and for explicit snapshots. A checkpoint may re-establish a trusted state after
a detected gap, but it cannot reconstruct missing intermediate states. The
reference snapshots are experimental oracles: replay does not consume them as
authority.

## Commands

The build helper writes binaries under ignored `build/native/`:

```powershell
uv run python tools/build_native.py
build\native\memory_lab.exe layout
build\native\memory_lab.exe packet 16909060 -2 4386 165 deadbeef
build\native\memory_lab.exe trace 7 16 3 write:0:01020304 modify:1:aabb snapshot release
```

On Unix-like systems, omit the `.exe` suffix. Malformed operations, out-of-range
fields, and invalid memory ranges return a non-zero status rather than changing
the contract to accommodate the input.
