from __future__ import annotations

import argparse
from pathlib import Path

from uvm.assembler import assemble_to_file


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Training VM assembler")
    parser.add_argument("--input", required=True, type=_path, help="Path to CSV source")
    parser.add_argument("--output", required=True, type=_path, help="Path to emit binary program")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Enable verbose mode with IR and byte dumps",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    assemble_to_file(args.input, args.output, test_mode=args.test)


if __name__ == "__main__":
    main()