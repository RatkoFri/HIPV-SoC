# Hazard unit

Pure combinational forwarding for the Execute-stage operands. File:
`rtl/core/hazard/hazard.sv`. Testbench: `tb/unit/hazard/`.

## Forwarding rules

For each operand (`Rs1E` → `ForwardAE`, `Rs2E` → `ForwardBE`), priority order:

1. `FWD_MEM` if the instruction in M writes the register (`RegWriteM & RdM == Rs`) —
   the newest value, taken from `ForwardDataM` (ALU result, or load data for loads);
2. `FWD_WB` if the instruction in W writes it (`RegWriteW & RdW == Rs`) — `ResultW`;
3. `FWD_RF` otherwise — the value read from the register file in Decode.

x0 is never forwarded. The `RegWriteM`/`RegWriteW` inputs are already qualified with
the stage valid bits by the LSU and WBU, so bubbles never match.

## Why there is no stall logic

The classic 5-stage design needs a dedicated load-use stall (`lwstall`) because the
load data only exists one stage later than the dependent instruction needs it. In
HIPV the elastic valid/ready handshake absorbs this case naturally:

- A load holds the Memory stage until its OBI response arrives (`ReadyM = 0`), so a
  dependent instruction simply waits in Execute.
- When the data arrives, `ForwardDataM` carries the load data (not the address), and
  the dependent instruction proceeds with the forwarded value in the same cycle the
  load moves to W.
- A branch whose operands are not yet resolved cannot fire a wrong redirect, because
  `PCSrcE` is gated with `ReadyM` (the redirect fires only in the retire cycle).

The remaining hazard — an instruction in Decode reading a register while its producer
retires — is covered by the register file's write-first bypass (see `docs/IDU.md`).

One more case needs care: **forwarding while Execute stalls**. An instruction can wait in
Execute for several cycles: behind a load or store that holds the Memory stage, or
during a multi-cycle operation. Meanwhile its producer can move from W out of the
pipeline. From then on nothing forwards that value, and the register value captured in
Decode is stale, because it was read before the producer wrote it. Example, with a slow
data memory:

```
lw   x5, 0(x10)    # slow: the next instructions bunch up behind it
addi x1, x0, 77    # producer
sw   x5, 4(x10)    # holds M while addi passes through W and retires
add  x3, x1, x0    # waits in E; x1 is forwarded from W for one cycle only
```

The IEU therefore refreshes its D/E operand registers (`RD1E`, `RD2E`) with the
forwarded values (`FwdAE`, `WriteDataE`) in every cycle the instruction is held
(`HoldE = ValidEReg & ~ReadyE`). Whatever was forwarded last before the producer
retired is kept. A value forwarded from a load that hasn't finished yet is
overwritten by a later refresh, once the data is there. `tb/core` test
`test_forward_while_stalled` covers this case.

## Verification

`tb/unit/hazard/test_hazard.py` checks: no-dependency defaults, M and W matches on
both operands, M-over-W priority, suppression when `RegWrite` is low, and the x0
exclusion. The pipeline-level behavior (load-use, back-to-back dependencies) is
exercised by the programs in `tb/core/`.
