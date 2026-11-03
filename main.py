"""Unified TetrisMind entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TetrisMind: play, watch AI, tune weights, or verify",
    )
    parser.add_argument(
        "--mode",
        choices=("play", "ai", "p4", "verify"),
        default="play",
        help="play=human UI, ai=AI demo, p4=GA experiment, verify=tests",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args, extra = build_parser().parse_known_args(argv)
    if args.mode == "play":
        from ui.__main__ import main as ui_main

        return ui_main(["--mode", "input", *extra])
    if args.mode == "ai":
        from ui.__main__ import main as ui_main

        return ui_main(["--mode", "render", *extra])
    if args.mode == "p4":
        from exp.demo import main as p4_main

        return p4_main(extra)

    import unittest

    tests = unittest.defaultTestLoader.discover(str(Path(__file__).parent / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
