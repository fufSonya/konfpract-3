from __future__ import annotations

"""Instruction set and core data models for the training VM."""

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

INSTRUCTION_BITS = 112
INSTRUCTION_BYTES = 14
OPCODE_BITS = 5
WORD_SIZE = 64
WORD_MASK = (1 << WORD_SIZE) - 1


@dataclass(frozen=True)
class FieldDefinition:
    """Bit layout definition for an instruction field."""

    name: str
    start_bit: int
    end_bit: int

    @property
    def width(self) -> int:
        return self.end_bit - self.start_bit + 1

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1


@dataclass(frozen=True)
class InstructionDefinition:
    """Metadata about a single VM instruction."""

    mnemonic: str
    opcode: int
    fields: tuple[FieldDefinition, ...]

    def validate_fields(self, values: Mapping[str, int]) -> None:
        required = {field.name for field in self.fields}
        missing = required - {name.upper() for name in values}
        if missing:
            raise ValueError(
                f"Instruction '{self.mnemonic}' requires fields: {sorted(missing)}"
            )
        for name in values:
            upper = name.upper()
            if upper not in required:
                raise ValueError(
                    f"Field '{name}' is not valid for instruction '{self.mnemonic}'"
                )

    def encode(self, values: Mapping[str, int]) -> int:
        """Encode field values into a 112-bit instruction word."""

        self.validate_fields(values)
        encoded = self.opcode & ((1 << OPCODE_BITS) - 1)
        for field in self.fields:
            raw_value = int(values[field.name.upper()])
            if raw_value < 0 or raw_value > field.mask:
                raise ValueError(
                    f"Field '{field.name}'={raw_value} does not fit into {field.width} bits"
                )
            encoded |= raw_value << field.start_bit
        return encoded

    def extract_fields(self, encoded: int) -> Dict[str, int]:
        """Extract field values from a raw instruction word."""

        result: Dict[str, int] = {}
        for field in self.fields:
            value = (encoded >> field.start_bit) & field.mask
            result[field.name] = value
        return result


@dataclass
class InstructionIR:
    """Intermediate representation produced by the assembler parser."""

    mnemonic: str
    fields: Dict[str, int]


@dataclass
class MachineInstruction:
    """Decoded instruction ready for execution."""

    definition: InstructionDefinition
    fields: Dict[str, int]
    raw_value: int


FIELD_B_SHORT = FieldDefinition("B", 5, 21)  # 17 bits
FIELD_C_LONG = FieldDefinition("C", 22, 50)  # 29 bits
FIELD_B_LONG = FieldDefinition("B", 5, 33)   # 29 bits
FIELD_C_SHORT = FieldDefinition("C", 34, 48)  # 15 bits
FIELD_D_LONG = FieldDefinition("D", 49, 77)   # 29 bits
FIELD_C_MEDIUM = FieldDefinition("C", 34, 62)  # 29 bits


INSTRUCTION_SET: Dict[str, InstructionDefinition] = {
    "LOAD_CONST": InstructionDefinition(
        mnemonic="LOAD_CONST",
        opcode=17,
        fields=(FIELD_B_SHORT, FIELD_C_LONG),
    ),
    "READ_MEM": InstructionDefinition(
        mnemonic="READ_MEM",
        opcode=16,
        fields=(FIELD_B_LONG, FIELD_C_SHORT, FIELD_D_LONG),
    ),
    "WRITE_MEM": InstructionDefinition(
        mnemonic="WRITE_MEM",
        opcode=23,
        fields=(FIELD_B_LONG, FIELD_C_MEDIUM),
    ),
    "NOT_MEM": InstructionDefinition(
        mnemonic="NOT_MEM",
        opcode=24,
        fields=(FIELD_B_LONG, FIELD_C_SHORT, FIELD_D_LONG),
    ),
}

INSTRUCTION_BY_OPCODE: Dict[int, InstructionDefinition] = {
    definition.opcode: definition for definition in INSTRUCTION_SET.values()
}


def decode_word(word: int) -> MachineInstruction:
    """Turn a raw 112-bit word into a machine instruction."""

    opcode = word & ((1 << OPCODE_BITS) - 1)
    definition = INSTRUCTION_BY_OPCODE.get(opcode)
    if definition is None:
        raise ValueError(f"Unknown opcode: {opcode}")
    fields = definition.extract_fields(word)
    return MachineInstruction(definition=definition, fields=fields, raw_value=word)


def encode_words(instructions: Iterable[InstructionIR]) -> list[int]:
    """Encode a sequence of IR instructions into machine words."""

    words: list[int] = []
    for ir in instructions:
        definition = INSTRUCTION_SET.get(ir.mnemonic.upper())
        if definition is None:
            raise ValueError(f"Unknown instruction mnemonic: {ir.mnemonic}")
        words.append(definition.encode(ir.fields))
    return words