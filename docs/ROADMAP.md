# Roadmap / build status

Clean-room XA toolkit. Every opcode is derived from the **public Philips XA User
Guide** (Chapter 6). Nothing is copied from IDA/Petr Novak's module; unverified
opcodes are never fabricated (they decode as `alu<n>` / `?`).

## Done (v0.1.0-alpha)
- [x] Repo scaffold: README, LICENSE (MIT), `pyproject.toml`, `.gitignore`, `AGENTS.md` (LLM block), `docs/CREDITS.md`.
- [x] `isa.py`: mnemonic set + addressing modes (User Guide §2.5); basic-ALU encoding structure (Ch.6).
- [x] `disasm.py`: decoder for the basic-ALU group (all 6 reg/mem sub-modes + immediate forms). `ADD` verified byte-for-byte.
- [x] `tests/test_disasm.py`: 10 tests, byte-exact from Ch.6 pp. 6-32..6-35. **All green.**

## Next (bulk extraction — best as a multi-agent workflow)
Source: *Philips XA User Guide*, Chapter 6 (per-instruction encodings) + Table 6.5 (sizes).

1. [x] **SZ (size-bit) polarity** = `1 -> word`, `0 -> byte` (confirmed via the shift group's
       SZ1/SZ0 note, p. 6-58: "00 byte, 10 word, 11 dword"). `.b/.w` suffix is now authoritative.
2. [x] **Fill `ALU_OPS`**: ADD/ADDC/SUB/SUBB/CMP/AND/OR/XOR/MOV = nibbles 0x0–0x8, each read
       byte-for-byte from its Ch.6 "Rd, Rs" page (manual, verified — no parser). Done 2026-07-03.
3. **Shift / rotate group**:
   - [x] ASL/ASR (reg + imm #data4, byte/word), RL/RLC/RR/RRC (imm #data4, byte/word). Done 2026-07-03.
         Resolved: ASR.b reg (0xC2) shares byte0 with the deferred FCALL.
   - [ ] Double-word (#data5) shift forms, LSR, NORM, NEG/SEXT/CPL/DA, ADDS, MUL/DIV, LEA.
4. [ ] **Data movement**: MOVS, MOVC, MOVX, PUSH/PUSHU/POP/POPU (incl. Rlist), XCH.
5. **Program flow**:
   - [x] Short branches: Bcc (14 condition codes 0xF0–0xFD) + BR (0xFE) + BKPT (0xFF), byte1=rel8,
         target = PC+2+rel8*2. Each opcode read byte-for-byte from its Ch.6 page. Done 2026-07-03.
   - [x] FJMP addr24 (0xD4), JMP rel16 (0xD5), JMP [Rs] / RET / RETI (0xD6 group). Done 2026-07-03.
   - [ ] **FCALL** (0xC2 collides with a byte-shift — resolve with the shift group) and
         **CALL rel16** (opcode box didn't render on p. 6-75 — re-read).
   - [ ] JMP [A+DPTR] / JMP [[Rs+]] (other 0xD6 byte1 forms), CJNE, DJNZ, JB/JBC/JNB, JZ/JNZ.
6. [ ] **Bit ops**: ANL/ORL C,bit(/bit), CLR/SETB bit, MOV C,bit / bit,C.
7. [ ] **Exception**: NOP, BKPT, RESET, TRAP #data4.
8. [ ] Per-opcode test (each row ↔ its Ch.6 page). **Adversarially verify** every encoding against the datasheet.

## Then
- [ ] `emu.py` — execute decoded instructions (regs/RAM/SFR) for data-flow analysis.
- [ ] `trace.py`, `cli.py` (`xa disasm/xref/emu`, `--json`).
- [ ] MCP server (`xa mcp`) per `AGENTS.md`.
- [ ] `git init` + first commit + push to `github.com/MikeVances/xa-toolkit`.
- [ ] Petr Novak outreach (draft ready) — attribution / optional license of the original module.

## Workflow sketch (for the bulk extraction)
Parallel readers over Ch.6 page-ranges → each emits structured `{mnemonic, operands, byte0_pattern,
byte1_pattern, extra_bytes, size, page}` JSON → synthesise into `isa.py` tables → an adversarial verifier
re-checks each opcode's bit pattern against its datasheet page before it lands. Discipline: never invent a
constant; a row without a confirming page stays out.
