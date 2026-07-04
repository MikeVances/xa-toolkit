"""Tests for the linear-sweep CLI backend."""
from xa_toolkit.cli import sweep


def test_sweep_basic():
    # ADD.w R1,R2 (09 12) ; BR +0 (FE 00) ; RET (D6 80)
    data = bytes([0x09, 0x12, 0xFE, 0x00, 0xD6, 0x80])
    insns = sweep(data)
    assert [i["mnemonic"] for i in insns] == ["add.w", "br", "ret"]
    assert [i["addr"] for i in insns] == [0, 2, 4]
    assert insns[1]["flow"] == "jump"
    assert insns[2]["flow"] == "ret"


def test_sweep_base_and_fields():
    insns = sweep(bytes([0xD6, 0x80]), base=0x1000)
    assert insns[0]["addr"] == 0x1000
    assert insns[0]["bytes"] == "d6 80"
    assert insns[0]["size"] == 2


def test_sweep_unknown_advances_one_byte():
    insns = sweep(bytes([0xE0, 0x00]))   # 0xE0 not decoded -> "?" size 1
    assert insns[0]["mnemonic"] == "?"
    assert insns[0]["size"] == 1
    assert len(insns) == 2               # swept byte-by-byte, no infinite loop


def test_sweep_cond_flow_classified():
    insns = sweep(bytes([0xF0, 0x02]))   # BCC
    assert insns[0]["flow"] == "cond"


def test_xref():
    from xa_toolkit.cli import xrefs_to
    # BR +2 at 0 -> target 0+2+2*2 = 6 ; then NOPs
    data = bytes([0xFE, 0x02, 0x00, 0x00, 0x00, 0x00])
    insns = sweep(data)
    hits = xrefs_to(insns, 0x6)
    assert len(hits) == 1
    assert hits[0]["mnemonic"] == "br"
    assert xrefs_to(insns, 0x100) == []
