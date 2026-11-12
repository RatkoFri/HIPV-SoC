# IDU decode cheat sheet

Quick reference for how the D stage turns `InstrD` into control signals.
Sources: `rtl/core/idu/{idu,idudec,extend}.sv`, encodings in `config/hipv_pkg.sv`.

## 1. Instruction fields (`idu.sv`)

```
 31        25 24  20 19  15 14  12 11       7 6      0
 +-----------+------+------+------+----------+--------+
 |  funct7   | rs2  | rs1  |funct3|    rd    | opcode |   R-type
 +-----------+------+------+------+----------+--------+
```

| Signal      | Bits            | Used for                                   |
|-------------|-----------------|--------------------------------------------|
| `OpD`       | `InstrD[6:0]`   | main decoder select                        |
| `RdD`       | `InstrD[11:7]`  | destination register                       |
| `Funct3D`   | `InstrD[14:12]` | ALU decoder; passed to E/M (branch type, load/store size) |
| `Rs1D`      | `InstrD[19:15]` | regfile A1                                 |
| `Rs2D`      | `InstrD[24:20]` | regfile A2                                 |
| `Funct7b5D` | `InstrD[30]`    | ADD/SUB and SRL/SRA select (only bit of funct7 used) |
| `InstrD[31:7]` | -            | into `extend`                              |

## 2. Main decoder: opcode -> control word (`idudec.sv`)

Control word (15 bits), MSB first:
`{RegWrite, ImmSrc[2:0], ALUSrcA[1:0], ALUSrcB, MemWrite, ResultSrc[1:0], Branch, Jump, Jalr, ALUOp[1:0]}`

| Instr   | Opcode    | RegWrite | ImmSrc | ALUSrcA | ALUSrcB | MemWrite | ResultSrc | Branch | Jump | Jalr | ALUOp |
|---------|-----------|:--:|:--:|:----:|:--:|:--:|:----:|:--:|:--:|:--:|:--:|
| R-type  | `0110011` | 1 | I | RF   | 0 (RD2) | 0 | ALU | 0 | 0 | 0 | 10 |
| I-ALU   | `0010011` | 1 | I | RF   | 1 (imm) | 0 | ALU | 0 | 0 | 0 | 10 |
| load    | `0000011` | 1 | I | RF   | 1 | 0 | MEM | 0 | 0 | 0 | 00 |
| store   | `0100011` | 0 | S | RF   | 1 | 1 | ALU | 0 | 0 | 0 | 00 |
| branch  | `1100011` | 0 | B | RF   | 0 | 0 | ALU | 1 | 0 | 0 | 01 |
| jal     | `1101111` | 1 | J | RF   | 0 | 0 | PC4 | 0 | 1 | 0 | 00 |
| jalr    | `1100111` | 1 | I | RF   | 1 | 0 | PC4 | 0 | 0 | 1 | 00 |
| lui     | `0110111` | 1 | U | ZERO | 1 | 0 | ALU | 0 | 0 | 0 | 00 |
| auipc   | `0010111` | 1 | U | PC   | 1 | 0 | ALU | 0 | 0 | 0 | 00 |
| other (fence, ecall, csr, ...) | - | all zero -> nop (no illegal-instruction trap) |||||||||||

Notes:
- `jal` and branch targets use the dedicated PC + imm adder in Execute; `jalr` target = `rs1 + imm` on the ALU.
- `lui` = `0 + imm`; `auipc` = `PC + imm`.
- Control outputs are only meaningful when `ValidD = 1`; later stages must qualify side effects with it.

## 3. Select-signal encodings (`hipv_pkg.sv`)

| Signal       | Value | Meaning                       |
|--------------|:-----:|-------------------------------|
| `ImmSrcD`    | `000` / `001` / `010` / `011` / `100` | I / S / B / J / U |
| `ALUSrcAD`   | `00` / `01` / `10` | RF `RD1` / PC / zero      |
| `ALUSrcBD`   | `0` / `1`          | `RD2` / `ImmExtD`         |
| `ResultSrcD` | `00` / `01` / `10` | ALU / MEM / PC+4          |
| `ForwardAE/BE` (hazard unit) | `00` / `01` / `10` | D/E reg / `ResultW` / `ForwardDataM` |

## 4. ALU decoder: `ALUControlD`

If `ALUOp != 10` -> `ALU_ADD` (address / target computation; branch compare is not done through this path).

If `ALUOp == 10` (R-type, I-ALU):

| funct3 | Operation | `ALUControlD` | Condition                               |
|:------:|-----------|:-------------:|-----------------------------------------|
| `000`  | add / sub | `0000` / `0001` | `SUB` only if `InstrD[30] & OpD[5]` (R-type); `addi` never subtracts |
| `001`  | sll       | `0010` | |
| `010`  | slt       | `0011` | |
| `011`  | sltu      | `0100` | |
| `100`  | xor       | `0101` | |
| `101`  | srl / sra | `0110` / `0111` | `SRA` if `InstrD[30]` (both `sra` and `srai`) |
| `110`  | or        | `1000` | |
| `111`  | and       | `1001` | |

Why `OpD[5]` for sub: in `addi` with a negative immediate `InstrD[30]` is an immediate bit, not funct7. `OpD[5]` is 1 for R-type (`0110011`) and 0 for I-ALU (`0010011`). The shift case does not need it, because `slli/srli/srai` have a fixed funct7 and I-type immediates for shifts are 5 bits.

## 5. Immediate extension (`extend.sv`)

All immediates sign-extend from `InstrD[31]`.

| Format | `ImmExtD`                                                              | Used by |
|:------:|------------------------------------------------------------------------|---------|
| I | `{{20{i[31]}}, i[31:20]}`                                                   | I-ALU, load, jalr |
| S | `{{20{i[31]}}, i[31:25], i[11:7]}`                                          | store |
| B | `{{20{i[31]}}, i[7], i[30:25], i[11:8], 1'b0}`                              | branch |
| J | `{{12{i[31]}}, i[19:12], i[20], i[30:21], 1'b0}`                            | jal |
| U | `{i[31:12], 12'b0}`                                                         | lui, auipc |
| other | `32'b0`                                                                 | - |

(`i` = `InstrD`.) B and J immediates have an implicit bit 0 = 0.

## 6. Stage handshake and flush (`idu.sv`)

```
ReadyD = ~ValidDReg | ReadyE          // accept when empty or Execute is draining
EnFD   = ValidF & ReadyD              // F/D data registers load
ValidD = ValidDReg & ~PCSrcE          // taken branch/jump in E squashes the instr in D
ValidDReg <= ValidF  (when ReadyD)    // reset -> 0
```

- Backpressure (`ReadyE = 0`) holds the instruction in D and stalls `ReadyD`.
- `PCSrcE` gates `ValidD` combinationally; the bubble is committed at the next edge via `ValidF` (gated by `PCSrcE` in `ifuctrl`).

## 7. Register file (`regfile.sv`)

- 32 x 32, two combinational read ports (`Rs1D`, `Rs2D`), one write port from W (`RegWriteW`, `RdW`, `ResultW`).
- x0 reads as zero and ignores writes.
- Write-first: a same-cycle write from W is bypassed to `RD1D`/`RD2D`, so no extra WB->D forwarding is needed.
- Array is not reset.

## 8. Worked examples

### 8.1 `addi x5, x1, -4`

`addi x5, x1, -4` = `0xFFC08293`

| Field | Value | Decode |
|-------|-------|--------|
| opcode `[6:0]` | `0010011` | I-ALU -> RegWrite=1, ImmSrc=I, SrcA=RF, SrcB=imm, ResultSrc=ALU, ALUOp=10 |
| rd `[11:7]` | 5 | `RdD` |
| funct3 `[14:12]` | `000` | add/sub branch |
| rs1 `[19:15]` | 1 | `Rs1D` |
| imm `[31:20]` | `0xFFC` | `ImmExtD = 0xFFFFFFFC` |
| `InstrD[30]` | 1 | ignored for sub, because `OpD[5] = 0` -> `ALUControlD = ADD` |

### 8.2 `sw x6, 8(x2)` = `0x00612423`

| Field | Value | Decode |
|-------|-------|--------|
| opcode `[6:0]` | `0100011` | store -> RegWrite=0, ImmSrc=S, SrcA=RF, SrcB=imm, MemWrite=1, ResultSrc=ALU, ALUOp=00 |
| imm[4:0] `[11:7]` | `01000` | low part of the offset (not `RdD`; it is unused because RegWrite=0) |
| funct3 `[14:12]` | `010` | word access (size passed on as `Funct3D`) |
| rs1 `[19:15]` | 2 | `Rs1D` = base address register |
| rs2 `[24:20]` | 6 | `Rs2D` = store data register |
| imm[11:5] `[31:25]` | `0000000` | high part of the offset |
| `ImmExtD` | `{{20{i[31]}}, i[31:25], i[11:7]}` = `0x00000008` | S format |
| `ALUControlD` | `ALU_ADD` | `ALUOp != 10`, so address = `rs1 + imm` |
