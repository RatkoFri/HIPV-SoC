# Memory subsystem

The HIPV SoC uses **one** true dual-port RAM behind **two** OBI slave ports: port A
serves the instruction window, port B the data window. Both windows alias the same
physical words, so the machine is von Neumann (one image, `lw` can read code and
rodata) while instruction fetch and data access still proceed in the same cycles.

Files: `rtl/mem/obi_ram.sv` (top), `rtl/mem/obi_ram_port.sv` (per-port OBI
controller), `rtl/mem/sync_dual_port_RAM.sv` (RAM primitive).
Testbench: `tb/unit/obi_ram/`. Image tooling: `scripts/mkmem.py`,
`rv32i.write_mem()`.

## Structure

```
  IMEM window ──> OBI port A ──> obi_ram_port ──┐
                                                ├──> sync_dual_port_RAM
  DMEM window ──> OBI port B ──> obi_ram_port ──┘    (INIT_FILE image)
```

## Why true dual-port

| Primitive | Ports | Verdict |
|-----------|-------|---------|
| `sync_single_port_RAM` | 1 R/W | Fetch and data serialise on every access |
| `sync_simple_dual_port_RAM` | 1 R + 1 W | Only one read port: a load and a fetch would collide |
| `sync_dual_port_RAM` | 2 × R/W | **Used.** Fetch reads on A while the LSU reads *or writes* on B |

True dual-port also maps directly onto FPGA BRAM TDP mode, and its 1-cycle
synchronous read matches OBI exactly: address phase in cycle N, `rvalid` in N+1.

All three primitives are kept in `rtl/mem/`; the two unused ones remain as teaching
material.

## OBI port controller

`obi_ram_port` is the buffer between the bus and the raw RAM port. It captures the
request (address, write data, byte enables) at grant, so the bus is released while the
RAM completes.

| Access | Sequence | Response latency |
|--------|----------|------------------|
| read | grant + RAM read → data | 1 cycle |
| word write (`sw`) | grant + RAM write | 1 cycle |
| `sb` / `sh` | grant + RAM read → merge + write back | 2 cycles |

**Byte enables by read-modify-write.** The RAM primitive has no byte write enables, so
sub-word stores read the old word, merge the enabled bytes
(`(old & ~mask) | (new & mask)`), and write it back — one extra cycle. The alternative,
four byte-wide write-enable lanes in the primitive, is faster and is the natural
extension exercise; this way the primitive stays as simple as the uploaded version.

Measured in `tb/unit/obi_ram/test_timing`: 1, 1 and 2 cycles respectively.

## Aliasing and concurrency

Both OBI ports address the same array, so a word written through the data window is
visible through the instruction window and vice versa — verified in `test_aliasing`,
in both directions. That also makes self-modifying code demonstrable.

Concurrency is verified structurally in `test_concurrent_ports`: both ports are granted
in the same cycle and assert `rvalid` in the same cycle. Note where the bus phases live
— the address phase occupies the window between the falling and rising edge, so a
monitor that samples only on clock edges will miss it; the test drives both ports by
hand for that reason.

Simultaneous writes to the same word from both ports are undefined, exactly as in real
BRAM. The crossbar never generates this case: each window is a separate slave and each
master keeps one transaction outstanding.

## Initialization (synthesis time)

`INIT_FILE` is a `$readmemh` image applied in an `initial` block at elaboration. This is
synthesis-time initialization: Vivado folds the contents into the BRAM initialization
of the bitstream, and Verilator reads the same file in simulation. No JTAG, no SPI
flash loader, no boot ROM.

Format: one 32-bit word per line, 8 hex digits, ascending word address from word 0.

Build an image from a linked binary:

```sh
riscv32-unknown-elf-objcopy -O binary prog.elf prog.bin
python3 scripts/mkmem.py --bin prog.bin -o mem_init.hex --words 16384
```

or straight from the Python assembler used by the testbenches:

```python
from rv32i import addi, sw, jal, write_mem
write_mem([addi(1, 0, 5), sw(1, 0, 0), jal(0, 0)], "mem_init.hex", words=16384)
```

Both produce byte-identical files (checked). Pass the image to the RTL:

```systemverilog
obi_ram #(.ADDR_WIDTH(14), .INIT_FILE("mem_init.hex")) mem(...);
```

`--words` pads to the memory depth with `nop`, and refuses images that do not fit.
Unset `INIT_FILE` (the default `""`) leaves the array uninitialized.

`tb/unit/obi_ram` demonstrates the full flow: its Makefile generates `mem_init.hex`
before elaboration and passes it through `-GINIT_FILE`, exactly as a synthesis flow
would; `test_init_image` then checks the values are readable from both ports at reset.

## Changes to the uploaded primitives

The three uploaded files did not compile as written. Fixes, applied identically to all
three:

- `module #(params) name (...)` → `module name #(params) (...)` (parameter list must
  follow the module name);
- `inital` → `initial`;
- the hard-coded `$readmemh("mem_init.txt", mem)` became the `INIT_FILE` parameter,
  guarded so an empty string skips initialization;
- `sync_simple_dual_port_RAM`: missing comma between the read and write port groups,
  and the `data_out` / `data_reg` name mismatch;
- `sync_single_port_RAM`: trailing comma after the last port.

## Known simplifications

- Sub-word stores cost an extra cycle (RMW); byte write enables in the primitive would
  remove it.
- No error response: out-of-range addresses within a window wrap (the port uses only
  the low address bits). The crossbar's decode error covers addresses outside the
  windows.
- IMEM and DMEM windows alias completely; there is no protection preventing a program
  from overwriting its own code.
