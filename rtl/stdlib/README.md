# std-lib primitives

Support modules from https://github.com/jurevreca12/std-lib (rev `de7f5c8`, 2026-07-14),
the dependency declared in the `Bender.yml` of `obi_timer` / `obi_uart` / `obi_gpio`.

| File | Used by |
|------|---------|
| `register.sv` | obi_uart, obi_gpio, obi_timer (async active-low reset, clock enable) |
| `register_wclear.sv` | cntr |
| `cntr.sv` | obi_timer (64-bit up counter) |

## Deviation from upstream: synchronous reset

Upstream `register.sv` and `register_wclear.sv` use an **asynchronous** reset
(`always_ff @(posedge clk or negedge rstn)`). The project coding standard requires
synchronous reset throughout, so both were changed to `always_ff @(posedge clk)` with
the reset test inside, marked with a `HIPV:` comment. Because every peripheral register
in `obi_uart`, `obi_gpio` and `obi_timer` is built from these two primitives, this one
change makes the whole peripheral subsystem synchronously reset.

`rstn` stays active-low, so no instantiation inside the cores changes; the SoC adapters
convert the project's active-high `reset` to `rstn`. The UART's own logic (FSMs, baud
generators, buffers) already used synchronous reset.

Consequence to be aware of: reset now requires a running clock. Testbenches must hold
reset for at least one clock edge — `tb/unit/timer/test_synchronous_reset` verifies the
path explicitly (and was checked to fail when the reset is sabotaged).

Lint waivers: `config/periph.vlt`.
