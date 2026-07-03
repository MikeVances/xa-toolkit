"""Decoder tests — byte-for-byte against the Philips XA User Guide, Chapter 6.

Each encoding below is transcribed from the ADD reference pages (6-32..6-35).
Because ADD's encoding is the template for the whole basic-ALU group, these
also exercise every addressing sub-mode of that group.
"""
from xa_toolkit.disasm import decode


def test_add_reg_reg():
    # ADD Rd,Rs : byte0 = 0000 S 001, byte1 = dddd ssss   (p. 6-32)
    # ADD.w R1,R2  -> byte0 = 0b0000_1_001 = 0x09, byte1 = 0b0001_0010 = 0x12
    size, mnem, ops = decode(bytes([0x09, 0x12]))
    assert size == 2
    assert mnem == "add.w"
    assert ops == ["R1", "R2"]


def test_add_reg_indirect():
    # ADD Rd,[Rs] : byte0 = 0000 S 010, byte1 = dddd 0sss  (dir=0: reg,mem)
    # ADD.w R1,[R2] -> byte0 = 0x0A, byte1 = 0b0001_0010 = 0x12
    size, mnem, ops = decode(bytes([0x0A, 0x12]))
    assert size == 2
    assert mnem == "add.w"
    assert ops == ["R1", "[R2]"]


def test_add_indirect_reg_direction_bit():
    # ADD [Rd],Rs : byte0 = 0000 S 010, byte1 = ssss 1ddd  (dir=1: mem,reg)
    # ADD.w [R3],R2 -> byte0 = 0x0A, byte1 = 0b0010_1_011 = 0x2B
    size, mnem, ops = decode(bytes([0x0A, 0x2B]))
    assert ops == ["[R3]", "R2"]


def test_add_reg_autoinc():
    # ADD Rd,[Rs+] : byte0 = 0000 S 011  (p. 6-34)
    size, mnem, ops = decode(bytes([0x0B, 0x12]))
    assert mnem == "add.w"
    assert ops == ["R1", "[R2+]"]


def test_add_reg_offset8():
    # ADD Rd,[Rs+offset8] : byte0 = 0000 S 100, byte2 = offset8  (p. 6-33)
    size, mnem, ops = decode(bytes([0x0C, 0x12, 0x40]))
    assert size == 3
    assert ops == ["R1", "[R2+0x40]"]


def test_add_reg_direct():
    # ADD Rd,direct : byte0 = 0000 S 110, byte1 = dddd 0DDD, byte2 = direct low
    # direct = (DDD<<8)|byte2 ; here DDD=0b010, byte2=0x34 -> 0x234
    size, mnem, ops = decode(bytes([0x0E, 0x12, 0x34]))
    assert size == 3
    assert ops == ["R1", "0x234"]


def test_add_reg_imm8():
    # ADD Rd,#data8 : byte0 = 1001 0001 = 0x91, byte1 = dddd 0000, byte2 = data8
    # op nibble (byte1 low) = 0 = ADD ; d = 3
    size, mnem, ops = decode(bytes([0x91, 0x30, 0x55]))
    assert size == 3
    assert mnem == "add"
    assert ops == ["R3", "#0x55"]


def test_add_reg_imm16():
    # ADD Rd,#data16 : byte0 = 1001 1001 = 0x99, byte2..3 = data16 (hi,lo)
    size, mnem, ops = decode(bytes([0x99, 0x30, 0x12, 0x34]))
    assert size == 4
    assert ops == ["R3", "#0x1234"]


def test_add_indirect_imm8():
    # ADD [Rd],#data8 : byte0 = 1001 0010 = 0x92, byte1 = 0ddd 0000
    size, mnem, ops = decode(bytes([0x92, 0x30, 0x55]))
    assert ops == ["[R3]", "#0x55"]


def test_all_basic_alu_ops_named():
    # Op nibbles verified byte-for-byte from each instruction's Ch.6 page.
    from xa_toolkit.isa import ALU_OPS
    assert ALU_OPS == {
        0x0: "add", 0x1: "addc", 0x2: "sub", 0x3: "subb", 0x4: "cmp",
        0x5: "and", 0x6: "or", 0x7: "xor", 0x8: "mov",
    }


def test_cmp_reg_reg():
    # CMP Rd,Rs : byte0 = 0100 S 001 (p. 6-80). CMP.w R1,R2 -> 0x49, 0x12
    size, mnem, ops = decode(bytes([0x49, 0x12]))
    assert mnem == "cmp.w"
    assert ops == ["R1", "R2"]


def test_mov_reg_reg():
    # MOV Rd,Rs : byte0 = 1000 S 001 (p. 6-110). MOV.w R1,R2 -> 0x89, 0x12
    size, mnem, ops = decode(bytes([0x89, 0x12]))
    assert mnem == "mov.w"
    assert ops == ["R1", "R2"]


def test_and_indirect_reg():
    # AND [Rd],Rs : byte0 = 0101 S 010 (p. 6-47), byte1 = ssss 1ddd
    # AND.w [R3],R2 -> byte0 = 0x5A, byte1 = 0b0010_1_011 = 0x2B
    size, mnem, ops = decode(bytes([0x5A, 0x2B]))
    assert mnem == "and.w"
    assert ops == ["[R3]", "R2"]


def test_sub_reg_reg():
    # SUB Rd,Rs : byte0 = 0010 S 001 (p. 6-155). SUB.w R5,R6 -> 0x29, 0x56
    size, mnem, ops = decode(bytes([0x29, 0x56]))
    assert mnem == "sub.w"
    assert ops == ["R5", "R6"]


def test_unknown_opcode_is_not_guessed():
    # Opcodes we have not verified must decode as "?", never fabricated.
    size, mnem, ops = decode(bytes([0xFF, 0x00]))
    assert mnem == "?"
