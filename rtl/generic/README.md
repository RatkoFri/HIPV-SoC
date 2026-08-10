## Standard (generic) modules for HIPV

Reusable, parameterized leaf cells written in behavioral style. Datapath modules
instantiate these structurally, per `NamingConvention.md` (section 10). This file is
updated whenever a module is added or a new user of a module appears.

### Module inventory

| Module    | File         | Parameters  | Description                                    |
|-----------|--------------|-------------|------------------------------------------------|
| `flopenr` | `flopenr.sv` | `WIDTH = 8` | Flip-flop with synchronous reset and enable    |
| `mux2`    | `mux2.sv`    | `WIDTH = 8` | 2-to-1 multiplexer                             |
| `adder`   | `adder.sv`   | `WIDTH = 8` | Adder, `Y = A + B`                             |

### Port reference

- `flopenr #(WIDTH)` — `clk`, `reset`, `en`, `D[WIDTH-1:0]` → `Q[WIDTH-1:0]`.
  Reset is synchronous, active-high, clears `Q` to 0. `en` gates the update.
- `mux2 #(WIDTH)` — `D0`, `D1`, `S` → `Y`. `Y = S ? D1 : D0`.
- `adder #(WIDTH)` — `A`, `B` → `Y`. Plain combinational add, no carry out.

### Used by

| Module    | Instantiated in         | Instance name | Purpose                          |
|-----------|-------------------------|---------------|----------------------------------|
| `flopenr` | `rtl/core/ifu/ifu.sv`   | `pcreg`       | PC register, advanced by `PCEnF` |
| `flopenr` | `rtl/core/ifu/ifu.sv`   | `instrreg`    | Fetched instruction register (`InstrF`) |
| `mux2`    | `rtl/core/ifu/ifu.sv`   | `pcmux`       | Next-PC select (PC+4 vs. branch target) |
| `adder`   | `rtl/core/ifu/ifu.sv`   | `pcadd4`      | Sequential PC+4                  |

### Conventions for adding a module

- One module per file, file name equals module name.
- Behavioral style, parameterized width, synchronous reset where applicable.
- Add the module to the inventory and port reference tables above.
- Add every new instantiation to the "Used by" table.
- Add the file to `VERILOG_SOURCES` of any testbench whose DUT uses it.
