"""Command-line interface for xa-toolkit.

    xa disasm FILE [--base A] [--start S] [--len N] [--json]

Linear-sweep disassembly. Human-readable table by default; `--json` emits the
structured records described in AGENTS.md (one object per instruction) for use
in tool pipelines / LLM agents.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import __version__
from .disasm import decode

_COND = {
    "bcc", "bcs", "bne", "beq", "bnv", "bov", "bpl", "bmi", "bg", "bl", "bge",
    "blt", "bgt", "ble", "cjne", "djnz", "jb", "jnb", "jbc", "jz", "jnz",
}


def _flow_kind(mnemonic: str) -> str:
    m = mnemonic.split(".")[0]
    if m in ("ret", "reti"):
        return "ret"
    if m in ("jmp", "br", "fjmp"):
        return "jump"
    if m in ("call", "fcall"):
        return "call"
    if m in _COND:
        return "cond"
    return "none"


def sweep(data, base: int = 0, start: int = 0, length: Optional[int] = None) -> List[dict]:
    """Linear disassembly. Returns a list of instruction records."""
    end = len(data) if length is None else min(len(data), start + length)
    pc = start
    out: List[dict] = []
    while pc < end:
        try:
            size, mnemonic, operands = decode(data, pc)
        except IndexError:                      # instruction truncated at EOF
            size, mnemonic, operands = 1, "?", [f"0x{data[pc]:02x}"]
        size = max(1, size)
        raw = bytes(data[pc:pc + size])
        out.append({
            "addr": base + pc,
            "bytes": " ".join(f"{b:02x}" for b in raw),
            "size": size,
            "mnemonic": mnemonic,
            "operands": operands,
            "flow": _flow_kind(mnemonic),
        })
        pc += size
    return out


def xrefs_to(insns: List[dict], target: int) -> List[dict]:
    """Instructions whose control-flow target equals `target`."""
    hits = []
    for i in insns:
        if i["flow"] in ("jump", "call", "cond"):
            for op in i["operands"]:
                if op.startswith("0x"):
                    try:
                        if int(op, 16) == target:
                            hits.append(i)
                            break
                    except ValueError:
                        pass
    return hits


def _cmd_xref(args) -> int:
    with open(args.file, "rb") as fh:
        data = fh.read()
    insns = sweep(data, args.base, args.start, args.len)
    hits = xrefs_to(insns, args.to)
    if args.json:
        json.dump(hits, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"# {len(hits)} reference(s) to 0x{args.to:x}")
        for i in hits:
            print(f"{i['addr']:06x}:  {i['mnemonic']:<8} {', '.join(i['operands'])}")
    return 0


def _cmd_disasm(args) -> int:
    with open(args.file, "rb") as fh:
        data = fh.read()
    insns = sweep(data, args.base, args.start, args.len)
    if args.json:
        json.dump(insns, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for i in insns:
            ops = ", ".join(i["operands"])
            print(f"{i['addr']:06x}:  {i['bytes']:<20}  {i['mnemonic']:<8} {ops}")
    return 0


def _int0(s: str) -> int:
    return int(s, 0)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="xa", description="Philips/NXP 80C51XA toolkit")
    p.add_argument("--version", action="version", version=f"xa-toolkit {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("disasm", help="linear disassembly of a binary")
    d.add_argument("file")
    d.add_argument("--base", type=_int0, default=0, help="load address for the address column")
    d.add_argument("--start", type=_int0, default=0, help="file offset to start at")
    d.add_argument("--len", type=_int0, default=None, help="number of bytes to decode")
    d.add_argument("--json", action="store_true", help="emit structured JSON (see AGENTS.md)")
    d.set_defaults(func=_cmd_disasm)

    x = sub.add_parser("xref", help="find control-flow references to an address")
    x.add_argument("file")
    x.add_argument("--to", type=_int0, required=True, help="target address to find references to")
    x.add_argument("--base", type=_int0, default=0)
    x.add_argument("--start", type=_int0, default=0)
    x.add_argument("--len", type=_int0, default=None)
    x.add_argument("--json", action="store_true")
    x.set_defaults(func=_cmd_xref)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
