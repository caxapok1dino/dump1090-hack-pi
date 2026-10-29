#!/usr/bin/env python3
"""Save HackRF CS8 IQ in bounded segments while forwarding the live stream."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path


SAMPLE_RATE = 8_000_000
BYTES_PER_SAMPLE = 2  # Interleaved signed 8-bit I and Q.
CHUNK_BYTES = 256 * 1024
RECORDINGS = Path(os.environ.get("RECORDINGS_DIR", "/recordings"))


def positive_int(name, default, *, allow_zero=False):
    value = int(os.environ.get(name, default))
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"{name} must be {'nonnegative' if allow_zero else 'positive'}")
    return value


def write_all(fd, data):
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written == 0:
            raise OSError("stream write returned zero bytes")
        view = view[written:]


def prune(max_recordings):
    if max_recordings == 0:
        return
    files = sorted(RECORDINGS.glob("hackrf-*.cs8"))
    for path in files[: max(0, len(files) - max_recordings + 1)]:
        path.unlink()


def main():
    seconds = positive_int("RECORD_SEGMENT_SECONDS", "60")
    max_recordings = positive_int("MAX_RECORDINGS", "10", allow_zero=True)
    segment_bytes = seconds * SAMPLE_RATE * BYTES_PER_SAMPLE
    RECORDINGS.mkdir(parents=True, exist_ok=True)
    capture_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    segment_index = 0
    current = None
    remaining = 0

    try:
        while data := os.read(sys.stdin.fileno(), CHUNK_BYTES):
            offset = 0
            while offset < len(data):
                if current is None:
                    segment_index += 1
                    path = RECORDINGS / f"hackrf-{capture_id}-{segment_index:06d}.cs8"
                    prune(max_recordings)
                    current = path.open("xb", buffering=0)
                    remaining = segment_bytes
                    print(f"Recording {path}", file=sys.stderr, flush=True)

                count = min(remaining, len(data) - offset)
                chunk = data[offset : offset + count]
                write_all(current.fileno(), chunk)
                write_all(sys.stdout.fileno(), chunk)
                offset += count
                remaining -= count

                if remaining == 0:
                    current.close()
                    current = None
    finally:
        if current is not None:
            current.close()


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
