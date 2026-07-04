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
    SHIFT_REG, SHIFT_IMM4,
)

# NOTE: SZ (byte0 bit3) polarity — provisional (word if set). The ADD pages show
# the "SZ" field but not its 0/1->byte/word mapping; confirm from the Ch.6
# general encoding notes before treating the .b/.w suffix as authoritative.
def _size_suffix(sz_bit: int) -> str:
    return ".w" if sz_bit else ".b"


def _r(n: int) -> str:
    return f"R{n}"


def _rlist(bitmap: int, word: bool, high: bool) -> str:
    """Decode a PUSH/POP register-list bitmap (Ch.6 pp. 6-142). Bit i selects:
    word -> Ri ; byte -> R(base+i//2)L/H, base = 4 if high else 0."""
    regs = []
    for i in range(8):
        if bitmap & (1 << i):
            if word:
                regs.append(f"R{i}")
            else:
                regs.append(f"R{(4 if high else 0) + i // 2}{'L' if i % 2 == 0 else 'H'}")
    return "{" + ",".join(regs) + "}"


def decode(mem: Sequence[int], pc: int = 0) -> Tuple[int, str, List[str]]:
    """Decode one instruction at `mem[pc]`. Returns (size, mnemonic, operands)."""
    b0 = mem[pc]
    hi = (b0 >> 4) & 0xF
    sz = (b0 >> 3) & 1
    sub = b0 & 0x7

    # -- MOVC A,[A+DPTR] / A,[A+PC] — fixed 2-byte forms (6-121/6-122) --------
    # Must precede the 0x9x ALU-immediate group (shared high nibble 0x9).
    if b0 == 0x90 and mem[pc + 1] in (0x4E, 0x4C):
        return (2, "movc", ["A", "[A+DPTR]" if mem[pc + 1] == 0x4E else "[A+PC]"])

    # -- unary register ops: DA/SEXT/CPL/NEG (0x90/0x98; Ch.6) ---------------
    # byte0 = 1001 SZ 000; byte1 low nibble selects the op.
    if b0 in (0x90, 0x98):
        b1 = mem[pc + 1]
        op = {0x8: "da", 0x9: "sext", 0xA: "cpl", 0xB: "neg"}.get(b1 & 0x0F)
        if op is not None:
            return (2, op + (".w" if b0 == 0x98 else ".b"), [_r((b1 >> 4) & 0xF)])

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
        # other 0x9x sub-modes (offset/direct immediate, and non-ALU 0x90 forms)
        # not decoded yet — fall through to the generic "?" rather than guess.

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
        if (b1 & 0xF0) == 0x30:                 # TRAP #data4 (byte1 = 0011 dddd) (6-168)
            return (2, "trap", [f"#0x{b1 & 0xF:x}"])
        # other 0xD6 forms (JMP [A+DPTR], [[Rs+]], CALL [Rs], ...) not yet decoded

    # -- CJNE / DJNZ direct / JB-family / JZ / JNZ (Ch.6) --------------------
    if b0 in (0xEC, 0xEE):                       # JZ 0xEC (6-106) / JNZ 0xEE (6-105)
        r = mem[pc + 1] - 0x100 if mem[pc + 1] >= 0x80 else mem[pc + 1]
        return (2, "jz" if b0 == 0xEC else "jnz", [f"0x{(pc + 2 + r * 2) & 0xFFFFFF:x}"])
    if b0 == 0x97:                               # JB/JNB/JBC bit,rel8 (6-98/104/99)
        b1 = mem[pc + 1]
        mnem = {0x80: "jb", 0xA0: "jnb", 0xC0: "jbc"}.get(b1 & 0xE0)
        if mnem is not None:
            bit = ((b1 & 0x3) << 8) | mem[pc + 2]
            r = mem[pc + 3] - 0x100 if mem[pc + 3] >= 0x80 else mem[pc + 3]
            return (4, mnem, [f"0x{bit:03x}", f"0x{(pc + 4 + r * 2) & 0xFFFFFF:x}"])
    if b0 in (0xE2, 0xEA):                       # CJNE Rd,direct (6-77) / DJNZ direct (6-95)
        b1 = mem[pc + 1]
        sfx = ".w" if b0 == 0xEA else ".b"
        direct = ((b1 & 0x7) << 8) | mem[pc + 2]
        r = mem[pc + 3] - 0x100 if mem[pc + 3] >= 0x80 else mem[pc + 3]
        tgt = f"0x{(pc + 4 + r * 2) & 0xFFFFFF:x}"
        if (b1 & 0x08) == 0:                     # CJNE Rd,direct,rel8 (byte1 = dddd 0 DDD)
            return (4, "cjne" + sfx, [_r((b1 >> 4) & 0xF), f"0x{direct:03x}", tgt])
        return (4, "djnz" + sfx, [f"0x{direct:03x}", tgt])   # DJNZ direct (0000 1 DDD)
    if b0 in (0xE3, 0xEB):                       # CJNE Rd/[Rd],#dataN,rel8 (6-78)
        b1 = mem[pc + 1]
        sfx = ".w" if b0 == 0xEB else ".b"
        indirect = bool(b1 & 0x08)
        d = (b1 >> 4) & (0x7 if indirect else 0xF)
        dest = f"[{_r(d)}]" if indirect else _r(d)
        r = mem[pc + 2] - 0x100 if mem[pc + 2] >= 0x80 else mem[pc + 2]
        if b0 == 0xE3:                           # #data8
            imm, size = f"#0x{mem[pc + 3]:02x}", 4
        else:                                    # #data16
            imm, size = f"#0x{(mem[pc + 3] << 8) | mem[pc + 4]:04x}", 5
        return (size, "cjne" + sfx, [dest, imm, f"0x{(pc + size + r * 2) & 0xFFFFFF:x}"])

    # -- shift / rotate group (byte & word forms; Ch.6) ----------------------
    if b0 in SHIFT_REG:                        # ASL/ASR Rd,Rs
        mnem, sfx = SHIFT_REG[b0]
        b1 = mem[pc + 1]
        return (2, mnem + sfx, [_r((b1 >> 4) & 0xF), _r(b1 & 0xF)])
    if b0 in SHIFT_IMM4:                        # ASL/ASR/RL/RLC/RR/RRC Rd,#data4
        mnem, sfx = SHIFT_IMM4[b0]
        b1 = mem[pc + 1]
        return (2, mnem + sfx, [_r((b1 >> 4) & 0xF), f"#0x{b1 & 0xF:x}"])

    # -- data movement: MOVC [Rs+], MOVX, MOVS (Ch.6) ------------------------
    if b0 in (0x80, 0x88):                     # MOVC Rd,[Rs+]  (6-120)
        b1 = mem[pc + 1]
        sfx = ".w" if b0 == 0x88 else ".b"
        return (2, "movc" + sfx, [_r((b1 >> 4) & 0xF), f"[{_r(b1 & 0x7)}+]"])
    if b0 in (0xA7, 0xAF):                      # MOVX Rd,[Rs] / [Rd],Rs  (6-125)
        b1 = mem[pc + 1]
        sfx = ".w" if b0 == 0xAF else ".b"
        reg = _r((b1 >> 4) & 0xF)
        mem_op = f"[{_r(b1 & 0x7)}]"
        return (2, "movx" + sfx, [reg, mem_op] if ((b1 >> 3) & 1) == 0 else [mem_op, reg])
    if 0xB1 <= b0 <= 0xB6 or 0xB9 <= b0 <= 0xBE:  # MOVS <dest>,#data4  (6-123/124)
        msub = b0 & 0x7
        sfx = ".w" if (b0 & 0x08) else ".b"
        b1 = mem[pc + 1]
        imm = f"#0x{b1 & 0xF:x}"
        if msub == 0b001:                        # Rd, #data4
            return (2, "movs" + sfx, [_r((b1 >> 4) & 0xF), imm])
        ptr = (b1 >> 4) & 0x7
        if msub == 0b010:
            return (2, "movs" + sfx, [f"[{_r(ptr)}]", imm])
        if msub == 0b011:
            return (2, "movs" + sfx, [f"[{_r(ptr)}+]", imm])
        if msub == 0b100:
            return (3, "movs" + sfx, [f"[{_r(ptr)}+0x{mem[pc + 2]:02x}]", imm])
        if msub == 0b101:
            off = (mem[pc + 2] << 8) | mem[pc + 3]
            return (4, "movs" + sfx, [f"[{_r(ptr)}+0x{off:04x}]", imm])
        if msub == 0b110:
            return (3, "movs" + sfx, [f"0x{(ptr << 8) | mem[pc + 2]:03x}", imm])

    if b0 == 0x00:                               # NOP — 1 byte, all zeros (6-130)
        return (1, "nop", [])

    # -- bit manipulation: CLR/SETB/ANL/ORL (byte0 0x08; Ch.6) ---------------
    # byte1[7:2] selects the op; bit address (10-bit) = (byte1 & 3):byte2.
    if b0 == 0x08:
        b1 = mem[pc + 1]
        bit = ((b1 & 0x3) << 8) | mem[pc + 2]
        info = {0x00: ("clr", False),    # p. 6-79
                0x10: ("setb", False),   # p. 6-153
                0x40: ("anl", True),     # ANL C,bit  p. 6-53
                0x60: ("orl", True),     # ORL C,bit  p. 6-138
                }.get(b1 & 0xFC)
        if info is not None:
            mnem, with_c = info
            return (3, mnem, (["C", f"0x{bit:03x}"] if with_c else [f"0x{bit:03x}"]))
        # ANL/ORL C,/bit and MOV C,bit / bit,C use other byte1 values — TODO.

    # -- stack: PUSH/POP/PUSHU/POPU + XCH (Ch.6) -----------------------------
    if b0 in (0x87, 0x8F):                      # PUSH/POP direct (6-140/6-143) OR DJNZ Rd,rel8 (6-95)
        b1 = mem[pc + 1]
        sfx = ".w" if b0 == 0x8F else ".b"
        if (b1 & 0x0F) == 0x08:                 # DJNZ Rd,rel8 : byte1 = dddd 1000
            rel8 = mem[pc + 2] - 0x100 if mem[pc + 2] >= 0x80 else mem[pc + 2]
            return (3, "djnz" + sfx, [_r((b1 >> 4) & 0xF), f"0x{(pc + 3 + rel8 * 2) & 0xFFFFFF:x}"])
        op = {0x00: "popu", 0x10: "pop", 0x20: "pushu", 0x30: "push"}.get(b1 & 0xF8)
        if op is not None:
            direct = ((b1 & 0x7) << 8) | mem[pc + 2]
            return (3, op + sfx, [f"0x{direct:03x}"])
    if (b0 & 0x87) == 0x07:                      # PUSH/POP Rlist (6-141/6-144)
        word = bool((b0 >> 3) & 1)
        op = ("pop" if (b0 >> 5) & 1 else "push") + ("u" if (b0 >> 4) & 1 else "")
        return (2, op + (".w" if word else ".b"),
                [_rlist(mem[pc + 1], word, bool((b0 >> 6) & 1))])
    if b0 in (0x60, 0x68):                       # XCH Rd,Rs (6-169)
        b1 = mem[pc + 1]
        return (2, "xch" + (".w" if b0 == 0x68 else ".b"), [_r((b1 >> 4) & 0xF), _r(b1 & 0xF)])
    if b0 in (0x50, 0x58):                       # XCH Rd,[Rs]
        b1 = mem[pc + 1]
        return (2, "xch" + (".w" if b0 == 0x58 else ".b"), [_r((b1 >> 4) & 0xF), f"[{_r(b1 & 0x7)}]"])
    if b0 in (0xA0, 0xA8):                       # XCH Rd,direct
        b1 = mem[pc + 1]
        direct = ((b1 & 0x7) << 8) | mem[pc + 2]
        return (3, "xch" + (".w" if b0 == 0xA8 else ".b"), [_r((b1 >> 4) & 0xF), f"0x{direct:03x}"])

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
