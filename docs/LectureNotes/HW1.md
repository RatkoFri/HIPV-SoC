# Homework 1: Extending the HIPV core

HIPV implements the RV32I base ISA. In this homework you add two standard RISC-V
extensions to the core:

- **Task 1** adds a subset of the bit-manipulation extensions **Zba** and **Zbb**. These
  are single-cycle instructions, and the work is in the decoder and the ALU.
- **Task 2** adds **Zmmul**, the multiply half of the M extension. It is built from a
  single 16×16 multiplier, so a multiply takes several cycles and has to stall the
  pipeline.

Do the tasks in order. Task 2 relies on the decoder changes you make in Task 1.

An optional extension of this homework is described separately in
[HW1_bonus.md](HW1_bonus.md).

## Learning goals

After this homework you can:

- read an instruction encoding from the ISA specification and decode it without
  breaking the instructions that share its opcode;
- extend a datapath while reusing existing hardware where possible;
- build a multi-cycle functional unit and connect it to an elastic (valid/ready)
  pipeline;
- reason about when forwarded operands are valid;
- verify your design at three levels (a single module, the core, software on the SoC)
  and measure its cost and benefit.

## Before you start

**Branch.** Work on the `hw1` branch. It contains everything listed under "What is
provided".

**Tools.**

| Tool | Version | Notes |
|---|---|---|
| Verilator | ≥ 5.036 | |
| cocotb | 2.x | `pip install -r requirements.txt` |
| RISC-V GCC | recent | Tested with `riscv64-unknown-elf-gcc` 15.2. Needs `.option arch` support in the assembler. |

**Reading.**

- [CORE.md](../CORE.md), [IDU.md](../IDU.md), [IEU.md](../IEU.md) and
  [HAZARD.md](../HAZARD.md): how the pipeline, the handshake and forwarding work.
- [NamingConvention.md](../../NamingConvention.md): your RTL is graded against it.
- The RISC-V Unprivileged ISA specification
  ([releases](https://github.com/riscv/riscv-isa-manual/releases)): the chapter on the
  B extension (Zba, Zbb) and the chapter on the M extension (Zmmul).

**Check your setup.** Before you change anything, run the existing testbenches (see
[Testbenches](#testbenches)). They must pass:

```sh
cd tb/core && make
cd tb/unit/idu && make
cd tb/unit/ieu && make
```

## What is provided

| File | What it is |
|---|---|
| [tb/common/rv32i.py](../../tb/common/rv32i.py) | Python encoders for all homework instructions (`andn`, `clz`, `mul`, ...) and `li` for 32-bit constants |
| [tb/common/hw1_model.py](../../tb/common/hw1_model.py) | Python reference model of every homework instruction |
| [rtl/core/ieu/mul.sv](../../rtl/core/ieu/mul.sv) | Task 2 skeleton with the **fixed interface** of the multiplier |
| [rtl/core/ieu/mulctrl.sv](../../rtl/core/ieu/mulctrl.sv) | Task 2 skeleton for the multiplier's control unit |
| [tb/unit/mul/](../../tb/unit/mul/) | Testbench for the `mul` module |
| [tb/core/test_zbb.py](../../tb/core/test_zbb.py), [tb/core/test_zmmul.py](../../tb/core/test_zmmul.py) | Testbenches for the whole pipeline, Task 1 and Task 2 |
| [sw/hw1/check/](../../sw/hw1/check/) | Self-checking C program for both tasks, run on the SoC |
| [sw/hw1/bench/](../../sw/hw1/bench/) | Benchmark comparing the new instructions with RV32I code |
| [sw/hw1/hw1_insn.h](../../sw/hw1/hw1_insn.h) | Inline-assembly wrappers for the new instructions |

### Where to change the code

Every place you have to change is marked in the source with a comment starting with
`HW1 Task 1` or `HW1 Task 2`. The comments say *where* to work, not *what* to write.
List them with:

```sh
grep -rn "HW1 Task" config rtl
```

| File | Task | What happens there |
|---|---|---|
| [config/hipv_pkg.sv](../../config/hipv_pkg.sv) | 1 | ALU operation codes |
| [rtl/core/idu/idudec.sv](../../rtl/core/idu/idudec.sv) | 1, 2 | decoder inputs, a multiply control output, the main decoder (multiply, divide), the ALU decoder (Zba/Zbb) |
| [rtl/core/idu/idu.sv](../../rtl/core/idu/idu.sv) | 1, 2 | the bits passed to the decoder, the new outputs of the Decode stage |
| [rtl/core/ieu/alu.sv](../../rtl/core/ieu/alu.sv) | 1 | the Zba/Zbb operations |
| [rtl/core/ieu/ieu.sv](../../rtl/core/ieu/ieu.sv) | 1, 2 | the new inputs, the D/E control register, the handshake (`ReadyE`/`ValidE`), the multiplier instance and its result |
| [rtl/core/hipv_core.sv](../../rtl/core/hipv_core.sv) | 1, 2 | the wires between `idu` and `ieu` |
| [rtl/core/ieu/mul.sv](../../rtl/core/ieu/mul.sv) | 2 | the multiplier datapath (new) |
| [rtl/core/ieu/mulctrl.sv](../../rtl/core/ieu/mulctrl.sv) | 2 | the multiplier state machine (new) |

`mul.sv` and `mulctrl.sv` are already listed in every testbench Makefile and in the
FPGA flow. If you add another RTL file, add it to the `VERILOG_SOURCES` of
`tb/unit/ieu`, `tb/unit/mul`, `tb/core`, `tb/soc` and `tb/fpga`, and to
`scripts/anvil_flow.py`.

---

## Testbenches

HIPV is verified with [cocotb](https://www.cocotb.org) and Verilator: the design is
simulated by Verilator, and the test itself is a Python program that drives the
design's inputs and checks its outputs. Each directory under `tb/` is one testbench:

- a `Makefile`, which says which RTL files to compile and which module is the top
  (`TOPLEVEL`);
- one or more `test_*.py` files, each holding several tests (Python functions marked
  `@cocotb.test()`).

Run a testbench with `make` in its directory. Useful options:

| Option | Effect |
|---|---|
| `TESTCASE=<name>` | run only one test |
| `WAVES=1` | write a waveform, `dump.vcd` |
| `SIM_BUILD=/tmp/sb` | build outside the repository (needed on cloud-synced drives) |

The homework uses testbenches at three levels. The level tells you **what is
simulated** and **what plays the rest of the world**.

| Level | Directory | Simulated RTL | The testbench plays |
|---|---|---|---|
| **Unit** | `tb/unit/<module>` | one module (`mul`, `idu`, `ieu`, ...) | the modules around it: it drives every input port directly, cycle by cycle |
| **Core** | `tb/core` | the CPU pipeline `hipv_core` only: fetch, decode, execute, memory, writeback, forwarding. No RAM, bus or peripherals. | the two memories: Python models of an instruction and a data memory on the core's OBI bus ports, with configurable wait states |
| **SoC** | `tb/soc` (via `make run` in `sw/`) | the complete system `hipv_soc`: core, crossbar, RAM, UART, timer, GPIO | the outside world: it loads a compiled C program into the RAM and decodes the characters the program prints on the UART pin |

A failure at a lower level is easier to debug: the unit testbench points straight at
one module, while a failed SoC test only tells you the printed text was wrong. Work
upwards: unit first, then core, then SoC.

### Unit level: `tb/unit/mul` (Task 2)

Toplevel: your `mul` module alone. The testbench plays the Execute stage. It pulses
`Start` with the operands, waits for `Done`, then raises `Ack`. Every result is compared
with `hw1_model.py`.

To check the interface contract in the header of `mul.sv`, the testbench does two
things on every operation:

- it drives **random values on `A`, `B` and `Funct3` after the `Start` cycle**, so a unit
  that does not capture its operands fails;
- it checks that `Busy`, `Done` and `Result` follow the contract.

| Test | What it checks |
|---|---|
| `test_edge_cases` | all four instructions on 12×12 operands chosen to break naive designs: 0, 1, all ones, `0x80000000`, `0x7FFFFFFF`, values on the 16-bit seam such as `0x0000FFFF` and `0x00010000` |
| `test_random` | 400 random operations; `Ack` is delayed by 0–3 cycles, and `Done`/`Result` must hold steady meanwhile |
| `test_latency` | logs the `Start → Done` latency of each instruction (record it for the report); fails if it exceeds 8 cycles |
| `test_back_to_back` | a new `Start` in the cycle right after `Ack` |

```sh
cd tb/unit/mul && make
```

### Unit level: `tb/unit/idu` and `tb/unit/ieu` (existing, regression)

These test the Decode and Execute stages as they were before the homework. You will
change both modules, and these tests **must keep passing**: they check that the RV32I
behavior is unchanged. They write the existing `ALUControl` codes as numbers, so keep
those codes unchanged (see Task 1).

- `tb/unit/idu`: field extraction, decoding of every RV32I instruction class, register
  file read/write and bypass, flush, back-pressure.
- `tb/unit/ieu`: all ten ALU operations, branch conditions and targets, `jal`/`jalr`,
  `lui`/`auipc`, forwarding selection, back-pressure, bubbles.

### Core level: `tb/core`

Toplevel: `hipv_core`, the pipeline without the SoC around it. Each test:

1. builds a short program in Python with the encoders in `rv32i.py`
   (`li(1, 0x80000000)`, `andn(3, 1, 2)`, `sw(3, 0, 10)`, ...);
2. places it in the Python instruction memory and runs the core for a fixed number of
   cycles;
3. checks the values the program stored in the Python data memory against
   `hw1_model.py`.

A failure prints the instruction, its operands, the stored value and the expected value,
for example `andn(0x00000001, 0x00000000) = 0x00000000, expected 0x00000001`. "Never
written" means the store never happened; usually the pipeline hung, or the store went
to the wrong address.

The Makefile selects the test file with `MODULE`:

| Command | File | Contents |
|---|---|---|
| `make` | `test_hipv_core.py` | the existing RV32I tests (regression): forwarding, load-use, branches, calls, byte/half accesses, slow memories, forwarding while Execute stalls |
| `make MODULE=test_zbb` | `test_zbb.py` | Task 1 |
| `make MODULE=test_zmmul` | `test_zmmul.py` | Task 2 |

**`test_zbb.py` (Task 1)**

| Test | What it checks |
|---|---|
| `test_zba` | `sh1add`, `sh2add`, `sh3add` on 12×4 edge-case pairs plus random pairs |
| `test_logic_with_negate` | `andn`, `orn`, `xnor` on the same pairs |
| `test_min_max` | `min`, `minu`, `max`, `maxu`; the pairs include operands where signed and unsigned order differ |
| `test_clz_cpop` | `clz` and `cpop` on 0, all ones, every single-bit value and random values |
| `test_forwarding_chain` | six new instructions in a row, each using the previous result (forwarding into and out of the new operations) |
| `test_rv32i_still_works` | the RV32I instructions that share encodings with the new ones: `add`, `sub`, `xor`, `sll`/`srl`/`sra`, `slli`/`srli`/`srai`, `andi`, `ori` |

**`test_zmmul.py` (Task 2)**

| Test | What it checks |
|---|---|
| `test_mul_edge` | all four instructions on edge-case operand pairs |
| `test_mul_random` | all four instructions on random pairs |
| `test_mul_dependencies` | a multiply using the result of the previous multiply, an ALU instruction using multiply results, a multiply using an ALU result, a store of a multiply result |
| `test_mul_after_load_slow_memory` | multiplies whose operands come from loads that are **still waiting for a slow data memory** while instruction fetch is fast. This is the case behind "When may the multiplier start?" (Task 2). |
| `test_mul_and_branches` | a branch on a multiply result, and a multiply on a branch path that is skipped (it must not write its register) |
| `test_back_to_back` | six independent multiplies in a row |
| `test_div_rem_are_nops` | `div`, `divu`, `rem`, `remu` must leave their destination register unchanged |

### SoC level: `sw/hw1/check` and `sw/hw1/bench`

Toplevel: `hipv_soc`, the complete system. `make run` in a program directory compiles
the C program, loads the binary into the SoC's RAM, simulates the whole system and
captures everything the program prints on the UART (`tb/soc/test_sw.py`).

- **`sw/hw1/check`** is self-checking. Every instruction runs on all pairs of 12 operands
  and is compared with a reference written in plain RV32I C, so the reference does not
  depend on your hardware. The run passes if the printed text matches
  `expected.txt` exactly. A failing line shows how many results were wrong and the
  first one:

  ```
  sh1add  OK
  min     FAIL 23/144  a=80000000 b=00000001 hw=00000001 ref=80000000
  ```

- **`sw/hw1/bench`** prints a table and does not check anything (see
  [Software on the SoC](#software-on-the-soc)).

A run simulates 4 million cycles and takes about half a minute.

### Existing SoC and FPGA testbenches (regression)

`tb/soc` (with plain `make`: a small assembly program exercising every peripheral) and
`tb/fpga` (the board wrapper) must still pass at the end. They don't test the new
instructions; they show you haven't broken the system.

### Hidden tests

The provided tests are a good start, not the whole story. Your design is also graded with
**additional hidden tests of the same kind and at the same levels**: more operand
values, other instruction sequences, other memory timings. Write your own tests for the
corner cases you can think of (see [Rules](#rules)).

---

## Task 1: Zba/Zbb subset

### Instructions

All instructions write `rd`. `rs1` and `rs2` are the register operands. R-type
instructions use opcode `OP` (`0110011`), the others use `OP-IMM` (`0010011`).

| Instruction | Ext. | Opcode | funct7 | rs2 field | funct3 | Operation |
|---|---|---|---|---|---|---|
| `sh1add` | Zba | OP | `0010000` | rs2 | `010` | `(rs1 << 1) + rs2` |
| `sh2add` | Zba | OP | `0010000` | rs2 | `100` | `(rs1 << 2) + rs2` |
| `sh3add` | Zba | OP | `0010000` | rs2 | `110` | `(rs1 << 3) + rs2` |
| `andn` | Zbb | OP | `0100000` | rs2 | `111` | `rs1 & ~rs2` |
| `orn` | Zbb | OP | `0100000` | rs2 | `110` | `rs1 \| ~rs2` |
| `xnor` | Zbb | OP | `0100000` | rs2 | `100` | `~(rs1 ^ rs2)` |
| `min` | Zbb | OP | `0000101` | rs2 | `100` | signed minimum |
| `minu` | Zbb | OP | `0000101` | rs2 | `101` | unsigned minimum |
| `max` | Zbb | OP | `0000101` | rs2 | `110` | signed maximum |
| `maxu` | Zbb | OP | `0000101` | rs2 | `111` | unsigned maximum |
| `clz` | Zbb | OP-IMM | `0110000` | `00000` | `001` | number of leading zeros (32 for 0) |
| `cpop` | Zbb | OP-IMM | `0110000` | `00010` | `001` | number of set bits |

### What to change

1. **The decoder.** Today [idudec.sv](../../rtl/core/idu/idudec.sv) only receives
   `funct7[5]`. Every encoding it doesn't recognize silently runs as an RV32I
   instruction. Assemble a `clz` and work out which RV32I instruction the current core
   executes instead. Pass the bits you need into `idudec`.
   - The unary instructions are told apart by the `rs2` field.
   - Most new instructions share their funct3 with an RV32I instruction (`clz` with
     `slli`, `andn` with `and`, `xnor` with `xor`, ...). The RV32I instructions must
     keep working.
2. **The ALU control signal.** `ALUControl` is 4 bits wide and 10 of the 16 codes are
   used. Widen it.
   - **Keep the existing codes unchanged.** The unit tests in `tb/unit/idu` and
     `tb/unit/ieu` use them.
   - The width appears in `hipv_pkg`, `idudec`, `idu`, `ieu` (including the D/E
     pipeline register `ctrlreg`), `alu` and `hipv_core`.
3. **The ALU.** Add the new operations. Before you add a new block for every
   instruction, look for hardware you already have:
   - `sh2add` is an add with one operand shifted.
   - `andn` is an `and` with one operand inverted.
   - `min`/`max` need exactly the comparison that `slt`/`sltu` already compute.

   Explain your choices in the report.
4. **Lint.** The testbenches run Verilator with `-Wall`, and every warning is an
   error.
   - A `casez` whose items overlap triggers `CASEOVERLAP`, even when the overlap is
     intentional (first match wins). Either write items that don't overlap, or
     disable the warning for that one block with
     `/* verilator lint_off CASEOVERLAP */ ... /* verilator lint_on CASEOVERLAP */`
     and justify it in a comment.
   - Don't switch warnings off globally.

### Testing Task 1

```sh
cd tb/core && make MODULE=test_zbb      # core level, Task 1
cd tb/core && make                      # core level, RV32I regression
cd tb/unit/idu && make                  # unit level, regression
cd tb/unit/ieu && make                  # unit level, regression
```

The SoC-level check `sw/hw1/check` also covers Task 1, but it only passes completely
once Task 2 is done as well.

---

## Task 2: Zmmul with a single 16×16 multiplier

### Instructions

| Instruction | funct7 | funct3 | Result |
|---|---|---|---|
| `mul` | `0000001` | `000` | low 32 bits of `rs1 × rs2` |
| `mulh` | `0000001` | `001` | high 32 bits, both operands signed |
| `mulhsu` | `0000001` | `010` | high 32 bits, `rs1` signed and `rs2` unsigned |
| `mulhu` | `0000001` | `011` | high 32 bits, both operands unsigned |

All four use opcode `OP`. The divide instructions `div`, `divu`, `rem` and `remu`
(funct7 `0000001`, funct3 `1xx`) are **not** part of Zmmul. HIPV has no
illegal-instruction trap yet, so they must execute as **nops**: no register is written.

### Required architecture

You may use **exactly one** multiplication operator in your design, with two **16-bit
unsigned** operands. Split each operand into halves, A = A<sub>H</sub>·2¹⁶ + A<sub>L</sub>
(and the same for B):

```
A·B = A_L·B_L  +  (A_L·B_H + A_H·B_L)·2¹⁶  +  A_H·B_H·2³²
```

Compute one partial product per cycle and add it, shifted, into a 64-bit
accumulator.

**Signed operands.** The four partial products are unsigned. For signed operands, use
the fact that a signed 32-bit value equals its unsigned bit pattern minus 2³² when bit 31
is set:

  A<sub>signed</sub> = A<sub>unsigned</sub> − a<sub>31</sub>·2³²

Work out from this what correction `mulh` and `mulhsu` need. Explain in your report why
the correction only affects the high word, and why `mul` needs none. One clean way to
apply it costs no extra cycle; look for it.

**Structure.**

- [mul.sv](../../rtl/core/ieu/mul.sv) holds the datapath. Its ports are fixed and must
  not change, because the unit testbench depends on them. The header of `mul.sv`
  defines the contract for `Start`, `Ack`, `Busy` and `Done`; read it carefully.
- [mulctrl.sv](../../rtl/core/ieu/mulctrl.sv) holds the state machine. Its ports are
  up to you.
- `Done` must rise at most **8 cycles** after `Start`.
- `A`, `B` and `Funct3` are valid **only in the `Start` cycle**.

### Timing of the `mul` interface

The diagrams below show the reference design, which needs 5 cycles from `Start` to
`Done`: one `Start` cycle, four partial-product cycles (`Step` 0–3) and one cycle
presenting the result. Your design may be faster or slower, up to 8 cycles. One column
is one clock cycle. `x` means "don't care": the value can be anything, and the testbench
drives random values there.

Result taken at once (`Ack` in the first `Done` cycle):

```
cycle           0     1     2     3     4     5     6   
Start         ‾‾‾‾‾‾\___________________________________
A, B, Funct3   valid╳xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Busy          ______/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\_____
Step                ╳  0  ╳  1  ╳  2  ╳  3  ╳           
Done          ______________________________/‾‾‾‾‾\_____
Result        xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx╳ A*B ╳xxxxx
Ack           ______________________________/‾‾‾‾‾\_____
```

- **Cycle 0:** `Start` is high. This is the only cycle in which `A`, `B` and `Funct3`
  are valid, so everything the unit needs from them is captured at the end of this
  cycle.
- **Cycles 1–4:** one partial product per cycle, selected by `Step`.
- **Cycle 5:** `Done` is high and `Result` holds the product. `Ack` in the same cycle
  means "taken".
- **Cycle 6:** the unit is idle again, and a new `Start` may come.

Result taken later (the pipeline is not ready yet). `Done` and `Result` hold until
`Ack`:

```
cycle     0     1     2     3     4     5     6     7     8   
Start   ‾‾‾‾‾‾\_______________________________________________
Busy    ______/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\_____
Done    ______________________________/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\_____
Result  xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx╳       A*B       ╳xxxxx
Ack     __________________________________________/‾‾‾‾‾\_____
```

### A suggested control unit (`mulctrl`)

The contract above already implies three states. The control unit below is one
straightforward way to implement it. Other designs are fine as long as they keep the
contract.

```
              ┌─────────────────────── Ack ───────────────────────┐
              v                                                   │
         ┌────────┐   Start    ┌────────┐     Step == 3      ┌────────┐
reset ─> │  IDLE  │ ─────────> │  BUSY  │ ─────────────────> │  DONE  │
         └────────┘            └────────┘                    └────────┘
           │    ^                │    ^                        │    ^
           └────┘                └────┘                        └────┘
           ~Start           Step != 3: Step+1                  ~Ack
```

| State | Meaning | `Busy` | `Done` | Accumulate |
|---|---|---|---|---|
| `IDLE` | no operation; waiting for `Start` | 0 | 0 | no |
| `BUSY` | one partial product per cycle, `Step` = 0, 1, 2, 3 | 1 | 0 | yes |
| `DONE` | result ready, waiting for `Ack` | 1 | 1 | no |

Transitions:

- **`IDLE → BUSY` on `Start`.** In that same cycle the datapath captures the
  operands, remembers whether the low or the high word is wanted, and loads the
  accumulator with its starting value. The step counter is cleared.
- **`BUSY → BUSY` while `Step` ≠ 3.** Each cycle adds one shifted partial product to
  the accumulator and increments `Step`.
- **`BUSY → DONE` when `Step` = 3.** The last partial product is added, so the
  accumulator holds the full 64-bit result from the next cycle on.
- **`DONE → IDLE` on `Ack`.** Without `Ack` the unit stays in `DONE` and keeps the
  result.

`Step` drives the datapath directly. Its two bits select the operand halves, and the
number of high halves sets the shift:

| `Step` | A half (`Step[1]`) | B half (`Step[0]`) | Partial product | Shift left |
|---|---|---|---|---|
| 0 | A<sub>L</sub> | B<sub>L</sub> | A<sub>L</sub>·B<sub>L</sub> | 0 |
| 1 | A<sub>L</sub> | B<sub>H</sub> | A<sub>L</sub>·B<sub>H</sub> | 16 |
| 2 | A<sub>H</sub> | B<sub>L</sub> | A<sub>H</sub>·B<sub>L</sub> | 16 |
| 3 | A<sub>H</sub> | B<sub>H</sub> | A<sub>H</sub>·B<sub>H</sub> | 32 |

So `mulctrl` needs only `Start` and `Ack` as inputs, and gives the datapath `Busy`,
`Done`, an accumulate enable and `Step`.

### Connecting it to the pipeline

The multiplier lives in the Execute stage ([ieu.sv](../../rtl/core/ieu/ieu.sv)). Three
questions guide the integration:

1. **How does Execute hold an instruction?** At the moment, Execute is ready whenever
   it is empty or the Memory stage accepts (`ReadyE = ~ValidEReg | ReadyM`). A multiply
   has to stay in Execute until its result is ready, and must not be offered to Memory
   (`ValidE`) before that. Change `ReadyE` and `ValidE` so that the handshake does this.
   The rest of the pipeline then stalls on its own.

   This is what the reference design looks like when the Memory stage is free
   (`ReadyM` = 1). The multiply enters Execute in cycle 0 and leaves it in cycle 5.
   The `addi` behind it waits in Decode, and the Memory stage sees bubbles meanwhile:

   ```
   cycle         -1    0     1     2     3     4     5     6     7   
   Decode        mul ╳     -     ╳          addi         ╳  sw ╳  -  
   Execute        -  ╳                mul                ╳ addi╳  sw 
   Memory                           -                    ╳ mul ╳ addi
   ReadyM      ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
   Start       ______/‾‾‾‾‾\_________________________________________
   Busy        ____________/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\___________
   Step                    ╳  0  ╳  1  ╳  2  ╳  3  ╳                 
   Done = Ack  ____________________________________/‾‾‾‾‾\___________
   ValidE      ____________________________________/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
   ReadyE      ‾‾‾‾‾‾\_____________________________/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
   ```

2. **Where does the result go?** Forwarding takes the newest value from the Memory
   stage (`ForwardDataM`) and from Writeback. If the product leaves Execute on the
   same path as an ALU result, forwarding works unchanged. Explain why in the report.
3. **When may the multiplier start?** This is the subtle one. Your multiplier uses the
   forwarded operands in its `Start` cycle, while an ALU instruction uses them in the
   cycle it leaves Execute. Read the comment on `PCSrcE` in `ieu.sv` and the section
   "Branches and jumps" in [IEU.md](../IEU.md). Then think about what `ForwardDataM`
   contains while a load in the Memory stage is still waiting for its data.

### Testing Task 2

```sh
cd tb/unit/mul && make                  # unit level: the mul module alone
cd tb/core && make MODULE=test_zmmul    # core level: the multiplier in the pipeline
cd sw/hw1/check && make run             # SoC level: both tasks from C
```

At the end, run every testbench once more: `tb/core` with all three `MODULE` values,
`tb/unit/idu`, `tb/unit/ieu`, `tb/unit/mul`, `tb/soc` and `tb/fpga`.

---

## Software on the SoC

### The self-check: `sw/hw1/check`

The program is compiled with `-march=rv32i`, so the compiler never emits a new
instruction on its own. The only new instructions in the binary come from the wrappers
in [hw1_insn.h](../../sw/hw1/hw1_insn.h), for example:

```c
static inline uint32_t hw_andn(uint32_t a, uint32_t b)
{
    uint32_t r;
    __asm__ volatile (".option push\n.option arch, +zbb\n"
                      "andn %0, %1, %2\n.option pop" : "=r"(r) : "r"(a), "r"(b));
    return r;
}
```

`.option arch, +zbb` enables the extension for the assembler inside this one block
only. `make dump` shows the disassembly.

```sh
cd sw/hw1/check
make run              # compared with expected.txt
make run REF=1        # reference against itself: checks the program on the unmodified core
```

### The benchmark: `sw/hw1/bench`

`make run` in `sw/hw1/bench` prints timer ticks per operation for each new instruction,
next to the code an RV32I compiler produces without it (a libgcc call such as
`__mulsi3`, or a few base instructions). Both columns include the same loop overhead,
shown in the `loop only` row. It is not graded; it shows what your hardware buys.
`make run REF=1` prints the software version in both columns.

---

## Report

Submit a PDF of at most **6 pages**. It must cover the following.

**Task 1**

1. Which instruction bits your decoder uses to tell the new instructions apart from
   RV32I, and how you verified that RV32I still works.
2. Your ALU structure: what you reused and what you added.
3. Implementation cost, measured with the FPGA flow ([FPGA.md](../FPGA.md)), before and
   after Task 1: LUTs, flip-flops, and the critical path or achieved Fmax.

**Task 2**

4. A derivation of the sign correction for `mulh` and `mulhsu`.
5. A block diagram of the multiplier datapath and a state diagram of `mulctrl`.
6. A waveform (`make ... WAVES=1`) of a multiply in the pipeline: `ValidE`, `ReadyE`,
   your `Start`, `Busy` and `Done`, and the instruction behind the multiply waiting
   in Decode.
7. Your answer to "When may the multiplier start?", and the waveform of the
   load-then-multiply case (`TESTCASE=test_mul_after_load_slow_memory`) that shows it.
8. Cost (LUTs, flip-flops, DSPs, Fmax) compared with Task 1 alone.

## Rules

- Follow [NamingConvention.md](../../NamingConvention.md). Every new or changed file
  keeps a banner comment with your name.
- Don't modify the provided tests, `hw1_model.py`, or the interface of `mul.sv`. You
  may add tests in new files, such as `tb/core/test_hw1_mine.py` (core level) or new
  tests in a new file under `tb/unit/mul/` (unit level).
- Every testbench that passed before your changes must still pass.

## Grading

The homework is worth **30 points**.

| Part | Points |
|---|---|
| Task 1: provided and hidden tests | 8 |
| Task 2: provided and hidden tests | 12 |
| Your own tests (new cases, not copies) | 2 |
| Report | 6 |
| Code quality and naming convention | 2 |
| **Total** | **30** |

## Submission

Deadline: **<date>**. Submit **<how: e.g. a link to your `hw1` branch, or an archive
of the repository without build directories>** together with the report PDF.
