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

# ALU op nibble -> mnemonic. Each nibble read byte-for-byte from the "Rd, Rs"
# encoding on that instruction's Chapter-6 page (manual verification, not parsed).
ALU_OPS: dict[int, str] = {
    0x0: "add",    # p. 6-32
    0x1: "addc",   # p. 6-38
    0x2: "sub",    # p. 6-155
    0x3: "subb",   # p. 6-161
    0x4: "cmp",    # p. 6-80
    0x5: "and",    # p. 6-47
    0x6: "or",     # p. 6-132
    0x7: "xor",    # p. 6-170
    0x8: "mov",    # p. 6-110
}
# Immediate forms (byte0 hi-nibble 0x9) carry the ALU op in byte1's LOW nibble.
# Verified for ADD (byte1 = dddd 0000). The other ops reuse the same nibble map
# above (structural — confirm per-op when their immediate pages are read).

# Sub-mode (byte0 low 3 bits) -> (name, total_size_bytes). From ADD (p.6-32..35).
ALU_SUBMODES = {
    0b001: ("reg",     2),   # Rd, Rs
    0b010: ("ind",     2),   # Rd,[Rs] / [Rd],Rs
    0b011: ("ind_inc", 2),   # Rd,[Rs+] / [Rd+],Rs
    0b100: ("off8",    3),   # Rd,[Rs+offset8]
    0b101: ("off16",   4),   # Rd,[Rs+offset16]
    0b110: ("direct",  3),   # Rd,direct  (11-bit direct: 3 bits in byte1 + byte2)
}

# --------------------------------------------------------------------------
# Short branches — opcode block 0xF0..0xFE, byte1 = rel8 (Ch.6). Each opcode
# read byte-for-byte from its page: byte0 = 0xF0 | cc. Target = PC+2+rel8*2
# (rel8 signed; word-aligned). 0xFF = BKPT (1 byte, all-ones). Pages: BCC 6-59,
# BNE 6-70, BEQ 6-61, BNV 6-71, BOV 6-72, BPL 6-73, BMI 6-69, BG 6-62, BL 6-66,
# BGE 6-63, BLT 6-68, BGT 6-64, BLE 6-67, BR 6-74, BKPT 6-65.
# --------------------------------------------------------------------------
BRANCH_CC: dict[int, str] = {
    0x0: "bcc", 0x1: "bcs", 0x2: "bne", 0x3: "beq",
    0x4: "bnv", 0x5: "bov", 0x6: "bpl", 0x7: "bmi",
    0x8: "bg",  0x9: "bl",  0xA: "bge", 0xB: "blt",
    0xC: "bgt", 0xD: "ble", 0xE: "br",
}
OP_BKPT = 0xFF  # breakpoint, Ch.6 p. 6-65

# --------------------------------------------------------------------------
# Far/absolute + register-indirect control flow (read byte-for-byte from Ch.6).
# These live in the 0xD4..0xD6 opcodes, which are unambiguous vs. the shift
# group (shifts use 0xC?/0xD? only with a valid 2-bit size field; the 0x?4/?5/?6
# low nibbles here correspond to size=01, which is not a valid shift size).
#   FJMP addr24  = 0xD4  (p. 6-97): byte1=addr[15:8], byte2=addr[7:0], byte3=addr[23:16]
#   JMP  rel16   = 0xD5  (p. 6-100): byte1..2 = rel16 (hi,lo); target = PC+3+rel16*2
#   0xD6 group   = multiplexed by byte1: RET 0x80 (6-147), RETI 0x90 (6-148),
#                  JMP [Rs] = 0b01110sss (6-101).
# --------------------------------------------------------------------------
OP_FJMP = 0xD4
OP_JMP_REL16 = 0xD5
OP_D6 = 0xD6

# DEFERRED — do NOT add without resolving (honest gaps):
#   FCALL addr24: p. 6-96 shows opcode 0xC2, but that also matches a byte-size
#     shift (ASR.b etc. = 0xC2). Resolve the collision when the shift group is read.
#   CALL rel16 (3 bytes): opcode box did not render on p. 6-75 — needs a re-read.

# --------------------------------------------------------------------------
# Shift / rotate group (read byte-for-byte from Ch.6). Byte & word forms only
# here; the double-word (#data5) forms and LSR/NORM are deferred (not yet read).
#
# Arithmetic shifts — size in bits 3-2 (SZ1 SZ0: 00->.b, 10->.w):
#   ASL reg (Rd,Rs)   1100 SZ1SZ0 01   p. 6-56    ASL imm (Rd,#data4) 1101 SZ1SZ0 01
#   ASR reg (Rd,Rs)   1100 SZ1SZ0 10   p. 6-58    ASR imm (Rd,#data4) 1101 SZ1SZ0 10
# Rotates — single size bit (SZ: 0->.b, 1->.w), immediate #data4 only:
#   RR  1011 SZ 000  6-151   RRC 1011 SZ 111  6-152
#   RL  1101 SZ 011  6-149   RLC 1101 SZ 111  6-150
# NOTE: ASR.b reg (0xC2) shares byte0 with the deferred FCALL — no active clash
# because FCALL is not decoded yet; resolve when FCALL is added.
# --------------------------------------------------------------------------
SHIFT_REG: dict[int, tuple] = {          # byte1 = dddd ssss -> "Rd, Rs"
    0xC1: ("asl", ".b"), 0xC9: ("asl", ".w"),
    0xC2: ("asr", ".b"), 0xCA: ("asr", ".w"),
}
SHIFT_IMM4: dict[int, tuple] = {         # byte1 = dddd <#data4> -> "Rd, #data4"
    0xD1: ("asl", ".b"), 0xD9: ("asl", ".w"),
    0xD2: ("asr", ".b"), 0xDA: ("asr", ".w"),
    0xD3: ("rl",  ".b"), 0xDB: ("rl",  ".w"),
    0xD7: ("rlc", ".b"), 0xDF: ("rlc", ".w"),
    0xB0: ("rr",  ".b"), 0xB8: ("rr",  ".w"),
    0xB7: ("rrc", ".b"), 0xBF: ("rrc", ".w"),
}

# Legacy placeholder kept for API stability.
ENCODING: dict[int, dict] = {}
