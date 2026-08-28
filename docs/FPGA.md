# FPGA synthesis with Anvil

Building HIPV for the Digilent Nexys A7-100T using
[Anvil](https://logismith.github.io/Anvil/), which drives the open-source F4PGA
toolchain (Yosys + VPR — no Vivado).

Project: `fpga/anvil/`. Build script: `scripts/anvil_flow.py`.
Wrapper testbench: `tb/fpga/`.

## How Anvil works

A single-file Python CLI that orchestrates F4PGA, `sv2v` and `openFPGALoader`. It
adds a project model on top:

- **`config.json`** — board, top module, module list, params.
- **Modules** — versioned directories `modules/<name>@<version>/` with a
  `module.json` declaring `depends`. Resolution is depth-first, deduplicated,
  topologically ordered, with a circular-dependency guard.
- **Boards** — `boards.json` maps a board to its part, target and master XDC.
- **SoC flow** (optional) — a module containing `soc.json` makes Anvil compile
  `firmware/` and generate a RAM module.

The `Makefile` in a project is **regenerated on every synth**. Never edit it.

```
anvil build      # firmware (if any) + bitstream
anvil program    # openFPGALoader
anvil modules    # list available modules
anvil test       # Icarus-based testbench runner (separate from F4PGA)
```

## Three constraints HIPV had to work around

These were found by reading `anvil.py` and by running the tools, not by assumption.

**1. Source collection is not recursive.** `get_sv_files` uses `os.listdir`, so only
files sitting *directly* in the project root or *directly* in a module directory are
collected. Our `rtl/core/ifu/*.sv` tree would be silently ignored. RTL must be
packaged flat — the build script checks that every basename is unique and fails
loudly if two would collide.

**2. Anvil runs sv2v once per file.** `sv2v_convert()` invokes `sv2v <file> -w <out>`
for each `.sv` separately. A file containing `import hipv_pkg::*;` converted in
isolation has no package in scope, so our design cannot go through that path at all.

**3. Our RTL genuinely needs sv2v.** Yosys 0.68 was run directly on the sources and
rejects both `parameter type DTYPE` (the std-lib `register`) and `import pkg::*` — in
the module body *and* in the module header. So bypassing sv2v is not an option either.

**The resolution:** `scripts/anvil_flow.py` does the conversion itself. It flattens
every source into one scratch project directory, runs sv2v **once over the whole
design** so packages resolve, and drops finished `.v` files in the project root.
Anvil then sees plain Verilog and uses it as-is — no sv2v step of its own, and no
modules or `installmodule` steps needed at all. Constraints 1–3 all disappear and
Anvil stays unmodified.

The scratch directory (`build/anvil-work/` by default) is **wiped at the start of
every run**, so a build can never pick up stale Verilog from a previous one. Nothing
in it is meant to be edited or committed.

## What synthesis produces

Yosys was run on the memory subsystem to check the part that actually worries a
teaching SoC — BRAM inference and program initialization:

```
MEMORY_LIBMAP: mapping memory sync_dual_port_RAM.mem via $__XILINX_BLOCKRAM_TDP_
4 × RAMB36E1        (16 KiB; 64 KiB → 16 BRAMs, the xc7a100t has 135)
```

The true dual-port style infers TDP block RAM with both write ports kept separate,
and the `$readmemh` init survives into a `$meminit` cell — so the program is baked
into the bitstream, exactly as `docs/MEMORY.md` intends.

## Board wrapper

`fpga/anvil/top.sv` is board plumbing only:

| Concern | What it does |
|---------|--------------|
| Clock | The board clock drives the SoC directly. The XDC constrains it at **50.00 MHz** (20.00 ns). See the warning below. |
| Reset | `CPU_RESETN` is active-low; two flops synchronise it into the SoC clock domain and it is inverted to the SoC's active-high `reset`. |
| Power-on | A 4-bit counter holds reset for 15 SoC clocks after configuration, so the SoC starts cleanly even if the button is never pressed. |
| GPIO | 8 slide switches → `GpioIn`, 8 LEDs ← `GpioOut`. |
| UART | `uart_tx` → D4 (Digilent's `UART_RXD_OUT`), `uart_rx` ← C4 (`UART_TXD_IN`). The naming is from the USB bridge's point of view, which is easy to get backwards. |
| Timer | `TimerOverflow` on LED8. |

The wrapper deliberately uses no packages and no type parameters, so it survives any
conversion path.

Pin assignments in `fpga/anvil/Nexys-A7-100T-Master.xdc` are taken from the Digilent
master XDC shipped with Anvil.

> **Clock frequency, worth a deliberate decision.** The Nexys A7 on-board oscillator
> at E3 is **100 MHz**, but the constraint declares 50 MHz. Static timing analysis
> therefore checks a 20 ns period that the pin does not actually receive, and hardware
> would run at twice the analysed frequency. This is correct only if a 50 MHz clock is
> genuinely supplied on that pin. Otherwise either change the period to `10.00` and
> build software with `CPU_HZ=100000000`, or bring the clock down before the pin.

## Build flow

One script does everything:

```sh
make -C sw/examples/hello                    # build a program
python3 scripts/anvil_flow.py build          # flatten, convert, synthesise
python3 scripts/anvil_flow.py program        # ... and flash the board
```

Other actions and options:

```sh
python3 scripts/anvil_flow.py prepare        # stop after flattening, inspect it
python3 scripts/anvil_flow.py clean          # remove the scratch directory
python3 scripts/anvil_flow.py build --firmware sw/examples/blink/build/blink.hex
python3 scripts/anvil_flow.py build --work /tmp/hipv --keep --sv2v /path/to/sv2v
```

What a run does, in order:

1. wipe the scratch project directory (`--keep` skips this, for debugging);
2. check every source has a unique basename — flattening needs that, and the script
   fails loudly rather than silently overwriting a file;
3. run sv2v once over packages + RTL + `top.sv` into the project root;
4. delete the empty files the packages leave behind (by name — an empty output for
   anything else is an error, since it means the conversion went wrong);
5. copy `config.json` (with an empty module list), the XDC, and the firmware image;
6. run `anvil build`, then `anvil program` if asked.

The firmware image is referenced by `top.sv` as `INIT_FILE("firmware.hex")` and
resolved relative to the directory synthesis runs in — the scratch project root.

## Verification before hardware

`tb/fpga/` simulates the wrapper itself, since bring-up bugs live in board plumbing
rather than in the SoC (which `tb/soc/` already covers): reset polarity, power-on
reset release, GPIO↔LED and switch↔GPIO mapping, UART on the right pin decoded as
real 8N1 frames, and the timer LED tracking `TimerOverflow`. Run with `make` in
`tb/fpga`.

Two consequences of cocotb running every test in one simulation shaped this
testbench, and both are easy to trip over:

- **The power-on-reset test must stay first** — power-on state exists only once.
- **Every test starts its own clock and presses the reset button.** cocotb cancels
  the coroutines a test started when that test ends, so a shared clock would stop
  after the first test; and the program only runs at boot, so a test that watches
  boot has to restart the SoC itself.

## Things to expect on first bring-up

- **Baud rate.** The BSP computes the UART divider from `CPU_HZ`. The SoC runs at
  50 MHz here, so build software with `make CPU_HZ=50000000` (the default) — not
  100 MHz, or every character will be garbled.
- **Timing closure.** At 50 MHz there should be generous margin; the likely critical
  path if you push higher is the crossbar's combinational grant path into the RAM.
- **Reset button.** `CPU_RESETN` is active-low, and is the red button, not one of
  the coloured push buttons.
- **BRAM budget.** 64 KiB of unified memory is 16 RAMB36 of 135.

## Not covered yet

`anvil test` (Icarus) would hit the same per-file sv2v limitation as synthesis; our
verification uses cocotb + Verilator instead. Anvil's `soc.json` firmware flow is
deliberately unused — it assumes its own `link.ld`, `startup.S` and generated RAM
module, which would replace the aliased-window memory design and the `sw/` toolchain.
