# IEU — Integer Execution Unit (E stage)

The IEU receives operands and control from the IDU through a valid/ready handshake into
the D/E pipeline register, selects ALU operands through the forwarding and source
muxes, executes the ALU operation, evaluates branch conditions and computes the
branch/jump target. It drives the redirect (`PCSrcE`/`PCTargetE`) consumed by the IFU
(next PC) and the IDU (flush), and passes results toward the Memory stage.

Files: `rtl/core/ieu/ieu.sv` (structural stage), `rtl/core/ieu/alu.sv`,
`rtl/core/ieu/branchcmp.sv` (behavioral leaf cells). Testbench: `tb/unit/ieu/`.

## Block diagram

```
              ┌────────────┐ RD1E ┌─────────┐ FwdAE  ┌─────────┐ SrcAE
 from IDU ───>│  D/E regs  │─────>│ fwdamux │───────>│ srcamux │──────┐
 (operands,   │ (flopenr,  │ RD2E │ (mux3)  │   PCE ─>│ (mux3)  │      v
  controls,   │ valid bit) │──┐   └─────────┘  zero ─>└─────────┘   ┌─────┐
  ValidD/     └────────────┘  │        ^ ForwardAE                  │ alu │─> ALUResultE
  ReadyE)          │          v   ResultW/ForwardDataM              └─────┘
                   │   ┌─────────┐ WriteDataE ┌─────────┐ SrcBE        ^
                   │   │ fwdbmux │──────┬────>│ srcbmux │──────────────┘
                   │   │ (mux3)  │      │     │ (mux2)  │<── ImmExtE
                   │   └─────────┘      │     └─────────┘
                   │        FwdAE ──┐   │
                   │                v   v
                   │           ┌───────────┐           ┌──────────────────────┐
                   │           │ branchcmp │─ TakenE ─>│ PCSrcE = Valid &     │
                   │           └───────────┘           │  (Jump|Jalr|Br&Taken)│
                   │  PCE ──> ┌───────────┐            └──────────────────────┘
                   │  ImmExtE>│ targetadd │─┐ ┌──────────┐
                   │          └───────────┘ └>│targetmux │──> PCTargetE
                   │     {ALUResultE[31:1],0}>│ (mux2)   │   (jalr selects ALU)
                   │                          └──────────┘
```

## Ports (summary)

- Decode side:  `ValidD`/`ReadyE` handshake plus all D-stage outputs (operands, register
specifiers, controls — see `docs/IDU.md`). 
- Memory side: `ValidE`/`ReadyM` handshake and
the stage payload `ALUResultE`, `WriteDataE` (forwarded rs2, store data), `PCPlus4E`,
`RdE`, `Funct3E`, `RegWriteE`, `MemWriteE`, `ResultSrcE`. 
- Hazard-unit side:
`ForwardAE`/`ForwardBE` selects with `ForwardDataM` and `ResultW` data inputs, and
`Rs1E`/`Rs2E` exported for the forwarding decision. 
- Redirect: `PCSrcE`, `PCTargetE`.

## Operand selection

Two mux levels per operand, in `hipv_pkg` encodings:

1. Forwarding (`ForwardAE`/`ForwardBE`): `FWD_RF` = D/E register operand, `FWD_WB` =
   `ResultW`, `FWD_MEM` = `ForwardDataM`. Until the hazard unit exists, tie both to
   `FWD_RF`.
2. Source (`ALUSrcAE`: rs1/PC/zero for auipc/lui; `ALUSrcBE`: rs2/immediate).

The branch comparator uses the *forwarded* operands (`FwdAE`, `WriteDataE`), not the
ALU sources, so comparisons see forwarded values while the ALU is free to compute with
PC/immediate. `WriteDataE` doubles as the store-data output to the Memory stage.

## Branches and jumps

`branchcmp` evaluates all six RV32I conditions by funct3. Targets: branch and `jal` use
the dedicated `PCE + ImmExtE` adder; `jalr` selects the ALU result (`rs1 + imm`) with
bit 0 cleared, per the ISA. `PCSrcE = ValidE & ReadyM & (JumpE | JalrE | (BranchE & TakenE))` —
qualified by the valid bit so a drained pipeline never redirects, and gated with
`ReadyM` so the redirect fires exactly in the cycle the instruction leaves E. While the
Memory stage stalls (a load in flight), forwarded operands may not be resolved yet, so
a branch must not fire until it can actually retire.

## Handshake

Same elastic pattern as F/D: `ReadyE = ~ValidEReg | ReadyM`, load on `ValidD & ReadyE`.
The E stage is never flushed: the redirect kills instructions *behind* the branch (in F
and D), while the branch itself continues into the Memory stage to retire.

## Verification

`tb/unit/ieu/test_ieu.py` drives the Decode-side inputs directly and checks: all ten
ALU operations (including signed/unsigned compares and arithmetic shift of a negative
value), all six branch conditions taken and not taken plus the target address and the
no-fire check after draining, `jal`/`jalr` targets (LSB clearing), `lui`/`auipc`
operand selection, A- and B-path forwarding from both `ResultW` and `ForwardDataM`,
backpressure holding, and bubble draining. Run with `make` in `tb/unit/ieu`.
