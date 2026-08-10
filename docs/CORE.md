# HIPV core

`rtl/core/hipv_core.sv` connects the five pipeline stages and the hazard unit into the
complete RV32I core with two OBI master ports.

## Pipeline overview

```
        ┌─────┐      ┌─────┐      ┌─────┐      ┌─────┐      ┌─────┐
        │ IFU │─V/R─>│ IDU │─V/R─>│ IEU │─V/R─>│ LSU │─V/R─>│ WBU │
        │ (F) │      │ (D) │      │ (E) │      │ (M) │      │ (W) │
        └──┬──┘      └──┬──┘      └─┬─┬─┘      └─┬─┬─┘      └──┬──┘
           │OBI I       │regfile    │ │PCSrcE/   │ │OBI D      │RegWriteW/
           v            │write<─────┼─┼─PCTargetE│ │           │RdW/ResultW
        instruction     │port       │ └──> IFU,  │ v         (to IDU regfile
        memory          └───────────┼──────IDU   │ data       and hazard)
                                    │            │ memory
                                    │  ┌────────┐│
                     Rs1E/Rs2E ────>│  │ hazard ││<─ RdM, RegWriteM
                     ForwardAE/BE <─┼──│        ││<─ RdW, RegWriteW
                     ForwardDataM ──┘  └────────┘│
                     (from LSU) <────────────────┘
```

Every stage boundary is an elastic valid/ready handshake: a stage accepts a new
instruction when it is empty or being drained (`Ready = ~Valid | ReadyDownstream`).
Stalls propagate upstream automatically (a load in M back-pressures E, D, F), and
bubbles drain naturally. Control flow: `PCSrcE` (taken branch, `jal`, `jalr`) redirects
the IFU and flushes the IDU in the cycle the instruction leaves Execute.

Per-stage documentation: `IFU.md`, `IDU.md`, `IEU.md`, `LSU.md`, `WBU.md`,
`HAZARD.md`.

## ISA and interfaces

RV32I base integer ISA: ALU ops, loads/stores (byte/half/word, signed/unsigned),
branches, `jal`/`jalr`, `lui`/`auipc`. `fence`/`ecall`/CSRs decode as nops (no traps,
no interrupts yet). Reset vector 0x00000000.

Two OBI master ports (read-only subset on the instruction side):

| Port | Signals |
|------|---------|
| Instruction | `ObiIReq`, `ObiIGnt`, `ObiIAddr`, `ObiIRvalid`, `ObiIRdata` |
| Data        | `ObiDReq`, `ObiDGnt`, `ObiDAddr`, `ObiDWe`, `ObiDBe`, `ObiDWdata`, `ObiDRvalid`, `ObiDRdata` |

## Performance characteristics

With ideal memories the fetch FSM limits throughput to 1 instruction per 3 cycles
(no prefetch buffer yet); memory instructions add their bus latency in M. This is
deliberate: the core is correct and simple first, and the performance fixes (prefetch
buffer, overlapped fetch, store buffer, branch prediction) each make a self-contained
lecture with measurable speedup.

## Verification

`tb/core/test_hipv_core.py` runs whole programs from a Python OBI instruction memory
(encoders in `tb/common/rv32i.py`) and checks data-memory contents: dependent
arithmetic chains (forwarding), load-use sequences, taken/not-taken branch loops,
`jal`/`jalr` call and return, `lui`/`auipc`, byte/half accesses with sign extension,
and the same programs against slow memories. Run with `make` in `tb/core`.

Next steps toward the SoC: memory models in `rtl/mem/`, an OBI interconnect in
`rtl/interconnect/`, peripherals in `rtl/periph/`, and `rtl/top/hipv_soc.sv`.
