from __future__ import annotations

"""Assembler CLI helpers for the training VM."""

import csv
import io
from pathlib import Path
from typing import Iterable, List

from .spec import INSTRUCTION_BYTES, InstructionIR, INSTRUCTION_SET, encode_words

COMMENT_PREFIX = "#"
HEADER_CANDIDATES = {"OPCODE", "MNEMONIC"}
FIELD_SKIP = HEADER_CANDIDATES | {"", None}


def _read_clean_lines(path: Path) -> List[str]:
    raw = path.read_text(encoding="utf-8").splitlines()
    cleaned: List[str] = []
    for line in raw:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(COMMENT_PREFIX):
            continue
        cleaned.append(line)
    return cleaned


def parse_source(path: Path) -> List[InstructionIR]:
    """Parse CSV source into a list of IR instructions."""

    lines = _read_clean_lines(path)
    if not lines:
        return []
    buffer = io.StringIO("\n".join(lines))
    reader = csv.DictReader(buffer)
    if not reader.fieldnames:
        raise ValueError("CSV file must contain a header row")

    fieldnames = [name.strip().upper() if name else "" for name in reader.fieldnames]
    if not any(name in HEADER_CANDIDATES for name in fieldnames):
        raise ValueError("Header must contain an 'opcode' column")

    instructions: List[InstructionIR] = []
    for row in reader:
        if not row:
            continue
        mnemonic_raw = None
        fields = {}
        for original_key, value in row.items():
            key = (original_key or "").strip().upper()
            if key in HEADER_CANDIDATES:
                mnemonic_raw = (value or "").strip()
                continue
            if key in FIELD_SKIP:
                continue
            if value is None:
                continue
            value_str = value.strip()
            if not value_str:
                continue
            try:
                parsed_value = int(value_str, 0)
            except ValueError as exc:
                raise ValueError(
                    f"Failed to parse integer for field '{key}': {value_str}"
                ) from exc
            fields[key] = parsed_value
        if mnemonic_raw is None:
            raise ValueError("Each row must include an opcode column")
        mnemonic = mnemonic_raw.upper()
        if mnemonic not in INSTRUCTION_SET:
            raise ValueError(f"Unknown mnemonic '{mnemonic}' on row {reader.line_num}")
        instructions.append(InstructionIR(mnemonic=mnemonic, fields=fields))
    return instructions


def format_ir_dump(ir_list: Iterable[InstructionIR]) -> str:
    """Render IR instructions similarly to the specification test tables."""

    lines: List[str] = []
    for idx, ir in enumerate(ir_list):
        definition = INSTRUCTION_SET[ir.mnemonic]
        parts = [f"A={definition.opcode}"]
        for field in definition.fields:
            value = ir.fields.get(field.name)
            parts.append(f"{field.name}={value if value is not None else 'NA'}")
        lines.append(f"Instruction {idx}: " + ", ".join(parts))
    return "\n".join(lines)


def format_byte_dump(blob: bytes, columns: int = 8) -> str:
    chunks = [f"0x{byte:02X}" for byte in blob]
    lines = [
        " ".join(chunks[i : i + columns]) for i in range(0, len(chunks), columns)
    ]
    return "\n".join(lines)


def assemble_to_file(source: Path, output: Path, test_mode: bool = False) -> bytes:
    """Assemble the provided CSV source file and persist the binary output."""

    instructions = parse_source(source)
    if test_mode:
        print(format_ir_dump(instructions))
    words = encode_words(instructions)
    blob = b"".join(word.to_bytes(INSTRUCTION_BYTES, "little") for word in words)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(blob)
    print(f"Assembled instructions: {len(words)}")
    if test_mode and blob:
        print("Byte dump:")
        print(format_byte_dump(blob))
    return blob
