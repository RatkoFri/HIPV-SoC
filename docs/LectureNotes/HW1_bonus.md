# Homework 1: Bonus

This is an optional extension of [Homework 1](HW1.md). Start it only once both tasks
of the homework pass all their tests. It is worth up to **3 extra points** on top of
the 30 points of the homework.

There are two parts. You can do either one or both.

## Bonus A: the rest of Zbb (1.5 points)

Implement the remaining RV32 Zbb instructions:

| Instruction | Opcode | funct7 (or imm[11:5]) | rs2 field (or shamt) | funct3 | Operation |
|---|---|---|---|---|---|
| `clz` | OP-IMM | `0110000` | `00000` | `001` | number of leading zeros (32 for 0) |
| `cpop` | OP-IMM | `0110000` | `00010` | `001` | number of set bits |
| `ctz` | OP-IMM | `0110000` | `00001` | `001` | number of trailing zeros (32 for 0) |
| `sext.b` | OP-IMM | `0110000` | `00100` | `001` | sign-extend byte |
| `sext.h` | OP-IMM | `0110000` | `00101` | `001` | sign-extend halfword |
| `zext.h` | OP | `0000100` | `00000` | `100` | zero-extend halfword |
| `rol` | OP | `0110000` | rs2 | `001` | rotate left by `rs2[4:0]` |
| `ror` | OP | `0110000` | rs2 | `101` | rotate right by `rs2[4:0]` |
| `rori` | OP-IMM | `0110000` | shamt | `101` | rotate right by `shamt` |
| `orc.b` | OP-IMM | `0010100` | `00111` | `101` | each byte becomes `0xFF` if non-zero, else `0x00` |
| `rev8` | OP-IMM | `0110100` | `11000` | `101` | reverse the byte order |

`clz`/`cpop`/`ctz`/`sext.b`/`sext.h` all share `OP-IMM` and funct3 `001` with
`slli` — a right shift by immediate isn't the only thing that encoding means.
They're unary (only `rs1`), so the `rs2` field is free to tell them apart from
each other and from `slli`; that's the same encoding trick Task 1's `andn`/
`minu` example used for distinguishing by funct7, just on a different field.

The rest of the decoding is harder than that:

- `rori`, `orc.b` and `rev8` share funct3 `101` with `srli` and `srai`, so `funct7[5]`
  alone no longer tells a right shift from the rest.
- `orc.b` and `rev8` are identified by the whole 12-bit immediate.

### Testing

The bonus tests are switched off unless you ask for them:

```sh
cd tb/core && make MODULE=test_zbb HW1_BONUS=1    # core level
cd sw/hw1/check && make run BONUS=1               # SoC level, compared with expected_bonus.txt
```

With `HW1_BONUS=1`, `test_zbb.py` runs three extra tests. All the Task 1 tests must
still pass too.

| Test | What it checks |
|---|---|
| `test_bonus_unary` | `clz`, `cpop`, `ctz`, `sext.b`, `sext.h`, `zext.h`, `orc.b`, `rev8` on edge cases, every single bit and random values |
| `test_bonus_rotate` | `rol` and `ror` with rotate amounts 0, 1, 15, 16, 31, and values above 31 (only `rs2[4:0]` counts) |
| `test_bonus_rori` | `rori` with several immediate amounts |

`make run BONUS=1` in `sw/hw1/check` adds a "Task 1: bonus" block to the self-check.

## Bonus B: a faster multiplier (1.5 points)

The straightforward Task 2 design spends one cycle capturing the operands, four cycles
on partial products and one cycle signalling `Done`. Shorten it, keeping exactly
**one** 16×16 multiplier. Each of these saves one cycle:

1. **Start working in the `Start` cycle.** The operands are on the inputs during
   `Start`, so the first partial product can be computed right away.
2. **Skip A<sub>H</sub>·B<sub>H</sub> for `mul`.** It only adds to bits 63:32, which
   `mul` does not return.
3. **Finish in the last accumulation cycle.** Present `accumulator + last partial
   product` directly, instead of waiting for it to be registered.

Some of these lengthen the critical path; measure what each costs.

### Testing

The Task 2 testbenches already accept any latency up to 8 cycles, so run them as before:

```sh
cd tb/unit/mul && make                  # test_latency logs the new latencies
cd tb/core && make MODULE=test_zmmul
cd sw/hw1/check && make run
cd sw/hw1/bench && make run
```

## What to submit

Add a section of at most 2 pages to your report (on top of the 6-page limit):

- **Bonus A:** how your decoder tells `srli`, `srai`, `rori`, `orc.b` and `rev8` apart, and
  the extra cost (LUTs) compared with Task 1.
- **Bonus B:** for each optimization you implemented, the latency from `tb/unit/mul`,
  the `mul`/`mulh` rows of the benchmark, and the cost (LUTs, flip-flops, Fmax)
  compared with your Task 2 design. Explain why the benchmark changes much less than
  the latency.

Bonus points are given only for work that passes all tests of the homework and of the
bonus part you did.
