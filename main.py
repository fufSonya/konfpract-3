from __future__ import annotations

"""CLI entry point for the training VM assembler and interpreter."""

import argparse
from pathlib import Path

from uvm.assembler import assemble_to_file
from uvm.interpreter import interpret


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Training VM toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    assemble_parser = subparsers.add_parser("assemble", help="Assemble CSV source")
    assemble_parser.add_argument("--input", required=True, type=_path, help="Path to CSV source")
    assemble_parser.add_argument(
        "--output", required=True, type=_path, help="Path to emit binary program"
    )
    assemble_parser.add_argument(
        "--test",
        action="store_true",
        help="Enable verbose mode with IR and byte dumps",
    )

    interpret_parser = subparsers.add_parser("interpret", help="Run binary program")
    interpret_parser.add_argument(
        "--binary", required=True, type=_path, help="Path to compiled program"
    )
    interpret_parser.add_argument(
        "--dump", required=True, type=_path, help="Path to store XML memory dump"
    )
    interpret_parser.add_argument(
        "--range",
        dest="dump_range",
        required=True,
        nargs=2,
        metavar=("START", "END"),
        type=int,
        help="Inclusive memory range to dump",
    )
    interpret_parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optional cap on executed instructions",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "assemble":
        assemble_to_file(args.input, args.output, test_mode=args.test)
    elif args.command == "interpret":
        start, end = args.dump_range
        result = interpret(args.binary, args.dump, start=start, end=end, max_steps=args.max_steps)
        status = "halted" if result.halted else "stopped (max steps reached)"
        print(f"Executed steps: {result.steps} -> {status}")
    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
