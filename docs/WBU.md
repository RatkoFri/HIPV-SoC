# WBU — Writeback Unit (W stage)

The WBU holds the M/W pipeline register and selects the value written back to the
register file: ALU result, load data, or PC+4 (for `jal`/`jalr` link). File:
`rtl/core/wbu/wbu.sv`. Testbench: `tb/unit/wbu/`.

## Operation

Writeback never stalls: `ReadyW = 1` constantly, and the valid bit simply tracks
whether a real instruction arrived from M. `ResultW` is selected by `ResultSrcW`
through a `mux3` (`RESULT_ALU`/`RESULT_MEM`/`RESULT_PC4`).

`RegWriteW` is qualified with the stage valid bit, so bubbles and non-writing
instructions never touch the register file. `RegWriteW`, `RdW` and `ResultW` drive
the register file write port in the Decode stage directly (the regfile's write-first
bypass makes a same-cycle write visible to the instruction currently decoding) and
feed the hazard unit for W-stage forwarding.

## Verification

`tb/unit/wbu/test_wbu.py` checks all three result selections and that `RegWriteW`
stays low for bubbles and for valid instructions with `RegWriteM = 0`.
