# IFU testbench (`test_ifu.py`)

cocotb testbench for `rtl/core/ifu/ifu.sv`. The Python side plays both neighbours of
the fetch stage: the OBI instruction-memory slave and the Decode stage on the
valid/ready handshake.

## Prerequisites

- Verilator ≥ 5.036 on `PATH`
- Python packages: `pip install -r requirements.txt` (repo root)

## Running

```sh
cd tb/unit/ifu
make
```

If the repo is on a cloud-synced drive (OneDrive), keep build output elsewhere:

```sh
make SIM_BUILD=/tmp/sim_build_ifu COCOTB_RESULTS_FILE=/tmp/ifu_results.xml
```

A summary table is printed at the end; `results.xml` holds the machine-readable
result.

Waveforms are off by default; enable them with `WAVES=1`:

```sh
make WAVES=1 SIM_BUILD=/tmp/sim_build_ifu_waves
```

then open `dump.vcd` (written into this test directory) with GTKWave. Use a clean
`SIM_BUILD` when toggling `WAVES`, since the Verilator flags change. `*.vcd` is
git-ignored.

To run a single test:

```sh
make TESTCASE=test_redirect
```

## Structure

- `imem_word(addr)` — deterministic fake instruction for an address; the checks
  recompute it instead of keeping a golden memory.
- `obi_imem(dut, gnt_delay, rvalid_delay)` — OBI slave coroutine, one outstanding
  transaction. Drives `ObiGntF` after `gnt_delay` cycles and `ObiRvalidF`/`ObiRdataF`
  `rvalid_delay` cycles after the grant. All driving happens on the falling edge so
  the DUT samples cleanly on the rising edge.
- `start(dut, ...)` — starts clock and slave, applies 2-cycle reset.
- `wait_valid(dut)` — waits for `ValidF`, returns `(PCF, InstrF)`; fails on timeout.

## Tests

| Test                    | Checks                                                       |
|-------------------------|--------------------------------------------------------------|
| `test_first_fetch`      | First instruction after reset comes from address 0           |
| `test_sequential_fetch` | Instructions arrive from 0, 4, 8, ... with `ReadyD` high     |
| `test_backpressure`     | `ValidF`/outputs hold steady while `ReadyD` is low           |
| `test_redirect`         | `PCSrcE` pulse fetches from `PCTargetE`, then target + 4     |
| `test_redirect_midfetch`| Stale response of an in-flight fetch is discarded (delay 4)  |
| `test_slow_memory`      | Sequential fetch correct with `gnt_delay=2`, `rvalid_delay=3`|

Memory latencies are per-test arguments to `start()`, so new corner cases are added by
calling `start(dut, gnt_delay=..., rvalid_delay=...)` in a new `@cocotb.test()`.
