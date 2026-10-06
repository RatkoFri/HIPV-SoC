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
disagreed by a factor of two. The BSP is back to `CPU_HZ / baud`. `CPU_HZ`, the XDC
constraint and `tb/fpga` all use the 50 MHz SoC clock (a 100 MHz configuration did
not meet timing). See "Clock frequency" in `docs/FPGA.md`.

---

<!-- Copy the block above for each new bug, replacing BUG-XXX with the next
     free number, and add a row to the Index table. -->
