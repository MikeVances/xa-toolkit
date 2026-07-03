"""XA instruction-set data — clean-room from the *Philips XA User Guide* (1997).

Sourced entirely from public Philips/NXP documentation (facts, not copyrightable):
  - §2.5.1 Instruction Syntax & addressing modes .......... pp. 2-12 .. 2-14
  - §2.5.2 Instruction Set Summary (mnemonic list) ........ pp. 2-15 .. 2-17
  - Chapter 6 Instruction Set (per-opcode byte encoding) .. see ENCODING (WIP)

No proprietary SDK/IDA-module source is used here. See docs/CREDITS.md.
"""
from __future__ import annotations

from enum import Enum

# --------------------------------------------------------------------------
# Mnemonics, grouped exactly as the User Guide §2.5.2 presents them.
# --------------------------------------------------------------------------
BASIC_ALU = ["add", "addc", "sub", "subb", "cmp", "and", "or", "xor", "mov"]      # p. 2-15
ADD_ARITH = ["adds", "neg", "sext", "mul", "div", "da", "asl", "asr", "lea"]      # p. 2-16
ADD_LOGIC = ["cpl", "lsr", "norm", "rl", "rlc", "rr", "rrc"]                      # p. 2-16
DATA_MOVE = ["movs", "movc", "movx", "push", "pop", "xch"]                        # p. 2-16
BIT_OPS   = ["setb", "clr", "mov", "anl", "orl"]                                  # p. 2-16 (bit forms; MOV/ANL/ORL act on carry)
FLOW      = ["br", "jmp", "call", "ret", "cjne", "djnz", "jz", "jnz", "jb", "jnb"]  # p. 2-17
MISC      = ["nop", "bkpt", "trap", "reset"]                                      # p. 2-17
# RETI ("return from interrupt") is described in §2.3; RET summary covers
# "return from subroutine or interrupt". Exact split confirmed in Chapter 6.

# Conditional-branch family: "Bcc — conditional branches with 15 possible
# condition variations" (p. 2-17). Condition-code -> opcode mapping is in Ch.6.
BCC = [
    "bcc", "bcs", "bne", "beq", "bnv", "bov", "bpl", "bmi",
    "bg", "bl", "bge", "blt", "bgt", "ble", "br",
]

# Full mnemonic set (deduplicated), for validation/printing.
MNEMONICS = sorted(set(
    BASIC_ALU + ADD_ARITH + ADD_LOGIC + DATA_MOVE + BIT_OPS + FLOW + MISC + BCC
))


# --------------------------------------------------------------------------
# Addressing modes — from §2.5.1 (syntax) and the §2.5.2 operand table.
#   R          register            (word Rn, or byte RnL/RnH with .b size)
#   [R]        indirect
#   [R+]       indirect auto-increment (post-inc by data size)   (Fig 2.11)
#   [R+off]    indirect with 8- or 16-bit signed offset          (p. 2-13)
#   direct     direct data address (first 1K of a segment) or SFR
#   #data      immediate, 8- or 16-bit (or 4-bit "short" for ADDS/MOVS)
#   bit        bit address (reg.bit form, e.g. PSWL.7)           (p. 2-14)
# --------------------------------------------------------------------------
class Mode(Enum):
    R_R          = "R,R"
    R_IND        = "R,[R]"
    IND_R        = "[R],R"
    R_INDINC     = "R,[R+]"
    INDINC_R     = "[R+],R"
    R_INDOFF     = "R,[R+offset]"
    INDOFF_R     = "[R+offset],R"
    DIRECT_R     = "direct,R"
    R_DIRECT     = "R,direct"
    R_IMM        = "R,#data"
    IND_IMM      = "[R],#data"
    INDINC_IMM   = "[R+],#data"
    INDOFF_IMM   = "[R+offset],#data"
    DIRECT_IMM   = "direct,#data"
    # branch / bit / implied forms (REL8, bit,REL8, implied) added with Ch.6.


# Size suffixes: instructions on indirect/immediate must state size (.b/.w),
# because those operands don't imply width (p. 2-14).
class Size(Enum):
    BYTE = "b"
    WORD = "w"


# Register-file names (from §2.2.1 register diagram, p. 2-2).
WORD_REGS = [f"R{i}" for i in range(16)]                     # R0..R15 (R8..R15 word-only)
BYTE_REGS = [f"R{i}{h}" for i in range(4) for h in ("L", "H")] + \
            [f"R{i}{h}" for i in range(4, 8) for h in ("L", "H")]  # R0L..R7H

# Core SFRs named in the architecture chapter (§2.3, p. 2-7): control/status.
CORE_SFRS = ["PSWL", "PSWH", "SCR", "SSEL", "ES", "DS", "CS", "PCON"]


# ==========================================================================
# ENCODING structure — from Chapter 6 opcode tables (verified byte-for-byte).
#
# Basic-ALU group (Ch.6 pp. 6-32..6-35, ADD reference; the group shares one
# regular encoding). Register/memory forms:
#     byte0 = OOOO S mmm    OOOO = ALU op nibble, S = size bit, mmm = sub-mode
#     byte1 = dddd ssss     bit3 of byte1 = direction (0: reg,mem  1: mem,reg)
# Immediate forms use opcode high-nibble 0x9 and carry the ALU op in the LOW
# nibble of byte1 (byte0 bit3 = data16 flag, byte0 low 3 bits = sub-mode).
#
# Only opcode nibbles VERIFIED against the datasheet are listed. Unverified
# ops decode as "alu<n>" (never fabricated). Fill remaining nibbles by reading
# their Ch.6 pages (ADDC/SUB/SUBB/CMP/AND/OR/XOR/MOV).
# ==========================================================================

# ALU op nibble -> mnemonic. VERIFIED: ADD = 0b0000 (Ch.6 p. 6-32).
ALU_OPS: dict[int, str] = {
    0x0: "add",   # p. 6-32, byte-for-byte
    # 0x1: "addc", 0x2: "sub", ... — TODO: read each op's Ch.6 page to confirm.
}

# Sub-mode (byte0 low 3 bits) -> (name, total_size_bytes). From ADD (p.6-32..35).
ALU_SUBMODES = {
    0b001: ("reg",     2),   # Rd, Rs
    0b010: ("ind",     2),   # Rd,[Rs] / [Rd],Rs
    0b011: ("ind_inc", 2),   # Rd,[Rs+] / [Rd+],Rs
    0b100: ("off8",    3),   # Rd,[Rs+offset8]
    0b101: ("off16",   4),   # Rd,[Rs+offset16]
    0b110: ("direct",  3),   # Rd,direct  (11-bit direct: 3 bits in byte1 + byte2)
}

# Legacy placeholder kept for API stability.
ENCODING: dict[int, dict] = {}
