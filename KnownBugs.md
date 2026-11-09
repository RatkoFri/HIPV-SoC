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
| BUG-CLOCK | CPU_HZ (50 MHz) didn't match the real undivided 100 MHz board clock | sw, docs | High | Fixed |

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
wrong — see `BUG-CLOCK`. `CPU_HZ` is now `100000000`, the real undivided board clock.

---

## BUG-CLOCK: CPU_HZ (50 MHz) didn't match the real 100 MHz board clock

- **Component:** sw, docs
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

**Remaining risk (not fixed here, by design)**
The design's timing closure was only ever verified against the 20 ns/50 MHz XDC
constraint; the real clock period is 10 ns, and that has never been checked by
place/route. `CPU_HZ=100000000` makes the *baud/timing-cycle math* correct, but does
not prove every combinational path actually settles within a true 10 ns period —
only an RTL fix (an actual clock divider in `top.sv`, or re-verified timing closure
at a true 100 MHz constraint) can close that out. Flagged here rather than fixed
since the fix was scoped to software only.

---

<!-- Copy the block above for each new bug, replacing BUG-XXX with the next
     free number, and add a row to the Index table. -->
