# HIPV — HIP RISC-V SoC

Pedagogical 5-stage pipelined RV32I core and SoC, developed for lectures.

- Coding standard: `NamingConvention.md`; project layout: `FolderStructure.md`
- Interconnect: `docs/INTERCONNECT.md`
- Core documentation: `docs/CORE.md` (overview) and per-stage `docs/{IFU,IDU,IEU,LSU,WBU,HAZARD}.md`
- Standard modules: `rtl/generic/README.md`
- Learning cocotb: `docs/CocotbTutorial.md` (runnable examples in `docs/cocotb_tutorial/`)

## Status

| Component | State |
|-----------|-------|
| ifu, idu, ieu, lsu, wbu, hazard, hipv_core | implemented + tested |
| interconnect (obi_xbar, decoder, arbiter) | implemented + tested |
| SoC memories, peripherals, hipv_soc | not started |

## Verification

cocotb + Verilator. Run any testbench with:

    cd tb/unit/<module>   # or tb/core
    make                  # options: WAVES=1, TESTCASE=<test>, SIM_BUILD=<dir>

If the repo is on a cloud-synced drive, build outside it: `make SIM_BUILD=/tmp/sb`.
Python dependencies: `pip install -r requirements.txt`; Verilator >= 5.036 required.
