#!/usr/bin/env python3
"""food-picture-01 entry: write the best-looking food picture to /output/entry.png.

Copies the bundled image (food.jpg) to /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png). Deterministic: no network, no randomness,
no clock. Python 3.13, stdlib only.
"""

import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "food.jpg"
DST = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")) / "entry.png"


def main() -> None:
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, DST)


if __name__ == "__main__":
    main()
