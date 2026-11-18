# Known Bugs

Tracks known issues in HIPV — RTL, software, testbenches, or the FPGA flow —
that are not fixed yet. Add a new entry when a bug is found but not
immediately fixed; move it to "Fixed" (or delete it) once resolved, noting
the commit that fixed it.

## Index

| ID | Title | Component | Severity | Status |
|----|-------|-----------|----------|--------|
| BUG-001 | *(example — remove once real bugs are added)* | core/ifu | Low | Open |
| BUG-UART | UART baud divider: software and hardware disagree on the clock | sw/bsp, fpga | High | Fixed |
| BUG-CLOCK | SoC ran on the board's raw 100 MHz clock; real ALU timing needs ~25 MHz | sw, fpga, docs | High | Fixed |

**Component:** `core/<stage>`, `interconnect`, `mem`, `periph/<name>`, `sw`,
`fpga`, `tb`, or `docs`.
**Severity:** `Critical` (wrong results / crash), `High` (breaks a feature),
`Medium` (workaround exists), `Low` (cosmetic, style, minor).
**Status:** `Open`, `In progress`, `Blocked`, `Fixed`.

<!-->
---

## TEMPLATE BUG-XXX: <short title>

- **Component:** <e.g. core/ifu, sw/bsp, fpga>
- **Severity:** <Critical | High | Medium | Low>
- **Status:** <Open | In progress | Blocked | Fixed>
- **Reported by:** <name>, <YYYY-MM-DD>
- **Affects:** <commit/branch, or "all" if long-standing>

**Description**
What is wrong, in one or two sentences.

**Steps to reproduce**
1. ...
2. ...

**Expected behavior**
What should happen.

**Actual behavior**
What happens instead (include error output, waveform observation, or test
failure if relevant).

**Workaround**
How to avoid hitting it in the meantime, if any. Omit if none.

**Notes / root cause**
Any investigation so far — suspected cause, related modules, links to a
testbench run or `docs/*.md` section. Omit while unknown.

**Resolution** *(fill in when Status becomes Fixed)*
Fixed in <commit hash / PR>. Brief note on the actual fix.
<!-->
---

## BUG-UART: <CALCULATION OF SPEED FOR  UART>

- **Component:** < sw/bsp, rtl/peripherals/obi_uart>
- **Severity:** <Critical |  Low>
- **Status:** Fixed
- **Reported by:** Ratko, 30. 8. 2027
>

**Description**
There is missmatch between how the speed is calculated between sw and hw. If you put  CPU_HZ / (baud >> 1) everything works well. However it is expected to be  CPU_HZ / (baud << 4) 

Need to check where the mismatch is 


**Steps to reproduce**
1. line 5 bsp.c


**Workaround**
How to avoid hitting it in the meantime, if any. Omit if none.

**Notes / root cause**
Any investigation so far — suspected cause, related modules, links to a
testbench run or `docs/*.md` section. Omit while unknown.

**Resolution**
The UART hardware is consistent with itself: TX uses `SPEED` clock cycles per bit,
and RX samples at `SPEED >> 4` (16× oversampling). So `SPEED = CPU_HZ / baud`
(rounded down to a multiple of 16) is the right formula. `CPU_HZ / (baud >> 1)`
doubled the divider, so the BSP and the testbench (which decodes at `CPU_HZ / BAUD`)
disagreed by a factor of two. The BSP is back to `CPU_HZ / baud`.

Note: the claim below that `CPU_HZ` should be the 50 MHz XDC constraint was itself
wrong — see `BUG-CLOCK`. `CPU_HZ` is now `25000000`, matching the real SoC clock
(`top.sv` now divides the board's 100 MHz oscillator down to 25 MHz).

---

## BUG-CLOCK: SoC ran on the board's raw 100 MHz clock; real ALU timing needs ~25 MHz

- **Component:** sw, fpga, docs
- **Severity:** High
- **Status:** Fixed
- **Reported by:** Ratko, 9. 11. 2026
- **Affects:** all hardware runs before this fix; simulation (`tb/soc`, `tb/fpga`) was
  unaffected, since those testbenches decode UART in clock-cycle units derived from
  the same `CPU_HZ`/`BAUD` the firmware uses, not from a real-time baud rate.

**Description**
Measured UART output on real hardware came out at exactly 2× the configured baud
(38400 observed vs. 19200 configured) — opening the terminal at double the
configured rate gave clean text.

**Steps to reproduce**
1. Build and flash any example (e.g. `make APP=blink all`).
2. `stty -F /dev/ttyUSB1 19200 raw -echo && cat /dev/ttyUSB1` — garbled.
3. `stty -F /dev/ttyUSB1 38400 raw -echo && cat /dev/ttyUSB1` — clean.

**Expected behavior**
UART output readable at the configured `BAUD` (19200).

**Actual behavior**
Output only readable at 2× the configured baud.

**Root cause**
`fpga/anvil/top.sv` feeds the Nexys A7's on-board oscillator (`CLK100MHZ`, pin E3)
directly into the SoC's `clk` input with no divider — the real clock is 100 MHz.
`CPU_HZ` (`sw/rules.mk`, `sw/bsp/bsp.h`) defaulted to `50000000`, matching the XDC's
`create_clock -period 20.00` — which is only a *timing-closure target* for
place/route, not an actual frequency divider. Every cycle-based divider the BSP
computes from `CPU_HZ` (`UART_SPEED`, `delay_cycles`, `timer`-based waits) therefore
ran at half the real rate, so hardware events happened twice as fast as the firmware
intended. The existing "Clock frequency" callout in `docs/FPGA.md` had already
anticipated this exact symptom ("readable at twice that rate") without anyone having
hit it yet.

**Resolution**
Software-only fix (explicitly not an RTL change — the real clock still reaches the
SoC undivided, and the 20 ns/50 MHz constraint is still what place/route verifies
against): `CPU_HZ` now defaults to `100000000` in `sw/rules.mk` and `sw/bsp/bsp.h`,
matching the real board clock. `RUN_CYCLES` in `sw/rules.mk` was doubled (2,000,000 →
4,000,000) since every UART character now costs ~52000 simulated cycles instead of
~26000. `docs/FPGA.md` and `sw/README.md` were updated to state the real clock (100
MHz) and the synthesis-only constraint (50 MHz) as two different numbers instead of
one.

**Update — the risk below materialized, and this was then fixed with a real
RTL clock divider instead of just matching software to the raw clock.**

The "remaining risk" originally flagged here (below, kept for history) was: the
20 ns/50 MHz XDC constraint had never been checked against the SoC's true 10 ns
clock period, so correctness at the real rate was unverified. It surfaced for
real once homework 1's reference solution (Zba/Zbb/Zmmul) widened the ALU: real
hardware gave corrupted results on the new `min`/`minu`/`max`/`maxu` ops (same
wrong constant, `0xffffffdf`, out of three different operations — a flop
capturing mid-transition, not an ALU logic bug), and the build's own timing
report confirmed it: **96 setup violations, worst slack -6.519 ns** against even
the lenient 20 ns/50 MHz constraint, let alone the true 10 ns the silicon
actually runs at.

Two angles were tried:

1. **Shrink the critical path.** Sharing `alu.sv`'s signed comparator across
   `SLT`/`MIN`/`MAX`, and sharing one adder across `ADD`/`SH1ADD`/`SH2ADD`/
   `SH3ADD`, recovered about half the gap (worst slack -6.519 ns → -3.409 ns,
   setup violations 96 → 77) but plateaued — the remaining cost is diffuse
   (the ALU's ~20-way result-select mux, not any one operation), confirmed by
   checking the crossbar (`obi_xbar.sv`'s response-data mux, `obi_arbiter.sv`)
   was **not** actually in the worst paths despite looking like a plausible
   culprit; the "clocked by `soc.xbar.gen_slave[4].arb.clk`" label on every
   violated path is just the flattened netlist's name for the one global
   clock net, not evidence the crossbar's own logic is in the chain.
2. **Lower the real clock instead.** Reverting the ALU to the untouched
   reference solution and re-checking against a 40 ns/25 MHz constraint gave
   **0 violations, +14.077 ns worst-case slack** — comfortable margin with no
   RTL changes to the core at all. This is the one that shipped.

**Resolution**
`fpga/anvil/top.sv` now has a real divider producing `SocClk` at 25 MHz, which
clocks `hipv_soc` and the whole reset tree, using the Artix-7's dedicated
clock-management hardware: `MMCME2_ADV` (VCO = 100 MHz × 10 = 1000 MHz,
`CLKOUT0` = 1000 / 40 = 25 MHz) through a `BUFG`. **Confirmed working on real
hardware** (Nexys A7-50T). The XDC's `create_clock` now honestly constrains
the `clk` **port** at its true 10 ns/100 MHz physical rate (previously it
mis-stated the port as if it ran at the SoC's rate). `CPU_HZ` is `25000000` in
`sw/rules.mk` and `sw/bsp/bsp.h`, matching `SocClk` — not the board's raw
oscillator and not any synthesis-only target.

Getting there took three attempts:

1. **`MMCME2_BASE` + `BUFG`** (the simplified MMCM wrapper) — synthesis
   succeeded, but packing failed: `Failed to find matching architecture model
   for 'MMCME2_BASE'`. Yosys's Xilinx techmap doesn't lower `MMCME2_BASE` to
   the `MMCME2_ADV` primitive this toolchain's VPR architecture actually
   models (confirmed present in `xc7a50t_test/arch.timing.xml`), and nothing
   in this flow performs that lowering step.
2. **A fabric FSM divider** (4 states, one per 100 MHz input edge, high for
   two of the four — 50% duty cycle divide-by-4) — no vendor-primitive gap to
   hit, builds and **confirmed working on real hardware** first. Shipped
   initially.
3. **`MMCME2_ADV` directly** (this is what's in `top.sv` now) — the full
   primitive, not the `BASE` wrapper, with its dynamic-reconfiguration and
   phase-shift ports (`DADDR`/`DCLK`/`DEN`/`DI`/`DWE`, `PSCLK`/`PSEN`/
   `PSINCDEC`) tied off disabled and `CLKINSEL` pinning `CLKIN1` as the only
   input. Builds cleanly and **also confirmed working on real hardware**;
   replaced the FSM since it's the proper use of dedicated silicon instead of
   fabric LUTs/FFs for this.

**Toolchain gotcha worth remembering:** this flow's XDC→SDC conversion follows
a declared clock through *combinational* wiring (how the direct-wire
experiments above got correctly constrained), but not through a register or a
clock-management primitive — so once anything sits between the `clk` port and
`SocClk`, that build's own `report_timing.setup.rpt` cannot be trusted to say
anything about `SocClk`'s domain:
- with the fabric FSM in place, it reports one trivial path (the divider's
  own register, meeting its own 100 MHz check) and lists the SoC's actual
  logic — thousands of flip-flops — as *unconstrained* in
  `report_unconstrained_timing.setup.rpt`;
- with `MMCME2_ADV` in place, `report_timing.setup.rpt` is **completely
  empty** (0 paths) — even less visibility than the FSM gave, despite being
  the "proper" hard-block implementation.

**Neither build's own timing report proves `SocClk`'s domain is safe.** The
confidence that 25 MHz is safe comes from the direct-wire experiment (no
divider at all, `clk` fed straight into the SoC, properly and fully
constrained at 40 ns/25 MHz against this same `hipv_soc` RTL: 0 violations,
+14 ns worst-case slack) plus real-hardware confirmation of both divider
implementations — not from either divider build's own report. Getting a
self-contained, trustworthy report for either would need an explicit
`create_generated_clock` in the XDC targeting `SocClk`/`CLKOUT0` — untried;
unknown whether this toolchain's XDC parser honors it.

---

<!-- Copy the block above for each new bug, replacing BUG-XXX with the next
     free number, and add a row to the Index table. -->
