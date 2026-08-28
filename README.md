# HIPV — HIP RISC-V SoC

Pedagogical 5-stage pipelined RV32I core and SoC, developed for lectures.

- Coding standard: `NamingConvention.md`; project layout: `FolderStructure.md`
- Software (bare-metal C, BSP, examples): `sw/README.md`
- FPGA synthesis (Anvil / F4PGA, Nexys A7-100T): `docs/FPGA.md`
- SoC top level: `docs/SOC.md`; interconnect: `docs/INTERCONNECT.md`; memory: `docs/MEMORY.md`
- Core documentation: `docs/CORE.md` (overview) and per-stage `docs/{IFU,IDU,IEU,LSU,WBU,HAZARD}.md`
- Standard modules: `rtl/generic/README.md`
- Learning cocotb: `docs/CocotbTutorial.md` (runnable examples in `docs/cocotb_tutorial/`)

## Status

| Component | State |
|-----------|-------|
| ifu, idu, ieu, lsu, wbu, hazard, hipv_core | implemented + tested |
| interconnect (obi_xbar, decoder, arbiter) | implemented + tested |
| peripherals (obi_uart, obi_gpio, obi_timer + SoC adapters) | implemented + tested |
| memory (unified dual-port RAM + OBI wrapper, synth-time init) | implemented + tested |
| hipv_soc top level (core + xbar + RAM + uart/timer/gpio) | implemented + tested |
| software: BSP, linker script, C examples running on the SoC | implemented + tested |
| FPGA flow: Anvil project, board wrapper, module packaging | implemented, wrapper simulated (bitstream not yet built) |

## Verification

cocotb + Verilator. Run any testbench with:

    cd tb/unit/<module>   # or tb/core, or tb/soc for the whole system
    make                  # options: WAVES=1, TESTCASE=<test>, SIM_BUILD=<dir>

If the repo is on a cloud-synced drive, build outside it: `make SIM_BUILD=/tmp/sb`.
Python dependencies: `pip install -r requirements.txt`; Verilator >= 5.036 required.
