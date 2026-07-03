# Using xa-toolkit from an LLM / agent

`xa-toolkit` is designed to be driven by LLM agents, not just humans. Every command emits
**structured JSON** with `--json`, and the package exposes a small, stable Python API and an
optional **MCP server** so a model can call the disassembler as a native tool.

## Tool surface

| Capability | CLI | Python | JSON out |
|---|---|---|---|
| Disassemble a range | `xa disasm FILE --base A --start S --len N --json` | `disasm.decode(mem, pc)` | list of instructions |
| Cross-references | `xa xref FILE --to ADDR --json` | `disasm.xrefs(mem, base)` | callers/branchers of ADDR |
| Emulate a routine | `xa emu FILE --entry ADDR --json` | `emu.run(mem, entry)` | final regs/RAM/SFR reads |

### Instruction JSON schema

```json
{
  "addr": 45600,
  "bytes": "96 22 b2",
  "size": 3,
  "mnemonic": "mov",
  "operands": ["R2", "[0x22b2]"],
  "flow": {"kind": "call|jump|cond|ret|none", "target": 49696}
}
```

Fields are stable; new fields may be added but existing ones will not change meaning.

## MCP server (optional)

```bash
pip install "xa-toolkit[mcp]"
xa mcp            # exposes tools: xa_disasm, xa_xref, xa_emulate over stdio
```

Point your MCP-capable client (Claude Desktop / Code, etc.) at `xa mcp`. The tools return the
same JSON as the CLI, so an agent can chain: disassemble → find xrefs → emulate a callee.

## Prompt patterns that work well

- "Disassemble `fw.bin` from 0xc220 for 64 bytes and summarise what the routine does."
- "Find every FCALL/CALL that targets 0xc220 and list the caller addresses."
- "Emulate the routine at 0xc220 with R1=5 and report which SFRs it writes."

## Guidance for the agent

- The XA is **little-endian for data**, instructions are **big-endian byte order**, 2–4 bytes each.
- Always pass the correct `--base` (load address) or addresses/xrefs will be wrong.
- Prefer `--json`; parse it rather than scraping the human table.
- Disassembly is a *hint*, not ground truth: verify control flow with `xref`/`emu` before
  asserting a routine's behaviour.
