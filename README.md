# HIPV-SOC — HIP RISC-V SoC

Pedagogical RISC-V pipelined SoC. See `NamingConvention.md` for the RTL coding
standard and `FolderStructure.md` for the project layout.

Verification uses [cocotb](https://www.cocotb.org/) with Verilator. Run a testbench with:

    cd tb/unit/<module> && make
