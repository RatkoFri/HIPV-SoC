# CLAUDE.md

Project context for Claude Code in this repo.

## What this is

HIPV: a pedagogical 5-stage pipelined RV32I RISC-V core and SoC (`hipv_core` +
`hipv_soc`), developed for lectures. SystemVerilog RTL, cocotb/Verilator
verification, bare-metal C software, and an Anvil/F4PGA FPGA flow targeting
the Digilent Nexys A7 (100T by default, 50T also supported).

Read before making non-trivial changes:

- `README.md` — project map, verification quick-start, Docker usage.
- `FolderStructure.md` — where things live and why.
- `NamingConvention.md` — RTL style (flatcase clk/reset, UpperCamelCase
  signals, MACRO_CASE constants, pipeline-stage suffixes `F`/`D`/`E`/`M`/`W`).
  New RTL is expected to follow this.
- `KnownBugs.md` — tracked bugs and toolchain gotchas. **Check this before
  re-investigating a clock, timing, or UART baud problem** — several
  non-obvious ones (and their root causes) are already written up in detail,
  e.g. `BUG-CLOCK` (the SoC's real operating clock vs. the XDC's
  timing-closure target are two different numbers, and `CPU_HZ` must track
  the real one) and `BUG-UART`.
- `docs/CORE.md` + the per-stage docs (`docs/{IFU,IDU,IEU,LSU,WBU,HAZARD}.md`),
  `docs/SOC.md`, `docs/INTERCONNECT.md`, `docs/MEMORY.md` for how the pipeline,
  the OBI interconnect, and memory actually work.
- `docs/FPGA.md` for the Anvil/F4PGA flow, board wrapper, and clock frequency
  details.

## Build & verify

```sh
cd tb/unit/<module>   # or tb/core, or tb/soc for the whole system
make                  # options: WAVES=1, TESTCASE=<test>, SIM_BUILD=<dir>
```

Needs `cocotb` (`pip install -r requirements.txt`) and Verilator ≥ 5.036 on
`PATH`. If the repo is on a cloud-synced drive, build outside it:
`make SIM_BUILD=/tmp/sb`.

Software + FPGA flow, from the repo root:

```sh
make APP=hello all                 # compile sw/examples/hello, synthesize, flash
make APP=hello sw                  # just compile
make BOARD=nexys-50t all           # target the Nexys A7-50T instead of the 100T
python3 scripts/anvil_flow.py ...  # the flow directly (flatten/convert/build/program)
```

`docker/` has an image with the whole toolchain (Anvil, F4PGA, sv2v, RISC-V
GCC, openFPGALoader, Verilator, cocotb) if the host doesn't have it —
`make docker-build`, `make docker-shell`, `make docker-<target>`.

## Toolchain locations on this machine

When investigating build/synthesis issues, the actual installed toolchain
(not just what's documented) is worth checking directly:

- `~/opt/anvil/` — Anvil itself (`anvil.py`, `boards.json`: the per-board
  part/target/constraints table `anvil init` and this project's
  `scripts/anvil_flow.py` both read).
- `~/opt/sv2v/` — the SystemVerilog-to-Verilog converter Anvil's flow needs.
- `~/opt/f4pga/`, `~/miniconda3/envs/xc7/` — the F4PGA/VPR/yosys toolchain
  (conda env `xc7`). VPR's board-specific architecture XML (under
  `~/opt/f4pga/xc7/share/f4pga/arch/<device>/arch.timing.xml`) is the source
  of truth for what hard primitives (MMCM, PLL, ...) a given part actually
  models — check there before assuming a Xilinx primitive will place/route.
- `~/f4pga-examples/` — upstream F4PGA example designs; useful as a reference
  for patterns proven to work in *this specific* open-source flow (which
  doesn't support everything a Vivado-based flow would).
- Toolchain install script: `docker/Dockerfile` pulls it from a pinned commit
  of an external repo (`ADD --checksum=...`); update both the commit and the
  checksum together if it needs bumping, never just the URL.

## FPGA / board facts

- Target boards: Nexys A7-100T (default) and Nexys A7-50T — same baseboard,
  smaller die on the 50T. `scripts/anvil_flow.py --board` and the root
  `Makefile`'s `BOARD=` select between them; `fpga/anvil/Nexys-A7-*-Master.xdc`
  must be kept in sync (same pin assignments) if the board wrapper's port
  list changes.
- The board's on-board oscillator is **100 MHz**, not whatever the SoC
  actually runs at — see `KnownBugs.md` (`BUG-CLOCK`) before changing
  anything clock-related. `CPU_HZ` (`sw/rules.mk`, `sw/bsp/bsp.h`) must match
  the SoC's *real* operating clock, which is not necessarily the same as the
  XDC's synthesis-closure target constraint.
- This toolchain's XDC→SDC conversion follows a declared clock through
  combinational wiring but **not** through a register or a clock-management
  primitive (confirmed empirically — see `BUG-CLOCK`). A clean
  `report_timing.setup.rpt` from a build with a clock divider in the design
  does not, by itself, prove that divided domain's timing is safe.

## Homework branches

Branches named `hwN` (e.g. `hw1`) carry course assignment content on top of
the base core/SoC. On those branches:

- `solutions/` holds instructor-only reference solutions and grading
  scripts (`grade.sh`). It's git-ignored (`.gitignore`) and must **never**
  be committed or pushed to any branch students can see, and neither should
  a working tree that has a reference solution's files copied over the
  starter RTL (`solutions/*/apply.sh` does this for local testing — always
  revert or stash those changes before committing/pushing on a homework
  branch, and never cherry-pick them onto `main`).
- `docs/LectureNotes/HW*.md` is the student-facing assignment text;
  `docs/LectureNotes/HW*_bonus.md` is the optional extension.
- Hidden tests (in `solutions/*/hidden/`, copied into `tb/` by `grade.sh`)
  must stay consistent with whatever is actually required vs. bonus in the
  assignment text — if required/bonus scope changes, check the hidden tests
  too, not just the visible ones in `tb/`.

## What Claude should generally do here

- Verify RTL/toolchain claims empirically when the toolchain is available
  (build, run the testbench, read the actual timing report) rather than
  reasoning from documentation alone — this flow has several non-obvious,
  undocumented limitations that are only discoverable by trying.
- Prefer fixing root causes (e.g. an actual clock divider, a real shared
  comparator) over narrower workarounds, but measure before and after —
  several plausible-looking RTL changes in this design's history turned out
  to help less than expected once actually synthesized and timed.
- Keep `KnownBugs.md` up to date when a non-obvious bug or toolchain gotcha
  is found and fixed; future sessions (and future TAs) rely on it.
