## Folder organization for HIPV (HIP RISC-V SoC)

1. Top-level layout

   ```
   HIPV/
   ├── docs/
   ├── rtl/
   ├── tb/
   ├── tests/
   ├── fpga/
   ├── syn/
   ├── config/
   ├── scripts/
   ├── requirements.txt
   └── README.md
   ```

   Verification uses cocotb with Verilator as the simulator, so there is no separate
   `sim/` folder — each testbench directory under `tb/` is self-contained with its own
   cocotb Python test(s) and Makefile.

2. `docs/` — project documentation
   - `Microarchitecture.md` — pipeline diagrams, stage descriptions, hazard handling.
   - `MemoryMap.md` — address map for memories and peripherals.
   - `LectureNotes/` — per-lecture material, if kept alongside the code.
   - `NamingConvention.md` and this file currently live at the project root rather than
     under `docs/`, so they are easy to find; move them into `docs/` if the root should
     stay minimal.

3. `rtl/` — synthesizable SystemVerilog source, one module per file
   - `rtl/generic/` — standard reusable leaf cells (flip-flops, muxes, adders, ...),
     behavioral style, parameterized; documented in `rtl/generic/README.md`, which also
     tracks where each module is used
   - `rtl/core/` — the RISC-V pipeline core
     - `ifu/` — Instruction Fetch Unit (`F` stage)
     - `idu/` — Instruction Decode Unit (`D` stage)
     - `ieu/` — Integer Execution Unit (`E` stage)
     - `lsu/` — Load/Store Unit (`M` stage)
     - `wbu/` — Writeback logic (`W` stage)
     - `hazard/` — hazard detection, forwarding, stall/flush control
     - `regfile/` — register file
     - `hipv_core.sv` — core top-level, connects the stages above
   - `rtl/mem/` — caches and on-chip memories (I$, D$, SRAM wrappers)
   - `rtl/periph/` — peripherals (UART, GPIO, timer, interrupt controller, ...)
   - `rtl/interconnect/` — OBI crossbar (`obi_xbar`), address decoder and arbiter;
     see `docs/INTERCONNECT.md`
   - `rtl/top/` — SoC top-level integration (`hipv_soc.sv`)

4. `tb/` — cocotb testbenches (Verilator as SIM), mirroring the `rtl/` hierarchy
   - `tb/common/` — shared Python: cocotb drivers, monitors, scoreboards, models, a common
     `Makefile.include` with the shared Verilator flags (`SIM = verilator`,
     `TOPLEVEL_LANG = verilog`, warning/coverage flags, `--trace` for waveform dumps)
   - `tb/unit/<module>/` — one directory per leaf RTL module, e.g. `tb/unit/ieu/`,
     `tb/unit/regfile/`, mirroring `rtl/core/<module>/`
     - `Makefile` — includes `tb/common/Makefile.include`, sets `TOPLEVEL`, `MODULE`,
       `VERILOG_SOURCES`
     - `test_<module>.py` — cocotb test(s) for that module
   - `tb/core/` — core-level testbench (`hipv_core`), same Makefile + `test_*.py` layout
   - `tb/soc/` — full SoC-level testbench (`hipv_soc`), same layout
   - simulation build artifacts (`sim_build/`, `.vcd`/`.fst`, `results.xml`) are
     Verilator/cocotb outputs and should be git-ignored

5. `tests/` — software/assembly test programs run on the core (loaded as memory images by
   the `tb/core` and `tb/soc` cocotb testbenches)
   - `tests/asm/` — hand-written directed assembly tests
   - `tests/riscv-tests/` — official RISC-V ISA compliance tests (as a submodule, if used)
   - `tests/c/` — C test programs, if a toolchain/linker script is provided

6. `requirements.txt` — Python dependencies for the verification flow (`cocotb`,
   `cocotb-bus`, `pytest`, `pytest-xdist` if used for parallel regression); Verilator itself
   is installed on the system/toolchain, not via pip.

7. `fpga/` — FPGA implementation
   - `fpga/constraints/` — pin/timing constraints (`.xdc`, `.sdc`)
   - `fpga/scripts/` — build/bitstream generation scripts

8. `syn/` — ASIC/logic synthesis scripts and constraints, kept separate from FPGA flow

9. `config/` — parameter packages and configuration
   - `config/hipv_pkg.sv` — core control encodings and RV32I opcodes
   - `config/hipv_soc_pkg.sv` — SoC address map, master/slave indices, arbiter policies
   - alternate configs (e.g. `config/minimal_pkg.sv`, `config/full_pkg.sv`) for different
     lecture stages or feature sets

10. `scripts/` — general build/utility scripts (lint, regression runner, formatting checks)

11. Notes
    - Each RTL module lives in its own file, matching the module name, per the naming
      convention (`NamingConvention.md`, section 10).
    - `rtl/` and `tb/` subfolders mirror each other so a module and its testbench are easy
      to locate side by side.
    - Keep tool-generated output (simulation logs, waveforms, synthesis results, build
      artifacts) out of version control via `.gitignore`; only scripts and constraints are
      checked in.
