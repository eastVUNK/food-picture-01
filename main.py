#!/usr/bin/env python3
"""Put the food-picture-01 entry image in place as /output/entry.png.

This program publishes the ramen picture that ships beside it: it reads
food.jpg, checks that the file is exactly the picture the competition
asks for, and then installs it as entry.png inside /output (or inside
whatever directory MAKEFUN_OUTPUT_DIR names). The checks run first — the
picture has to be a real JPEG, measure 1024 by 1024 pixels, stay within
one mebibyte, and carry its end-of-image marker, so a damaged or wrong
file stops the run instead of being submitted. Publishing itself is done
carefully: the bytes go into a scratch file in the same folder, are
flushed all the way to disk, and are then moved over the destination in
a single atomic step, which means an interrupted run can never leave a
half-written entry.png behind. Once the move is done, the program reads
the published file back and makes sure it is identical to the bundled
picture. Any problem is reported on stderr and the program exits with
status 1. It only uses the Python standard library, never touches the
network, and produces the same output on every run.
"""

import os
import struct
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent
IMAGE_FILE = HERE / "food.jpg"
OUTPUT_FILE = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")) / "entry.png"
MAX_IMAGE_SIZE = 1_048_576
EXPECTED_WIDTH, EXPECTED_HEIGHT = 1024, 1024


def jpeg_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """Find a JPEG's pixel size by stepping through its markers until the SOF segment."""
    if image_bytes[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG (missing SOI marker)")
    cursor = 2
    while cursor + 4 <= len(image_bytes):
        if image_bytes[cursor] != 0xFF:
            raise ValueError("corrupt JPEG marker stream")
        tag = image_bytes[cursor + 1]
        if tag == 0xD9:  # end of image with no SOF segment seen
            break
        if tag in (0xD8,) or 0xD0 <= tag <= 0xD7:
            cursor += 2
            continue
        segment_length = struct.unpack(">H", image_bytes[cursor + 2:cursor + 4])[0]
        if tag in (0xC0, 0xC1, 0xC2):  # SOF0/1/2 store precision, height, then width
            height, width = struct.unpack(">HH", image_bytes[cursor + 5:cursor + 9])
            return width, height
        cursor += 2 + segment_length
    raise ValueError("no SOF marker found in JPEG")


def abort(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def verify_output(image_bytes: bytes) -> None:
    """Read the published entry back and confirm it is the bundled picture, byte for byte."""
    try:
        saved_bytes = OUTPUT_FILE.read_bytes()
    except OSError as e:
        abort(f"cannot read back {OUTPUT_FILE}: {e}")
    if saved_bytes != image_bytes:
        abort("output differs from bundled image after write")
    if len(saved_bytes) > MAX_IMAGE_SIZE:
        abort("output exceeds the 1 MiB limit")


def main() -> None:
    try:
        image_bytes = IMAGE_FILE.read_bytes()
    except OSError as e:
        abort(f"cannot read bundled image {IMAGE_FILE}: {e}")
    if len(image_bytes) > MAX_IMAGE_SIZE:
        abort(f"bundled image is {len(image_bytes)} bytes, over the 1 MiB limit")
    try:
        width, height = jpeg_dimensions(image_bytes)
    except ValueError as e:
        abort(f"bundled image is not a valid JPEG: {e}")
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        abort(f"bundled image is {width}x{height}, expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}")
    if not image_bytes.endswith(b"\xff\xd9"):
        abort("bundled image is truncated (missing JPEG EOI marker)")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=".entry-", dir=OUTPUT_FILE.parent)
    try:
        with os.fdopen(handle, "wb") as f:
            f.write(image_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, OUTPUT_FILE)
    except OSError as e:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        abort(f"cannot write {OUTPUT_FILE}: {e}")

    verify_output(image_bytes)


if __name__ == "__main__":
    main()
