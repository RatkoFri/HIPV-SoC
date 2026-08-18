# HIPV SoC

`rtl/top/hipv_soc.sv` is the complete system: the RV32I core, the OBI crossbar, the
unified dual-port RAM and three peripherals. It boots from a memory image applied at
elaboration — no boot ROM, no JTAG, no SPI loader.

Testbench: `tb/soc/`. Component docs: `CORE.md`, `INTERCONNECT.md`, `MEMORY.md`,
`rtl/periph/README.md`.

## Structure

```
                 ┌──────────────┐
                 │  hipv_core   │
                 │  I master ─┐ │
                 │  D master ─┼─┼──┐
                 └────────────┼─┘  │
                              v    v
                        ┌───────────────┐
                        │   obi_xbar    │  2 masters x 5 slaves
                        └──┬──┬──┬──┬──┬┘
              IMEM window ─┘  │  │  │  └─ GPIO ──> GpioOut / GpioIn
              DMEM window ────┘  │  └──── TIMER ─> TimerOverflow
                    (one RAM)    └─────── UART ──> Tx / Rx
```

The instruction master is read-only; its `We`/`Be`/`Wdata` are tied off in the top
level. IMEM and DMEM are two crossbar slaves backed by **one** physical dual-port RAM,
so a single image holds code and data (see `MEMORY.md`).

## Ports

| Port | Dir | Description |
|------|-----|-------------|
| `clk`, `reset` | in | Clock and synchronous, active-high reset |
| `Tx`, `Rx` | out/in | UART serial pins |
| `GpioIn`, `GpioOut` | in/out | GPIO pins, `GPIO_WIDTH` bits each |
| `TimerOverflow` | out | Timer compare match — the future machine-timer interrupt |

## Parameters

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `RAM_ADDR_WIDTH` | 14 | RAM depth in words (2^14 = 64 KiB) |
| `INIT_FILE` | `""` | `$readmemh` program image, applied at elaboration |
| `ARB_POLICY` | `ARB_FIXED` | Crossbar arbitration: fixed priority or round robin |
| `GPIO_WIDTH` | 8 | GPIO pin count |

## Address map

See `INTERCONNECT.md` for the table and `rtl/periph/README.md` for the register maps.
In short: IMEM `0x0000_0000`, DMEM `0x1000_0000`, UART `0x2000_0000`,
TIMER `0x2000_1000`, GPIO `0x2000_2000`.

Because the two memory windows alias, **the data area must sit above the code**. The
test program places it at byte offset `0x200`; a store to `0x1000_0000` would overwrite
the first instruction.

## Reset

Everything is synchronously reset, including the peripherals (see
`rtl/stdlib/README.md`). Reset must therefore be held with the clock running — the SoC
has no gated clocks, so this is always satisfied. `test_reset_is_synchronous` checks
that a mid-run reset clears the GPIO outputs and the program restarts from address 0.

## Running a program

```sh
# from a linked binary
riscv32-unknown-elf-objcopy -O binary prog.elf prog.bin
python3 scripts/mkmem.py --bin prog.bin -o prog.hex --words 16384
```

then elaborate with `-GINIT_FILE=\"prog.hex\"` (the `tb/soc` Makefile shows the full
invocation). In practice use `sw/`: `make run` in any example builds the image and
executes it on this testbench, printing the program's UART output (`sw/README.md`). `tb/soc/gen_prog.py` builds its image straight from the Python assembler
in `tb/common/rv32i.py`, including a two-pass label resolver.

## Verification

`tb/soc/test_hipv_soc.py` runs one program that exercises every slave and reports
results **over the UART**, so the checks happen at the SoC pins rather than by reaching
inside the design. Each reported byte proves a different path:

| Byte | Proves |
|------|--------|
| `0x2A` (42) | store to RAM through the DMEM window, then load back |
| `0xA5` | GPIO output register read back over the bus |
| `0x37` (55) | branch loop summing 1..10, with forwarding |
| `0xB7` | low byte of instruction word 0 read through the DMEM window — the unified-memory aliasing |

Other tests: GPIO pins driven, timer compare match firing (and dropping when a non-zero
compare is programmed), stored results present in the RAM array, and the synchronous
reset restart. The UART check was confirmed non-vacuous by feeding it wrong
expectations and seeing the real bytes reported.

The program also exercises `jal`/`jalr` (the UART send routine is called four times)
and a poll loop on the UART status register, so control flow and peripheral polling are
covered end to end.

## Toolchain note

Some Verilator packages (the pip wheel among them) ship `verilated.mk` with an empty
`CFG_CXXFLAGS_PCH_I`, which breaks the C++ build for designs large enough to use a
precompiled header — the SoC testbench trips it, the unit ones do not.
`tb/common/Makefile.include` detects that specific case and supplies the correct
`-include` flag; a correctly packaged Verilator is left untouched.

## Not implemented yet

- Traps and interrupts: `TimerOverflow` is brought to the boundary but nothing consumes
  it; `ecall`/`ebreak`/CSRs decode as nops.
- No bus error path: the crossbar's error responder returns zeros, and peripheral
  `rerr` outputs are unrouted.
- No protection between the code and data windows.
