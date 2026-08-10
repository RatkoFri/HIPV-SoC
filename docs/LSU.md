# LSU — Load/Store Unit (M stage)

The LSU holds the E/M pipeline register and executes memory accesses over the OBI data
port. Non-memory instructions pass through in a single cycle; loads and stores run one
OBI transaction and hold the stage (`ReadyM = 0` toward Execute) until the response
arrives. File: `rtl/core/lsu/lsu.sv`. Testbench: `tb/unit/lsu/`.

## Ports (summary)

Execute side: `ValidE`/`ReadyM` handshake with payload `ALUResultE` (address or
result), `WriteDataE` (store data), `PCPlus4E`, `RdE`, `Funct3E`, `RegWriteE`,
`MemWriteE`, `ResultSrcE`. Writeback side: `ValidM`/`ReadyW` with `ALUResultM`,
`ReadDataM`, `PCPlus4M`, `RdM`, `RegWriteM` (valid-qualified), `ResultSrcM`.
Forwarding: `ForwardDataM`. OBI data port: `ObiReqM/ObiGntM/ObiAddrM/ObiWeM/ObiBeM/
ObiWdataM/ObiRvalidM/ObiRdataM`.

## Operation

`MemOpM = MemWriteM | (ResultSrcM == RESULT_MEM)` marks a memory instruction. The
stage presents `ValidM = ValidMReg & (~MemOpM | DoneM)`: pass-through for non-memory
instructions, completion-gated for memory ones. `ReadyM = ~ValidMReg | (ValidM &
ReadyW)`, so the Execute stage is back-pressured for exactly the duration of the bus
access — this is what makes a dedicated load-use stall unnecessary (see
`docs/HAZARD.md`).

The OBI transaction control is two flags: `WaitRespM` (between grant and rvalid) and
`DoneM` (response consumed, cleared when the next instruction loads). One transaction
per instruction, one outstanding at most.

## Alignment and sizes

The address sent on the bus is word-aligned (`ObiAddrM = {addr[31:2], 2'b00}`); the
byte offset selects the byte enables (`sb`: one-hot, `sh`: half, `sw`: all four) and
shifts the store data. Read data is shifted back by the offset and sign/zero extended
by funct3 (`lb`/`lh` signed, `lbu`/`lhu` unsigned, `lw` raw).

`ForwardDataM` is the load data for loads and the ALU result otherwise, so the
forwarding mux in Execute always receives the architecturally correct M-stage value.

## Known simplifications

Misaligned accesses are not detected (no traps); a halfword crossing a word boundary
is silently truncated to the addressed word. No write buffer: a store occupies the
stage until its OBI response. Both are candidate lecture extensions.

## Verification

`tb/unit/lsu/test_lsu.py` uses the shared OBI slave model (`tb/common/obi.py`) and
checks: single-cycle pass-through, word stores, byte/halfword stores with merge into
the existing word, all five load types with offsets and sign extension, `ReadyM`
back-pressure during a slow transaction, and holding under `ReadyW = 0`.
