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
| Clock | `top.sv` divides the board's 100 MHz oscillator down to the SoC's real 25 MHz operating clock with the CMT's `MMCME2_ADV` + a `BUFG`. The XDC constrains the port itself at its true **100.00 MHz** (10.00 ns). See "Clock frequency" below. |
| Reset | `CPU_RESETN` is active-low; two flops synchronise it into the SoC clock domain and it is inverted to the SoC's active-high `reset`. |
| Power-on | A 4-bit counter holds reset for 15 SoC clocks after configuration, so the SoC starts cleanly even if the button is never pressed. |
| GPIO | 8 slide switches → `GpioIn`, 8 LEDs ← `GpioOut`. |
| UART | `uart_tx` → D4 (Digilent's `UART_RXD_OUT`), `uart_rx` ← C4 (`UART_TXD_IN`). The naming is from the USB bridge's point of view, which is easy to get backwards. |
| Timer | `TimerOverflow` on LED8. |

The wrapper deliberately uses no packages and no type parameters, so it survives any
conversion path.

Pin assignments in `fpga/anvil/Nexys-A7-100T-Master.xdc` are taken from the Digilent
master XDC shipped with Anvil.

> **Clock frequency.** Two different clocks matter here, and they are not the same
> thing:
>
> - **The physical oscillator on the `clk` pin is 100 MHz** (`CLK100MHZ`, pin E3).
>   The XDC constrains the port at its true rate, `create_clock -period 10.00`.
> - **The SoC's actual operating clock is 25 MHz (`SocClk`)**, produced inside
>   `top.sv` by the Artix-7's dedicated clock-management hardware: `MMCME2_ADV`
>   (VCO = 100 MHz × 10 = 1000 MHz, `CLKOUT0` = 1000 / 40 = 25 MHz) through a
>   `BUFG` for low-skew distribution. `CPU_HZ` in `sw/rules.mk` and
>   `sw/bsp/bsp.h` (default `25000000`) must match **this** clock, not the
>   board's raw oscillator rate — it is what the BSP uses to compute the UART
>   divider and delays.
>
> A real divider was chosen over just changing `CPU_HZ` to match the undivided 100
> MHz (which is what this project did for a while — see `KnownBugs.md`, `BUG-CLOCK`)
> because the design's logic does not reliably meet timing at 100 MHz; 25 MHz does,
> with comfortable margin. A plain fabric FSM divider (no hard block) works too and
> was confirmed on hardware first; `MMCME2_ADV` replaced it since it's the proper
> use of dedicated silicon for this. (`MMCME2_BASE`, the simplified wrapper, does
> *not* work in this flow — Yosys's Xilinx techmap doesn't lower it to the
> `MMCME2_ADV` primitive this toolchain's VPR architecture actually models, so
> packing fails outright. `MMCME2_ADV` must be instantiated directly.)
>
> One toolchain limitation worth knowing if you touch this: the XDC→SDC conversion
> in this flow follows a declared clock through *combinational* wiring, but not
> through a register or a clock-management primitive — so a constraint on the `clk`
> port does not automatically extend to `SocClk`'s domain, divider or hard block.
> `report_timing.setup.rpt` for a build with `MMCME2_ADV` in place is **completely
> empty** (0 paths); with the fabric FSM it at least reports the divider's own
> trivial register. Neither build's own report proves `SocClk`'s domain is safe.
> The confidence that 25 MHz is safe instead comes from a separate, directly-wired
> experiment (no divider at all, `clk` fed straight into the SoC, properly and
> fully constrained at 40 ns/25 MHz) against this same `hipv_soc` RTL, which
> reported 0 violations and +14 ns worst-case slack — plus confirmation on real
> hardware with both the FSM and the `MMCME2_ADV` version. See `KnownBugs.md`
> (`BUG-CLOCK`) for the full history and that measurement.
>
> If UART output is readable only at exactly double the configured baud, `CPU_HZ`
> has drifted from the real 25 MHz clock again (see `BUG-CLOCK`).

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

- **Baud rate.** The BSP computes the UART divider as `CPU_HZ / BAUD`, rounded down to
  a multiple of 16 (the receiver oversamples ×16). The defaults (`CPU_HZ=25000000`,
  `BAUD=19200`) give 1296 clock cycles per bit, 0.47 % off 19200 baud. Set the terminal
  to 19200 8N1. A `CPU_HZ` that doesn't match the real clock garbles every character —
  readable at exactly double the configured baud is the signature of `CPU_HZ` being
  half the real clock (see `KnownBugs.md`, `BUG-CLOCK`).
- **Timing closure.** The design meets the 40 ns (25 MHz) constraint comfortably
  (+14 ns worst-case slack, measured against the unmodified reference-solution ALU);
  20 ns (50 MHz) does not close, and 10 ns (100 MHz, the board's raw oscillator
  rate) closes even less. The reference solution's wider ALU (Zba/Zbb/Zmmul) made
  the margin considerably tighter than the base RV32I core alone — see
  `KnownBugs.md` (`BUG-CLOCK`) for the measurements.
- **Reset button.** `CPU_RESETN` is active-low, and is the red button, not one of
  the coloured push buttons.
- **BRAM budget.** 64 KiB of unified memory is 16 RAMB36 of 135.

## Not covered yet

`anvil test` (Icarus) would hit the same per-file sv2v limitation as synthesis; our
verification uses cocotb + Verilator instead. Anvil's `soc.json` firmware flow is
deliberately unused — it assumes its own `link.ld`, `startup.S` and generated RAM
module, which would replace the aliased-window memory design and the `sw/` toolchain.
