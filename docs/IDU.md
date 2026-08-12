# IDU — Instruction Decode Unit (D stage)

The IDU receives fetched instructions from the IFU through a valid/ready handshake,
holds them in the F/D pipeline register, decodes them into control signals, reads the
register file and extends the immediate. Its outputs feed the Execute stage through a
`ValidD`/`ReadyE` handshake.

Files: 
- `rtl/core/idu/idu.sv` (structural stage), `rtl/core/idu/idudec.sv` (behavioral
control decoder)
- `rtl/core/idu/extend.sv` (immediate extension),
- `rtl/core/regfile/regfile.sv` (register file). 
- Shared encodings:
`config/hipv_pkg.sv`. 

Testbench: `tb/unit/idu/`.

## Block diagram

```
 ValidF ──┐  ┌─────────────┐
 InstrF ──┼─>│  F/D regs   │── InstrD ──┬──> fields: Rs1D, Rs2D, RdD, Funct3D
 PCF ─────┼─>│ (flopenr ×3 │            ├──> idudec ──> controls (RegWriteD, ...)
 PCPlus4F ┼─>│  + valid    │            └──> extend ──> ImmExtD
 ReadyD <─┘  │    bit)     │── PCD, PCPlus4D ──>
 PCSrcE ────>└─────────────┘
                  Rs1D/Rs2D ──> regfile (A1/A2) ──> RD1D, RD2D
    RegWriteW/RdW/ResultW ────> regfile (WE3/A3/WD3)   [from Writeback]
```

## Ports

| Port                    | Dir | Width | Description                                  |
|-------------------------|-----|-------|----------------------------------------------|
| `clk`, `reset`          | in  | 1     | Clock, synchronous active-high reset         |
| `ValidF` / `ReadyD`     | in/out | 1  | Handshake with Fetch                         |
| `InstrF`, `PCF`, `PCPlus4F` | in | 32 | Fetch stage payload                          |
| `PCSrcE`                | in  | 1     | Flush: taken branch/jump resolved in Execute |
| `ValidD` / `ReadyE`     | out/in | 1  | Handshake with Execute                       |
| `RegWriteW`, `RdW`, `ResultW` | in | 1/5/32 | Register file write port from Writeback |
| `RD1D`, `RD2D`          | out | 32    | Register operands                            |
| `ImmExtD`               | out | 32    | Extended immediate                           |
| `PCD`, `PCPlus4D`       | out | 32    | PC and PC+4 of the instruction in D          |
| `Rs1D`, `Rs2D`, `RdD`   | out | 5     | Register specifiers                          |
| `Funct3D`               | out | 3     | funct3 (branch type / load-store size)       |
| `RegWriteD`, `MemWriteD`, `BranchD`, `JumpD`, `JalrD` | out | 1 | Control flags |
| `ResultSrcD`            | out | 2     | Writeback select: ALU / MEM / PC+4           |
| `ALUSrcAD`              | out | 2     | ALU operand A: RD1 / PC / zero               |
| `ALUSrcBD`              | out | 1     | ALU operand B: RD2 / immediate               |
| `ALUControlD`           | out | 4     | ALU operation (`hipv_pkg` encoding)          |

## Handshake and flush

The F/D register is an elastic pipeline stage: `ReadyD = ~ValidDReg | ReadyE`
(accept when empty or when Execute is draining the current instruction), data registers
load on `ValidF & ReadyD`, and the valid bit tracks whether the stage holds a real
instruction. `PCSrcE` gates `ValidD` off combinationally and clears the valid bit at
the next edge, turning the wrong-path instruction into a bubble.

Control outputs are only meaningful when `ValidD` is high; later stages must qualify
side effects (register/memory writes) with the valid bit.

## Decoder

The main decoder (case on opcode) produces a 15-bit control word; the ALU decoder
refines `ALUControlD` from funct3/funct7 when `ALUOp = 10` (R-type and I-type ALU).
All ten RV32I ALU operations are supported. Design choices:

- `jalr` computes its target on the ALU (`rs1 + imm`, `ALUControlD = ADD`); branch and
  `jal` targets use the dedicated PC + imm adder in Execute.
- `lui` is `0 + imm` (`ALUSrcA = zero`), `auipc` is `PC + imm` (`ALUSrcA = PC`).
- Unimplemented opcodes (`fence`, `ecall`/`csr`, ...) decode to an all-zero control
  word and pass through as a nop — no illegal-instruction trap yet.

## Register file

32 × 32 bit, two combinational read ports, one synchronous write port driven by the
Writeback stage. x0 reads as zero and ignores writes. The read ports are write-first:
a same-cycle write from W is bypassed to the read outputs, which removes the classic
"read-during-writeback" hazard without an extra forwarding path. The array itself is
not reset.

## Verification

`tb/unit/idu/test_idu.py` encodes RV32I instructions in Python and checks: field
slicing and immediates for all five formats, `ALUControlD` for all R-type and I-type
shift operations, load/store/branch/jal/jalr/lui/auipc control words, register file
write→read, x0 behavior, write-first bypass, flush on `PCSrcE`, and backpressure
(`ReadyE = 0` holds the instruction and stalls `ReadyD`). Run with `make` in
`tb/unit/idu` (see `tb/unit/ifu/README.md` for the common options: `WAVES=1`,
`SIM_BUILD=`, `TESTCASE=`).
