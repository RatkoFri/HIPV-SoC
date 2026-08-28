# FPGA

Bitstream builds for the HIPV SoC.

- `anvil/` — Anvil (F4PGA) project for the Digilent Nexys A7-100T:
  `top.sv` board wrapper, `config.json`, and the pin constraints. These are the
  sources; the build assembles a flattened scratch copy elsewhere.

Full instructions, including the three Anvil limitations this project works
around and the verified BRAM/synthesis results: **`docs/FPGA.md`**.

Quick start:

    make -C sw/examples/hello               # build a program
    python3 scripts/anvil_flow.py build     # flatten, sv2v, synthesise
    python3 scripts/anvil_flow.py program   # flash the board

`anvil_flow.py` assembles everything into `build/anvil-work/`, which is **wiped on
every run** — never edit anything in there.

Simulate the board wrapper before touching hardware: `make -C tb/fpga`.
