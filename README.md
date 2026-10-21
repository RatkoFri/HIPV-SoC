# HIPV — HIP RISC-V SoC

Pedagogical 5-stage pipelined RV32I core and SoC, developed for lectures.

- Coding standard: `NamingConvention.md`; project layout: `FolderStructure.md`
- Software (bare-metal C, BSP, examples): `sw/README.md`
- FPGA synthesis (Anvil / F4PGA, Nexys A7-100T): `docs/FPGA.md`
- Docker toolchain (Anvil, F4PGA, RISC-V GCC, openFPGALoader): see [Docker](#docker) below
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

## Docker

`docker/` holds an image with the whole FPGA toolchain: Anvil, F4PGA, sv2v,
the RISC-V GCC and openFPGALoader. The top-level Makefile drives it:

    make docker-build              # build the image (once; downloads several GB)
    make docker-shell              # shell in the container, repo mounted at /work
    make docker-all APP=blink      # any Makefile target, prefixed with docker-

Inside the container the user has your UID/GID, so generated files belong to you.

**USB on Linux:** the container sees USB devices automatically, including a
board plugged in after it started, so `make docker-program` and the UART
console (`/dev/ttyUSB*`) work. `docker/run.sh` bind-mounts the host's `/dev`
and lets the container use USB, USB-serial and CDC-ACM devices, without
running it `--privileged`.

**macOS / Windows:** Docker Desktop runs containers in a VM that cannot reach
USB devices. Build in the container, then flash from the host:

    make docker-fpga APP=blink
    brew install openfpgaloader    # once
    make program-host

## Acknowledgments

The Docker setup is based on [anvil-docker](https://github.com/jurevreca12/anvil-docker)
by Jure Vreča ([@jurevreca12](https://github.com/jurevreca12)), which packages the
[Anvil](https://github.com/LogiSmith/Anvil) / F4PGA installer in a container. Thank you, Jure!
