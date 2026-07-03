# xa-toolkit

Pure-Python toolkit for the **Philips / NXP 80C51XA** (eXtended Architecture) 16-bit
microcontroller family (XA-G3 / XA-S3 / XA-G49): a **disassembler**, **emulator**, and
execution **tracer** — plus first-class **LLM / agent integration** (structured JSON output
and an MCP server).

> There is almost nothing open-source for the 80C51XA. This fills the gap: a small, hackable,
> dependency-free toolkit for reversing and analysing XA firmware.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Status](https://img.shields.io/badge/status-alpha-orange)

## Why

The XA is a 16-bit, 80C51-compatible core (Philips, mid-90s) still found in industrial,
automotive and appliance firmware. Modern RE tooling (Ghidra/radare2) has weak or no XA
support, and the one IDA processor module for it is unmaintained. `xa-toolkit` gives you a
scriptable decoder you can drop into Python pipelines — and hand to an LLM.

## Features

- 🧩 **Disassembler** — decode XA instructions to `(size, mnemonic, operands)`; linear sweep,
  FCALL/FJMP/CALL/JMP/direct-xref extraction.
- 🖥️ **Emulator** — execute selected routines (registers, RAM, SFRs) for data-flow analysis.
- 🔎 **Tracer** — follow execution / collect reachable code.
- 📦 **Zero dependencies** — Python stdlib only.
- 🤖 **LLM-ready** — `--json` structured output + `AGENTS.md` + optional MCP server, so an
  agent can call the disassembler as a tool. See [AGENTS.md](AGENTS.md).

## Install

```bash
pip install xa-toolkit        # (after first release)
# or from source:
pip install -e .
```

## Quickstart

```bash
xa disasm firmware.bin --base 0x0000            # linear disassembly
xa disasm firmware.bin --json > insns.json      # structured, for tools/LLMs
xa xref  firmware.bin --to 0xc220               # who calls 0xc220
```

```python
from xa_toolkit.disasm import decode
size, mnem, ops = decode(memory, pc)
```

## Provenance & credits

This decoder is a **clean-room implementation derived from the public Philips
*XA User Guide* and *80C51XA (IC25) datasheet*** (instruction encodings are factual ISA data,
not copyrightable). It intentionally does **not** reuse any proprietary SDK code.

Credit to **Petr Novak**, who authored the original XA processor module for IDA and first
mapped this ISA. (Contact/licensing in progress — see `docs/CREDITS.md`.)

No vendor firmware is included in this repository.

## License

MIT — see [LICENSE](LICENSE).
