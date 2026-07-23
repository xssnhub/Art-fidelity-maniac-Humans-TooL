from __future__ import annotations

import argparse
from pathlib import Path

from quicksharp_baby.app import run


def main() -> None:
    parser = argparse.ArgumentParser(description="快晰寶貝｜QuickSharp Baby")
    parser.add_argument(
        "paths", nargs="*", type=Path,
        help="啟動時直接開啟的照片資料夾或影像檔",
    )
    args = parser.parse_args()
    run(args.paths)


if __name__ == "__main__":
    main()
