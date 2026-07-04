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


def test_branch_condition_codes_named():
    from xa_toolkit.isa import BRANCH_CC
    assert BRANCH_CC[0x0] == "bcc"
    assert BRANCH_CC[0x3] == "beq"
    assert BRANCH_CC[0xE] == "br"


def test_bcc_forward_target():
    # BCC rel8 (0xF0). rel8 = +3 -> target = pc(0) + 2 + 3*2 = 8  (p. 6-59)
    size, mnem, ops = decode(bytes([0xF0, 0x03]))
    assert size == 2
    assert mnem == "bcc"
    assert ops == ["0x8"]


def test_branch_backward_target():
    # rel8 = -1 (0xFF) -> target = 0 + 2 + (-1)*2 = 0
    size, mnem, ops = decode(bytes([0xF0, 0xFF]))
    assert ops == ["0x0"]


def test_beq_bne_br():
    assert decode(bytes([0xF3, 0x00]))[1] == "beq"
    assert decode(bytes([0xF2, 0x00]))[1] == "bne"
    assert decode(bytes([0xFE, 0x00]))[1] == "br"   # unconditional


def test_bkpt_is_one_byte():
    # BKPT = 0xFF, all-ones opcode, 1 byte (p. 6-65)
    size, mnem, ops = decode(bytes([0xFF]))
    assert size == 1
    assert mnem == "bkpt"


def test_fjmp_addr24():
    # FJMP addr24 (0xD4): byte1=addr[15:8], byte2=addr[7:0], byte3=addr[23:16] (p. 6-97)
    size, mnem, ops = decode(bytes([0xD4, 0x34, 0x12, 0x56]))
    assert size == 4
    assert mnem == "fjmp"
    assert ops == ["0x563412"]


def test_jmp_rel16():
    # JMP rel16 (0xD5): rel16 = +2 -> target = pc(0) + 3 + 2*2 = 7 (p. 6-100)
    size, mnem, ops = decode(bytes([0xD5, 0x00, 0x02]))
    assert size == 3
    assert mnem == "jmp"
    assert ops == ["0x7"]


def test_jmp_indirect_reg():
    # JMP [Rs] (0xD6, byte1 = 0b01110sss) (p. 6-101). Rs=3 -> byte1 = 0x73
    size, mnem, ops = decode(bytes([0xD6, 0x73]))
    assert size == 2
    assert mnem == "jmp"
    assert ops == ["[R3]"]


def test_ret_and_reti():
    # RET = 0xD6 0x80 (6-147); RETI = 0xD6 0x90 (6-148)
    assert decode(bytes([0xD6, 0x80])) == (2, "ret", [])
    assert decode(bytes([0xD6, 0x90])) == (2, "reti", [])


def test_asl_reg():
    # ASL Rd,Rs : 1100 SZ1SZ0 01 (p. 6-56). ASL.b R1,R2 -> 0xC1, 0x12
    size, mnem, ops = decode(bytes([0xC1, 0x12]))
    assert size == 2 and mnem == "asl.b" and ops == ["R1", "R2"]


def test_asr_word_reg():
    # ASR.w Rd,Rs : 0xCA (1100 10 10). R3,R5 -> byte1 0x35
    assert decode(bytes([0xCA, 0x35])) == (2, "asr.w", ["R3", "R5"])


def test_rl_imm4():
    # RL Rd,#data4 : 1101 SZ 011 (p. 6-149). RL.b R2,#4 -> 0xD3, byte1 0x24
    assert decode(bytes([0xD3, 0x24])) == (2, "rl.b", ["R2", "#0x4"])


def test_rr_and_rrc():
    # RR 1011 SZ 000 (6-151); RRC 1011 SZ 111 (6-152)
    assert decode(bytes([0xB0, 0x17])) == (2, "rr.b", ["R1", "#0x7"])
    assert decode(bytes([0xBF, 0x50])) == (2, "rrc.w", ["R5", "#0x0"])


def test_rlc_word():
    # RLC.w : 0xDF (1101 1 111). R4,#3 -> byte1 0x43
    assert decode(bytes([0xDF, 0x43])) == (2, "rlc.w", ["R4", "#0x3"])


def test_movc_indirect_autoinc():
    # MOVC Rd,[Rs+] : 1000 SZ 000 (p. 6-120). MOVC.b R1,[R2+] -> 0x80, 0x12
    assert decode(bytes([0x80, 0x12])) == (2, "movc.b", ["R1", "[R2+]"])


def test_movc_a_dptr_and_pc():
    # MOVC A,[A+DPTR] = 0x90 0x4E (6-121); MOVC A,[A+PC] = 0x90 0x4C (6-122)
    assert decode(bytes([0x90, 0x4E])) == (2, "movc", ["A", "[A+DPTR]"])
    assert decode(bytes([0x90, 0x4C])) == (2, "movc", ["A", "[A+PC]"])


def test_movx_both_directions():
    # MOVX 0xA7/0xAF, byte1 direction bit (p. 6-125)
    assert decode(bytes([0xA7, 0x12])) == (2, "movx.b", ["R1", "[R2]"])   # Rd,[Rs]
    assert decode(bytes([0xA7, 0x2B])) == (2, "movx.b", ["[R3]", "R2"])   # [Rd],Rs


def test_movs_reg_and_indirect():
    # MOVS <dest>,#data4 : 1011 SZ sub (p. 6-123). Coexists with RR/RRC (0xB0/B7/B8/BF).
    assert decode(bytes([0xB1, 0x57])) == (2, "movs.b", ["R5", "#0x7"])
    assert decode(bytes([0xB2, 0x34])) == (2, "movs.b", ["[R3]", "#0x4"])


def test_rotate_still_wins_b0_b7():
    # sanity: 0xB0/0xB7 remain RR/RRC, not MOVS (MOVS is 0xB1..0xB6)
    assert decode(bytes([0xB0, 0x17]))[1] == "rr.b"
    assert decode(bytes([0xB7, 0x10]))[1] == "rrc.b"


def test_push_pop_direct():
    # PUSH direct 0x87/8F, byte1 bits5-4 select push/pop/user (6-140/6-143).
    # PUSH.b 0x234 -> byte0 0x87, byte1 0x32 (0x30|2), byte2 0x34
    assert decode(bytes([0x87, 0x32, 0x34])) == (3, "push.b", ["0x234"])
    assert decode(bytes([0x8F, 0x11, 0x05])) == (3, "pop.w", ["0x105"])
    assert decode(bytes([0x87, 0x20, 0x00]))[1] == "pushu.b"
    assert decode(bytes([0x87, 0x00, 0x00]))[1] == "popu.b"


def test_push_pop_rlist():
    # PUSH Rlist word: byte0 = 0 HL pp uu SZ 111. PUSH.w = 0x0F, bitmap bit0|bit2
    assert decode(bytes([0x0F, 0x05])) == (2, "push.w", ["{R0,R2}"])
    assert decode(bytes([0x2F, 0x80])) == (2, "pop.w", ["{R7}"])
    # byte lower group (SZ=0, HL=0): bit0=R0L, bit3=R1H
    assert decode(bytes([0x07, 0x09])) == (2, "push.b", ["{R0L,R1H}"])


def test_xch_forms():
    assert decode(bytes([0x60, 0x12])) == (2, "xch.b", ["R1", "R2"])       # Rd,Rs
    assert decode(bytes([0x58, 0x34])) == (2, "xch.w", ["R3", "[R4]"])     # Rd,[Rs]
    assert decode(bytes([0xA0, 0x19, 0x02])) == (3, "xch.b", ["R1", "0x102"])  # Rd,direct


def test_bit_ops():
    # byte0 0x08; byte1[7:2] = op; bit addr (10-bit) = (byte1 & 3):byte2 (Ch.6)
    assert decode(bytes([0x08, 0x41, 0x23])) == (3, "anl", ["C", "0x123"])   # ANL C,bit (6-53)
    assert decode(bytes([0x08, 0x61, 0x05])) == (3, "orl", ["C", "0x105"])   # ORL C,bit (6-138)
    assert decode(bytes([0x08, 0x00, 0x80])) == (3, "clr", ["0x080"])        # CLR bit (6-79)
    assert decode(bytes([0x08, 0x12, 0xA0])) == (3, "setb", ["0x2a0"])       # SETB bit (6-153)


def test_jz_jnz():
    # JZ 0xEC (6-106), JNZ 0xEE (6-105): rel8 -> target = PC+2+rel8*2
    assert decode(bytes([0xEC, 0x02])) == (2, "jz", ["0x6"])
    assert decode(bytes([0xEE, 0x00])) == (2, "jnz", ["0x2"])


def test_jb_jnb_jbc():
    # 0x97, byte1 top bits select jb(0x80)/jnb(0xA0)/jbc(0xC0); bit,rel8 (6-98/104/99)
    assert decode(bytes([0x97, 0x81, 0x05, 0x01])) == (4, "jb", ["0x105", "0x6"])
    assert decode(bytes([0x97, 0xA0, 0x00, 0x00])) == (4, "jnb", ["0x000", "0x4"])
    assert decode(bytes([0x97, 0xC0, 0x00, 0x00]))[1] == "jbc"


def test_cjne_forms():
    # CJNE Rd,direct,rel8 (0xE2, byte1 bit3=0) (6-77)
    assert decode(bytes([0xE2, 0x12, 0x34, 0x01])) == (4, "cjne.b", ["R1", "0x234", "0x6"])
    # CJNE Rd,#data8,rel8 (0xE3, byte1 bit3=0) (6-78)
    assert decode(bytes([0xE3, 0x30, 0x01, 0x55])) == (4, "cjne.b", ["R3", "#0x55", "0x6"])
    # CJNE [Rd],#data8,rel8 (0xE3, byte1 bit3=1)
    assert decode(bytes([0xE3, 0x28, 0x01, 0x55])) == (4, "cjne.b", ["[R2]", "#0x55", "0x6"])


def test_djnz_forms():
    # DJNZ Rd,rel8 (0x87, byte1 = dddd 1000; shares byte0 with PUSH/POP) (6-95)
    assert decode(bytes([0x87, 0x18, 0x01])) == (3, "djnz.b", ["R1", "0x5"])
    # DJNZ direct,rel8 (0xE2, byte1 bit3=1; shares byte0 with CJNE Rd,direct)
    assert decode(bytes([0xE2, 0x0A, 0x34, 0x01])) == (4, "djnz.b", ["0x234", "0x6"])
    # sanity: PUSH still wins its 0x87 byte1
    assert decode(bytes([0x87, 0x32, 0x34]))[1] == "push.b"


def test_unary_ops():
    # 0x90/0x98, byte1 low nibble = op (DA 8 / SEXT 9 / CPL A / NEG B)
    assert decode(bytes([0x90, 0x1B])) == (2, "neg.b", ["R1"])    # NEG (6-129)
    assert decode(bytes([0x98, 0x3A])) == (2, "cpl.w", ["R3"])    # CPL (6-87)
    assert decode(bytes([0x90, 0x28])) == (2, "da.b", ["R2"])     # DA  (6-88)
    assert decode(bytes([0x90, 0x59])) == (2, "sext.b", ["R5"])   # SEXT (6-154)


def test_nop():
    # NOP = 0x00, 1 byte (6-130)
    assert decode(bytes([0x00])) == (1, "nop", [])


def test_trap():
    # TRAP #data4 = 0xD6, byte1 = 0011 dddd (6-168)
    assert decode(bytes([0xD6, 0x35])) == (2, "trap", ["#0x5"])


def test_unknown_opcode_is_not_guessed():
    # An opcode group we have not decoded yet must render "?", never fabricated.
    size, mnem, ops = decode(bytes([0xE0, 0x00]))
    assert mnem == "?"
