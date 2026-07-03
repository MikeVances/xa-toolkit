"""XA disassembler — clean-room from the Philips XA User Guide, Chapter 6.

`decode(mem, pc)` returns `(size, mnemonic, operands)` for one instruction.

Status (alpha): the fully-regular **basic-ALU group** (ADD/ADDC/SUB/SUBB/CMP/
AND/OR/XOR/MOV) is decoded structurally. Only ALU op nibbles verified against
the datasheet are named (ADD); unverified ops render as "alu<n>" so nothing is
fabricated. Remaining instruction groups (shifts, MOVx, branches, bit ops,
FCALL/FJMP/CALL/JMP, …) are decoded from their Ch.6 pages next.

Byte order: instructions are big-endian byte streams; multi-byte immediates and
offsets are stored high-byte-first (Ch.6). Data in memory is little-endian.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

from .isa import (
    ALU_OPS, ALU_SUBMODES, BRANCH_CC, OP_BKPT, OP_FJMP, OP_JMP_REL16, OP_D6,
)

# NOTE: SZ (byte0 bit3) polarity — provisional (word if set). The ADD pages show
# the "SZ" field but not its 0/1->byte/word mapping; confirm from the Ch.6
# general encoding notes before treating the .b/.w suffix as authoritative.
def _size_suffix(sz_bit: int) -> str:
    return ".w" if sz_bit else ".b"


def _r(n: int) -> str:
    return f"R{n}"


def decode(mem: Sequence[int], pc: int = 0) -> Tuple[int, str, List[str]]:
    """Decode one instruction at `mem[pc]`. Returns (size, mnemonic, operands)."""
    b0 = mem[pc]
    hi = (b0 >> 4) & 0xF
    sz = (b0 >> 3) & 1
    sub = b0 & 0x7

    # -- basic-ALU immediate group: byte0 high nibble 0x9 --------------------
    if hi == 0x9:
        data16 = (b0 >> 3) & 1
        isub = b0 & 0x7
        b1 = mem[pc + 1]
        op = b1 & 0xF
        mnem = ALU_OPS.get(op, f"alu{op}")
        if data16:
            imm = (mem[pc + 2] << 8) | mem[pc + 3]
            size, immstr = 4, f"#0x{imm:04x}"
        else:
            imm = mem[pc + 2]
            size, immstr = 3, f"#0x{imm:02x}"
        if isub == 0b001:      # reg, #data   (byte1 = dddd 0000)
            d = (b1 >> 4) & 0xF
            return (size, mnem, [_r(d), immstr])
        if isub == 0b010:      # [reg], #data (byte1 = 0ddd 0000)
            d = (b1 >> 4) & 0x7
            return (size, mnem, [f"[{_r(d)}]", immstr])
        return (size, mnem, ["?", immstr])   # other immediate sub-modes: Ch.6 TODO

    # -- short branches / breakpoint: opcode block 0xFx (Ch.6) ---------------
    if hi == 0xF:
        if b0 == OP_BKPT:                      # 0xFF: BKPT, 1 byte, no operand
            return (1, "bkpt", [])
        mnem = BRANCH_CC.get(b0 & 0xF)
        if mnem is not None:                   # 0xF0..0xFE: byte1 = signed rel8
            rel8 = mem[pc + 1]
            if rel8 >= 0x80:
                rel8 -= 0x100
            target = (pc + 2 + rel8 * 2) & 0xFFFFFF   # word-aligned PC-relative
            return (2, mnem, [f"0x{target:x}"])

    # -- far/absolute + register-indirect flow (0xD4..0xD6, Ch.6) ------------
    if b0 == OP_FJMP:                          # 4 bytes: addr24
        addr = (mem[pc + 3] << 16) | (mem[pc + 1] << 8) | mem[pc + 2]
        return (4, "fjmp", [f"0x{addr:06x}"])
    if b0 == OP_JMP_REL16:                      # 3 bytes: signed rel16
        rel16 = (mem[pc + 1] << 8) | mem[pc + 2]
        if rel16 >= 0x8000:
            rel16 -= 0x10000
        return (3, "jmp", [f"0x{(pc + 3 + rel16 * 2) & 0xFFFFFF:x}"])
    if b0 == OP_D6:                             # multiplexed by byte1
        b1 = mem[pc + 1]
        if b1 == 0x80:
            return (2, "ret", [])
        if b1 == 0x90:
            return (2, "reti", [])
        if (b1 & 0xF8) == 0x70:                 # 0b01110sss
            return (2, "jmp", [f"[{_r(b1 & 0x7)}]"])
        # other 0xD6 forms (JMP [A+DPTR], [[Rs+]], CALL [Rs], ...) not yet decoded

    # -- basic-ALU register/memory group: byte0 = OOOO S mmm ------------------
    # (ADD..MOV = nibbles 0x0..0x8; sub-mode in the low 3 bits selects 1..6).
    # NOTE: other instruction groups may also use hi-nibbles 0..8 — refine this
    # dispatch as their opcodes are added; for now ALU is decoded best-effort.
    if hi in ALU_OPS:
        info = ALU_SUBMODES.get(sub)
        if info is not None:
            name, size = info
            mnem = ALU_OPS.get(hi, f"alu{hi}") + _size_suffix(sz)
            b1 = mem[pc + 1]
            if name == "reg":                      # Rd, Rs
                d = (b1 >> 4) & 0xF
                s = b1 & 0xF
                return (2, mnem, [_r(d), _r(s)])
            direction = (b1 >> 3) & 1              # 0: reg,mem   1: mem,reg
            reg = _r((b1 >> 4) & 0xF)
            ptr = b1 & 0x7
            if name == "ind":
                mem_op, size = f"[{_r(ptr)}]", 2
            elif name == "ind_inc":
                mem_op, size = f"[{_r(ptr)}+]", 2
            elif name == "off8":
                mem_op, size = f"[{_r(ptr)}+0x{mem[pc + 2]:02x}]", 3
            elif name == "off16":
                off = (mem[pc + 2] << 8) | mem[pc + 3]
                mem_op, size = f"[{_r(ptr)}+0x{off:04x}]", 4
            else:  # direct: 11-bit address = 3 bits (byte1 low) + byte2
                direct = (ptr << 8) | mem[pc + 2]
                mem_op, size = f"0x{direct:03x}", 3
            operands = [reg, mem_op] if direction == 0 else [mem_op, reg]
            return (size, mnem, operands)

    # Unknown / not-yet-decoded opcode. Report length 1 and raw byte; never guess.
    return (1, "?", [f"0x{b0:02x}"])
