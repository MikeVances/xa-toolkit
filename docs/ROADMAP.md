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

1. [ ] **Confirm SZ (size-bit) polarity** from Ch.6 general encoding notes; make `.b/.w` authoritative.
2. [ ] **Fill `ALU_OPS`**: read the ADDC/SUB/SUBB/CMP/AND/OR/XOR/MOV pages → op nibbles (byte-verify each).
3. [ ] **Shift/misc group**: ASL/ASR/LSR/RL/RLC/RR/RRC/NORM, NEG/SEXT/CPL/DA, ADDS, MUL/DIV, LEA.
4. [ ] **Data movement**: MOVS, MOVC, MOVX, PUSH/PUSHU/POP/POPU (incl. Rlist), XCH.
5. [ ] **Program flow**: BR, Bcc (15), CALL/rel16 & [Rs], FCALL/FJMP addr24, JMP variants, CJNE, DJNZ, JB/JBC/JNB, JZ/JNZ, RET, RETI.
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
