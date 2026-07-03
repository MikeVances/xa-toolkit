# Credits & provenance

## Clean-room basis

The instruction decoder in `xa_toolkit/isa.py` and `xa_toolkit/disasm.py` is a **clean-room
implementation** derived solely from public Philips/NXP documentation:

- *Philips XA User Guide* (Philips Semiconductors, 1997/1998)
- *80C51XA (IC25) datasheet* (Philips Semiconductors, 1997)

Instruction encodings, mnemonics, register names and addressing modes are **factual ISA data**
published by the vendor and are not, in themselves, copyrightable. No proprietary SDK source
was copied into this project.

## Acknowledgement — Petr Novak

**Petr Novak** authored the original XA processor module for IDA and was, as far as we know, the
first person to publicly map the 80C51XA instruction set for a disassembler. His work is
gratefully acknowledged. This project does not include his code; licensing/attribution
discussion is in progress. If you are Petr (or know how to reach him), please open an issue.

## Not included

- No vendor firmware images (`*.bin` / `*.hex`).
- No third-party datasheet PDFs (link to the vendor documents instead).
- No IDA SDK or IDA-module source.
