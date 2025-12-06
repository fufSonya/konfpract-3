from __future__ import annotations

"""Interpreter helpers for the training VM."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import xml.etree.ElementTree as ET

from .spec import (
    INSTRUCTION_BYTES,
    MachineInstruction,
    WORD_MASK,
    decode_word,
)


class Memory:
    """Sparse memory model shared by the interpreter."""

    def __init__(self) -> None:
        self._cells: Dict[int, int] = {}

    def read(self, address: int) -> int:
        if address < 0:
            raise ValueError("Address must be non-negative")
        return self._cells.get(address, 0)

    def write(self, address: int, value: int) -> None:
        if address < 0:
            raise ValueError("Address must be non-negative")
        self._cells[address] = value & WORD_MASK

    def dump(self, start: int, end: int) -> List[Tuple[int, int]]:
        if start < 0 or end < 0 or end < start:
            raise ValueError("Invalid dump range")
        return [(addr, self.read(addr)) for addr in range(start, end + 1)]


@dataclass
class ExecutionResult:
    steps: int
    halted: bool


class Interpreter:
    def __init__(self, program: List[MachineInstruction], memory: Optional[Memory] = None):
        self.program = program
        self.memory = memory or Memory()
        self.pc = 0
        self.steps = 0

    def run(self, max_steps: Optional[int] = None) -> ExecutionResult:
        while self.pc < len(self.program):
            if max_steps is not None and self.steps >= max_steps:
                return ExecutionResult(steps=self.steps, halted=False)
            self._execute(self.program[self.pc])
            self.pc += 1
            self.steps += 1
        return ExecutionResult(steps=self.steps, halted=True)

    def _execute(self, instruction: MachineInstruction) -> None:
        name = instruction.definition.mnemonic
        fields = instruction.fields
        if name == "LOAD_CONST":
            self._op_load_const(fields)
        elif name == "READ_MEM":
            self._op_read_mem(fields)
        elif name == "WRITE_MEM":
            self._op_write_mem(fields)
        elif name == "NOT_MEM":
            self._op_not_mem(fields)
        else:
            raise ValueError(f"Unsupported instruction: {name}")

    def _op_load_const(self, fields: Dict[str, int]) -> None:
        constant = fields["B"]
        destination = fields["C"]
        self.memory.write(destination, constant)

    def _op_read_mem(self, fields: Dict[str, int]) -> None:
        pointer_address = fields["B"]
        offset = fields["C"]
        target_address = fields["D"]
        base = self.memory.read(pointer_address)
        value = self.memory.read(base + offset)
        self.memory.write(target_address, value)

    def _op_write_mem(self, fields: Dict[str, int]) -> None:
        source_address = fields["B"]
        destination_address = fields["C"]
        value = self.memory.read(source_address)
        self.memory.write(destination_address, value)

    def _op_not_mem(self, fields: Dict[str, int]) -> None:
        pointer_address = fields["B"]
        offset = fields["C"]
        target_address = fields["D"]
        base = self.memory.read(pointer_address)
        value = self.memory.read(base + offset)
        self.memory.write(target_address, (~value) & WORD_MASK)


def load_program(path: Path) -> List[MachineInstruction]:
    data = path.read_bytes()
    if len(data) % INSTRUCTION_BYTES != 0:
        raise ValueError("Binary file size must be a multiple of 14 bytes")
    program: List[MachineInstruction] = []
    for idx in range(0, len(data), INSTRUCTION_BYTES):
        chunk = data[idx : idx + INSTRUCTION_BYTES]
        word = int.from_bytes(chunk, "little")
        program.append(decode_word(word))
    return program


def dump_memory_to_xml(memory: Memory, start: int, end: int, output: Path) -> None:
    dump = memory.dump(start, end)
    root = ET.Element("memory", attrib={"start": str(start), "end": str(end)})
    for address, value in dump:
        ET.SubElement(root, "cell", address=str(address), value=str(value))
    tree = ET.ElementTree(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="utf-8", xml_declaration=True)


def interpret(binary: Path, dump_path: Path, start: int, end: int, max_steps: Optional[int] = None) -> ExecutionResult:
    program = load_program(binary)
    interpreter = Interpreter(program)
    result = interpreter.run(max_steps=max_steps)
    dump_memory_to_xml(interpreter.memory, start, end, dump_path)
    return result
