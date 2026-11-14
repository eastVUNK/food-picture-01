#!/usr/bin/env python3
"""food-picture-01 entry: write the best-looking food picture to /output/entry.png.

Copies the bundled image (food.jpg) to /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png), then verifies the result before exiting: the
output must be byte-identical to the source, a valid JPEG of 1024x1024
pixels, and at most 1 MiB. The write goes through a temporary file in the
same directory followed by an atomic rename, so a partial or interrupted
write can never leave a broken entry.png behind. Any failed check exits
non-zero with a clear message on stderr.
Deterministic: no network, no randomness, no clock. Python 3.13, stdlib only.
"""

import os
import struct
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent
SRC = HERE / "food.jpg"
DST = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")) / "entry.png"
MAX_BYTES = 1_048_576
EXPECT_W, EXPECT_H = 1024, 1024


def jpeg_size(data: bytes) -> tuple[int, int]:
    """Return (width, height) of a JPEG by scanning for its SOF marker."""
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG (missing SOI marker)")
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise ValueError("corrupt JPEG marker stream")
        marker = data[pos + 1]
        if marker == 0xD9:  # EOI: no SOF found
            break
        if marker in (0xD8,) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        size = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):  # SOF0/1/2: precision, height, width
            h, w = struct.unpack(">HH", data[pos + 5:pos + 9])
            return w, h
        pos += 2 + size
    raise ValueError("no SOF marker found in JPEG")


def fail(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    try:
        data = SRC.read_bytes()
    except OSError as e:
        fail(f"cannot read bundled image {SRC}: {e}")
    if len(data) > MAX_BYTES:
        fail(f"bundled image is {len(data)} bytes, over the 1 MiB limit")
    try:
        w, h = jpeg_size(data)
    except ValueError as e:
        fail(f"bundled image is not a valid JPEG: {e}")
    if (w, h) != (EXPECT_W, EXPECT_H):
        fail(f"bundled image is {w}x{h}, expected {EXPECT_W}x{EXPECT_H}")
    if not data.endswith(b"\xff\xd9"):
        fail("bundled image is truncated (missing JPEG EOI marker)")

    DST.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".entry-", dir=DST.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, DST)
    except OSError as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        fail(f"cannot write {DST}: {e}")

    written = DST.read_bytes()
    if written != data:
        fail("output differs from bundled image after write")
    if len(written) > MAX_BYTES:
        fail("output exceeds the 1 MiB limit")


if __name__ == "__main__":
    main()
