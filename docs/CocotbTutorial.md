# cocotb tutorial

A hands-on introduction to verifying SystemVerilog with cocotb and Verilator, using two
small examples that you can run and edit. Everything here is the same style used in the
HIPV testbenches, so after working through it `tb/unit/*` should read naturally.

Runnable code:

- `docs/cocotb_tutorial/01_alu/` — combinational circuit (`tiny_alu.sv`)
- `docs/cocotb_tutorial/02_counter/` — synchronous circuit (`counter.sv`)

Each directory has the DUT, a heavily commented `test_*.py`, and a standalone Makefile.

## 1. What cocotb is

cocotb replaces the SystemVerilog testbench with Python. The DUT is still compiled by a
simulator (Verilator here); cocotb attaches to it through VPI and gives you a Python
handle to every signal. The test is a Python coroutine: you assign to inputs, `await`
simulation time or a clock edge, and read outputs back.

Why it is pleasant for teaching:

- No `initial` blocks, no fork/join — plain Python control flow.
- Reference models, random stimulus, file I/O and data structures come for free.
- The same test runs against any supported simulator.

The mental model that matters: **your Python code and the simulator take turns.** While
your coroutine runs, simulation time is frozen. Time only advances when you `await` a
trigger. Assignments to inputs are *scheduled* and take effect when time advances — this
is the single most common source of confusion for beginners.

## 2. Setup

```sh
pip install cocotb          # or: pip install -r requirements.txt
verilator --version         # needs >= 5.036 for cocotb 2.x
```

Run the first example:

```sh
cd docs/cocotb_tutorial/01_alu
make
```

You should see a table of tests with `PASS`. Useful options in every example:

| Command | Effect |
|---------|--------|
| `make` | run all tests |
| `make TESTCASE=test_zero_flag` | run one test |
| `make WAVES=1` | also write `dump.vcd` (open with GTKWave) |
| `make SIM_BUILD=/tmp/build` | build outside the source tree (needed on OneDrive) |
| `make clean` | remove build output |

## 3. Anatomy of a cocotb setup

Three files per testbench:

**The DUT** (`tiny_alu.sv`) — ordinary synthesizable SystemVerilog, nothing special.

**The test** (`test_tiny_alu.py`) — Python. Functions decorated with `@cocotb.test()`
are collected and run in order. Each receives `dut`, a handle to the top-level module;
`dut.A`, `dut.Y` etc. are signal handles.

**The Makefile** — tells cocotb which simulator, sources, top module and Python module
to use:

```make
SIM             = verilator          # simulator
TOPLEVEL_LANG   = verilog            # SystemVerilog counts as "verilog"
VERILOG_SOURCES = $(PWD)/tiny_alu.sv # RTL files, in dependency order
TOPLEVEL        = tiny_alu           # top-level module name
MODULE          = test_tiny_alu      # Python file (no .py) with the tests
include $(shell cocotb-config --makefiles)/Makefile.sim
```

`TOPLEVEL` must match the module name, `MODULE` must match the Python filename. Getting
these two mixed up is the classic first error.

## 3b. What happens behind the scenes

Nothing in `test_tiny_alu.py` says "run me", and you never execute the Python file
directly. So who calls your tests? Short answer: **the simulator does.** Your Python is
not the program — the compiled simulation is, and it loads Python as a plugin.

### The chain, end to end

```
  make
    │  reads your Makefile, then cocotb's Makefile.sim → Makefile.verilator
    │
    ├─1─ VERILATE:  verilator -cc --exe --vpi --public-flat-rw
    │               --prefix Vtop -o Vtop <your .sv files> verilator.cpp
    │               → C++ model of the DUT in $(SIM_BUILD)
    │
    ├─2─ COMPILE:   make -C sim_build -f Vtop.mk
    │               → sim_build/Vtop, a normal executable,
    │                 linked against libcocotbvpi_verilator.so
    │
    └─3─ RUN:       COCOTB_TEST_MODULES=test_tiny_alu \
                    COCOTB_TOPLEVEL=tiny_alu ... ./sim_build/Vtop
                       │
                       ├─ verilator.cpp main() starts the simulation
                       ├─ vlog_startup_routines_bootstrap() → VPI library loads
                       ├─ libcocotbvpi embeds a CPython interpreter
                       ├─ cocotb imports $COCOTB_TEST_MODULES  ← your test file
                       ├─ collects every @cocotb.test() object it finds
                       └─ runs them one at a time, writing results.xml
```

Three separate phases, and it is worth knowing which one an error came from: a syntax
error in SystemVerilog fails in step 1, a missing signal in Python fails in step 3.

### Step 1 — verilate

`make` does not run your Makefile alone; your file sets a few variables and then
includes cocotb's, which supplies the recipes. The important flags cocotb adds:

| Flag | Why |
|------|-----|
| `-cc --exe` | translate SystemVerilog to C++ and build an executable |
| `--vpi` | enable VPI, the standard C API that lets external code inspect and drive signals |
| `--public-flat-rw` | keep signals visible and writable; Verilator would otherwise optimise them away, and `dut.A.value = 3` would fail |
| `--prefix Vtop -o Vtop` | fixed names so the shim can `#include "Vtop.h"` |
| `--timescale 1ns/1ps` | from `COCOTB_HDL_TIMEUNIT`/`TIMEPRECISION` |
| `--trace` | only when you pass `WAVES=1` (our examples), hence no VCD by default |

Note the extra source file on the command line: `verilator.cpp`, shipped inside cocotb.
That is the `main()` of the simulation — your DUT alone has no entry point.

### Step 2 — compile

`Vtop.mk` (generated by Verilator) compiles the C++ model plus the shim and links
`libcocotbvpi_verilator.so`. The output `sim_build/Vtop` is an ordinary ELF executable.

### Step 3 — run

The recipe exports environment variables and runs the binary. That is the entire
interface between `make` and cocotb:

| Variable | Set from | Meaning |
|----------|----------|---------|
| `COCOTB_TEST_MODULES` | `MODULE` | Python module(s) to import and search for tests |
| `COCOTB_TOPLEVEL` | `TOPLEVEL` | HDL top module, becomes the `dut` handle |
| `COCOTB_TEST_FILTER` | `TESTCASE` | regex selecting which tests to run |
| `PYGPI_PYTHON_BIN` | auto | which Python interpreter to embed |
| `PYTHONPATH` | your Makefile | where to import test modules from (this is how `tb/common/` is shared in HIPV) |

You can bypass `make` entirely to prove the point — this really works:

```sh
cd sim_build
PYGPI_PYTHON_BIN=$(python3 -m cocotb_tools.config --python-bin) \
COCOTB_TEST_MODULES=test_tiny_alu COCOTB_TOPLEVEL=tiny_alu TOPLEVEL_LANG=verilog \
COCOTB_TEST_FILTER=test_zero_flag PYTHONPATH=.. ./Vtop
```

`make` is convenience, not magic. (If you forget `PYGPI_PYTHON_BIN`, the binary prints
`Can't initialize Python interpreter` — the VPI library found no interpreter to embed.)

### How your tests get found

Inside the running simulation, cocotb does the equivalent of:

```python
mod = importlib.import_module("test_tiny_alu")   # your file, imported normally
for name, obj in vars(mod).items():
    if isinstance(obj, Test):                    # what @cocotb.test() produced
        register(obj)
```

So `@cocotb.test()` is not a "run this" instruction — it wraps your coroutine in a
`Test` object. Importing the module creates those objects; cocotb then scans the
module's namespace for them and queues them. Consequences worth remembering:

- **Your test file is imported, so top-level code runs at import time.** Keep heavy
  work inside the tests.
- **Discovery scans the module namespace, not the source text.** What counts is a
  module-level *name* bound to a `Test` object. A test defined inside a function but
  assigned at module level (`t = make_test()`) is found and runs; one created inside a
  function and never bound at module level, or under `if False:`, is silently skipped.
  A silently-missing test is worse than a failing one — check the count in the summary
  table matches what you expect.
- **Tests run in definition order**, sequentially, sharing **one** simulation — the DUT
  is *not* re-elaborated between tests. Verified: a test that leaves `Y = 99` is
  followed by a test that reads `Y = 99` before driving anything. That is why every
  test in our examples calls `start()` and applies its own reset; without it, state
  leaks in from whichever test ran before, and your test passes or fails depending on
  the order.
- **Helper functions are not tests.** `do_op` and `start` have no decorator, so they
  are not `Test` objects, are ignored by discovery, and only run when a test calls
  them.

### Who owns time

`verilator.cpp` runs the simulation loop; cocotb registers VPI callbacks and gets
control at specific points:

```
  loop:
    eval the design until it settles
    call cbReadWriteSynch callbacks   ← cocotb applies scheduled input writes
    call cbReadOnlySynch callbacks    ← cocotb reads outputs
    jump time forward to the next registered callback deadline
    call timed callbacks              ← this is what wakes your Timer / edge awaits
```

This is the mechanism behind the rule from section 4: when you write `dut.A.value = 3`,
cocotb only *schedules* the write; it lands at the next ReadWrite point, which is why
time must advance before the effect is visible. The clock is no different — `Clock`
is just a coroutine registering timed callbacks. Notice the last step of the loop:
simulation time jumps straight to the next registered callback. If no cocotb coroutine
is waiting for anything, there is no deadline and the simulation ends — which is
exactly what a "test hangs then finishes early" symptom means.

### After the run

The simulation writes `results.xml` (JUnit format, the same shape CI tools consume) and
`make` runs `cocotb_tools.check_results` on it, which is what turns a failed test into a
nonzero exit status. That is why a failing test makes `make` itself fail — useful for
`make -C ... && make -C ...` style regressions.

### In HIPV

Identical, one layer up: `tb/common/Makefile.include` centralises `SIM`, the Verilator
flags, `WAVES`, and the `PYTHONPATH` export that makes `obi.py` and `rv32i.py`
importable; each `tb/*/Makefile` only sets `TOPLEVEL`, `MODULE` and `VERILOG_SOURCES`.
`VERILOG_SOURCES` must list every file the DUT needs (packages first) — Verilator does
not search for them.

## 4. Example 1 — combinational: `tiny_alu`

The DUT is an 8-bit ALU: `Op` selects add/sub/and/or, and `Zero` flags a zero result.
No clock. Open `docs/cocotb_tutorial/01_alu/test_tiny_alu.py` and follow along.

### Drive, wait, check

```python
@cocotb.test()
async def test_single_add(dut):
    dut.A.value = 3
    dut.B.value = 4
    dut.Op.value = ADD
    await Timer(1, unit="ns")        # let the assignment take effect
    assert dut.Y.value == 7
```

Three things to note:

1. **`.value` on both sides.** `dut.A.value = 3` writes, `dut.Y.value` reads. Assigning
   to `dut.A` directly (without `.value`) silently rebinds the Python name and does
   nothing to the simulation.
2. **The `await` is mandatory.** Delete it and the test fails: `Y` still holds the old
   value because no simulation time has passed. Measured on this DUT — after setting
   `A = B = 100` on top of a previous `3 + 4`, reading `Y` immediately returns `7`, and
   only after `await Timer(1, unit="ns")` does it become `200`. For combinational logic
   any nonzero delay works; `Timer(1, unit="ns")` is conventional.
3. **`dut.Y.value` compares like an integer** but is a `LogicArray`. Use
   `int(dut.Y.value)` when you need arithmetic or a formatted message; `hex()` needs the
   `int()` too.

### A helper per stimulus

Repeating the same four lines gets noisy, so wrap it:

```python
async def do_op(dut, a, b, op):
    dut.A.value, dut.B.value, dut.Op.value = a, b, op
    await Timer(1, unit="ns")
    return int(dut.Y.value), int(dut.Zero.value)
```

Helpers like this are the backbone of every real testbench — `push_instr` in
`tb/unit/idu/`, `push_op` in `tb/unit/ieu/` are exactly the same idea.

### Directed, random, exhaustive

The example shows the three styles you will keep reaching for:

- **Directed** (`test_all_operations`, `test_zero_flag`) — one case per behaviour you
  care about, including the interesting edge: 8-bit wraparound making `Zero` fire
  after `200 + 56`.
- **Random against a reference model** (`test_random`) — a Python function
  `alu_model(a, b, op)` says what the answer should be; 200 random inputs compare RTL
  against it. Seed the RNG (`random.seed(1)`) so a failure is reproducible.
- **Exhaustive** (`test_exhaustive_low_nibble`) — for small state spaces, just try
  everything. 1024 cases run in a fraction of a second. If exhaustive is affordable,
  prefer it over random.

The reference model is the key idea: it states *what* to compute, independently of
*how* the RTL does it. Two independent descriptions disagreeing is how bugs surface.

### Failure messages

```python
assert y == expected, f"op={op} a={a} b={b}: got {y}, expected {expected}"
```

Write the message so that the failure alone tells you which stimulus broke — you will
not want to re-derive it from a waveform.

## 5. Example 2 — synchronous: `counter`

A 4-bit up counter with synchronous reset, enable, and a combinational `Wrap` flag.
Open `docs/cocotb_tutorial/02_counter/test_counter.py`.

### Starting a clock

```python
cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
```

`Clock(...).start()` is a coroutine that toggles the signal forever;
`cocotb.start_soon` runs it in the background, concurrently with your test. Nothing
happens until your test awaits something — background coroutines only advance when the
foreground yields.

### Reset, then a settling edge

```python
async def start(dut, cycles=2):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.en.value = 0
    dut.reset.value = 1
    await ClockCycles(dut.clk, cycles)   # wait N rising edges
    dut.reset.value = 0
    await FallingEdge(dut.clk)
```

Every synchronous testbench in this project has a `start()` like this. Factor it out
immediately; you will call it from every test.

### Reading `await start(dut)` closely

Every test in the counter example begins with this one line, so it is worth taking
apart word by word.

**`start` is not cocotb API.** It is the helper defined a few lines above in the same
file — an ordinary function you wrote. Nothing in the name is special.

**`async def` means calling it does not run it.** `start(dut)` on its own just builds a
*coroutine object* and hands it back, the way calling a generator function returns a
generator. Something has to drive it. There are exactly two ways:

| Form | Meaning |
|------|---------|
| `await start(dut)` | run it **now, inline**, and suspend this test until it finishes |
| `cocotb.start_soon(start(dut))` | run it **concurrently**; the caller continues immediately |

`start()` itself uses both, one line apart: the clock is launched with `start_soon`
(it must keep toggling forever, in the background), while the test awaits `start()` as
a whole (it must be finished before the test body begins).

**`await` is also where simulation time passes.** A plain function call cannot advance
time; only awaiting a trigger can. Since `start()` internally awaits `ClockCycles` and
`FallingEdge`, awaiting it advances the clock. Measured on this DUT with a 10 ns clock,
`await start(dut)` takes the test from t = 0 to t = 15 ns:

```
t=0ns    start() entered; clock coroutine launched with start_soon
t=0ns    en=0, reset=1 scheduled
t=0ns    rising edge 1  ┐ await ClockCycles(dut.clk, 2)
t=10ns   rising edge 2  ┘
t=10ns   reset=0 scheduled
t=15ns   falling edge   ← await FallingEdge(dut.clk)
t=15ns   start() returns; the test body resumes here
```

(The clock rises at 0, 10, 20 … and falls at 5, 15, 25 …, so two rising edges land at
t = 10 and the next falling edge at t = 15. This is why every counter test reports a
15 ns baseline.)

So the single line means: *start a clock in the background, hold reset for two clock
cycles, release it, and leave me parked on a falling edge with the DUT in a known
state.* The test body can then assume a running clock and `Count == 0`.

**Why a helper at all?** Because tests share one simulation (section 3b), each test must
establish its own known state — otherwise it inherits whatever the previous test left
behind. Putting that in `start()` means the reset protocol is written once and cannot
drift between tests.

**The failure mode to know.** Write `start(dut)` without `await` and Python does not
raise an error — it emits a `RuntimeWarning: coroutine 'start' was never awaited` and
carries on. No clock is started, no reset is applied, and no time passes. The test then
"passes" in 0.00 ns purely because Verilator initialises the counter to zero:

```
0.00ns WARNING  RuntimeWarning: coroutine 'start' was never awaited
0.00ns INFO     Count reads as: 0000
** test.forgot_await   PASS   0.00 ns **
```

A green result that proves nothing. Two habits catch it: treat that warning as an
error, and glance at the `SIM TIME` column — a synchronous test that took 0 ns never
ran a clock.

### The sampling convention

This is the one rule to internalise for clocked designs:

> **Drive inputs after a rising edge; sample outputs on the falling edge.**

```python
await RisingEdge(dut.clk)     # the edge that updates the flip-flops
await FallingEdge(dut.clk)    # now safely read the new state
assert dut.Count.value == expected
```

Reading immediately after `RisingEdge` without letting time advance returns the
pre-edge value, because your coroutine resumes before the DUT's non-blocking
assignments have settled. Measured on this counter: right after the first counting
edge `Count` still reads `0`, and only after `await Timer(1, unit="ns")` does it read
`1`. `test_sampling_convention` demonstrates that minimal fix; the falling-edge
convention is the better habit because it also keeps your stimulus far from the DUT's
sampling edge.

The available triggers, in practice:

| Trigger | Use |
|---------|-----|
| `RisingEdge(sig)` / `FallingEdge(sig)` | clock edges, and waiting on a signal change |
| `ClockCycles(clk, n)` | skip `n` edges |
| `Timer(t, unit="ns")` | fixed delay; settling in combinational tests |
| `with_timeout(...)` | bound a wait so a hang fails instead of running forever |

### Combinational outputs of a sequential block

`Wrap = en & (Count == MAX)` is combinational, so it is high *during* the cycle whose
edge will wrap the counter — not after. `test_wrap` checks exactly that ordering, and
`test_wrap_needs_enable` checks that a disabled counter sitting at MAX does not flag a
wrap. Timing questions like "is this flag before or after the edge?" are where
testbenches earn their keep.

### Background monitors

`count_monitor` runs concurrently and keeps its own Python copy of the counter:

```python
async def count_monitor(dut, errors):
    model = 0
    while True:
        await RisingEdge(dut.clk)
        if dut.reset.value:   model = 0          # values before the edge
        elif dut.en.value:    model = (model + 1) % (MAX + 1)
        await FallingEdge(dut.clk)               # compare the new state
        if int(dut.Count.value) != model:
            errors.append(...)
```

The test then wiggles `en` randomly for 100 cycles and only asserts at the end. This
is a scoreboard in miniature — the same structure that scales up to the OBI memory
model in `tb/common/obi.py`, which serves bus requests in the background while the
core-level test just runs a program.

Note the ordering: inputs are sampled *before* the edge (they decide the next state),
the DUT output is compared *after* it. Getting this backwards produces off-by-one-cycle
false failures, a classic beginner bug.

## 6. Debugging

**Print things.** Every DUT has a logger:

```python
dut._log.info("Count=%d Wrap=%d", int(dut.Count.value), int(dut.Wrap.value))
```

**Look at waves.** `make WAVES=1` writes `dump.vcd`; open it in GTKWave. Waveforms
answer "when did this change?" much faster than prints.

**Run one test.** `make TESTCASE=test_wrap` narrows the output.

**Common errors and what they mean:**

| Symptom | Cause |
|---------|-------|
| Output has the previous value | No `await` between driving and sampling |
| `AttributeError: ... has no attribute` | Signal name mismatch (case-sensitive), or the signal was optimised away — Verilator needs `--public-flat-rw`, which cocotb passes automatically for the top level |
| Test hangs, or ends instantly at time 0 | Waiting on an edge that never comes (no clock started, or a handshake that never completes). With nothing scheduled, the sim loop finds no next deadline and simply exits — see section 3b. Bound waits with a loop counter or `with_timeout` |
| A test you wrote never appears in the summary | Not discovered — it must be bound to a module-level name (section 3b) |
| Test passes alone, fails in the suite | Leftover DUT state: all tests share one simulation. Apply reset in every test |
| Value is `X` | Uninitialised register — drive reset, or check `.is_resolvable` before comparing |
| `make` reuses stale build | `make clean`, or use a fresh `SIM_BUILD` |

**Assert on `int(...)` when comparing to Python ints** if a signal might contain `X`;
`dut.sig.value == 5` on an unresolved value raises rather than failing cleanly.

## 7. From here to the HIPV testbenches

The project testbenches use exactly these building blocks, one layer up:

| Tutorial concept | In HIPV |
|------------------|---------|
| `do_op` helper | `push_op` (`tb/unit/ieu`), `push_instr` (`tb/unit/idu`) |
| `start()` with clock + reset | every `tb/unit/*/test_*.py` |
| Falling-edge sampling | used throughout |
| Reference model | `alu_model` → RV32I encoders in `tb/common/rv32i.py` |
| Background monitor | OBI slave model in `tb/common/obi.py` |
| Shared code | `tb/common/` on `PYTHONPATH` via `tb/common/Makefile.include` |

Read them in this order: `tb/unit/wbu` (smallest), `tb/unit/ifu` (handshake + bus
model), `tb/core` (whole programs).

## 8. Exercises

1. Add an `xor` opcode to `tiny_alu` — but the `Op` field is full. Widen it to 3 bits,
   extend the reference model, and watch the exhaustive test catch a forgotten case if
   you leave the model unchanged.
2. Add a `Carry` output to the adder path and write the directed test for
   `255 + 1` before you write the RTL.
3. Make the counter a down counter under a `dir` input; extend `count_monitor` to model
   both directions.
4. Add a `load` input (`Count <= Din`) to the counter and decide the priority against
   `reset` and `en` — then write the test that pins that decision down.
5. Deliberately break something (change `+ 1` to `+ 2`) and confirm the tests fail with
   a message that tells you what went wrong. A test suite that never fails has never
   been proven to work.
