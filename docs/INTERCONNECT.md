# Interconnect — OBI crossbar

The HIPV SoC connects its two masters (instruction fetch, data) to five slaves through a
crossbar, so an instruction fetch and a load/store to *different* slaves proceed in the
same cycles. Only accesses to the same slave are serialised.

Files: `rtl/interconnect/obi_xbar.sv` (crossbar), `obi_decoder.sv` (address decode),
`obi_arbiter.sv` (per-slave arbitration). Address map: `config/hipv_soc_pkg.sv`.
Testbenches: `tb/unit/obi_decoder/`, `tb/unit/obi_arbiter/`, `tb/unit/obi_xbar/`.
Adding a slave: `docs/ADDING_A_SLAVE.md`.

## Topology

```
   MASTER_D (LSU) ─┐                                    ┌─> SLAVE_IMEM
                   ├─> decoder ─┐                       ├─> SLAVE_DMEM
   MASTER_I (IFU) ─┘            │  ┌────────────────┐   ├─> SLAVE_UART
                                ├─>│ per-slave      │──>├─> SLAVE_TIMER
                    arbiter ────┘  │ request mux    │   └─> SLAVE_GPIO
                    (one per slave)└────────────────┘
                                ┌────────────────────┐
   responses <──────────────────│ pending-slave regs │<── SRvalid / SRdata
                                │ (one per master)   │
                                └────────────────────┘
```

## Address map

| Slave | Base | Size | Notes |
|-------|------|------|-------|
| IMEM | `0x0000_0000` | 64 KiB | reset vector at 0; readable by the data master too, so `lw` can fetch rodata |
| DMEM | `0x1000_0000` | 64 KiB | |
| UART | `0x2000_0000` | 4 KiB | |
| TIMER | `0x2000_1000` | 4 KiB | |
| GPIO | `0x2000_2000` | 4 KiB | |

Regions must be power-of-two sized and naturally aligned: the decoder compares only the
address bits above the region size (`(Addr & ~(Size-1)) == Base`), which is one
comparator per region instead of two.

Anything outside every region asserts `DecErr`.

## Address phase

Each master has its own `obi_decoder`, producing a one-hot slave select. For every
slave, the crossbar collects the masters selecting it and an `obi_arbiter` picks one;
the winner's `Addr`/`We`/`Be`/`Wdata` are muxed onto that slave port and the grant is
routed back to that master.

`ARB_POLICY` selects the arbitration policy, so the two can be compared in a lab:

| Policy | Behaviour |
|--------|-----------|
| `ARB_FIXED` (0) | Lowest master index wins. `MASTER_D = 0`, so data beats fetch — combinational, no state. Under permanent contention the higher index starves (the arbiter test asserts exactly that). |
| `ARB_ROUND_ROBIN` (1) | Rotating priority; the pointer advances only when a grant is actually taken (`Update`). Fair, one pointer register per slave. |

Starvation is not a practical problem with fixed priority here because the LSU issues at
most one transaction per instruction, so fetch always gets gaps to use.

## Response phase — the interesting part

OBI separates the address phase (`req`/`gnt`) from the response phase
(`rvalid`/`rdata`), and responses carry no ID. So after granting, the fabric must
*remember* where each master's answer will come from. Each master therefore has:

- `PendValid[m]` — this master is waiting for a response;
- `PendSlave[m]` — which slave owes it.

Both are loaded on grant, and `MRvalid[m] = PendValid[m] & SRvalid[PendSlave[m]]`, with
`MRdata` muxed from the same slave.

This is correct **only because each HIPV master keeps at most one transaction
outstanding** (the IFU FSM and the LSU each wait for `rvalid` before issuing again). It
is the main structural assumption in this design. If a prefetch buffer with several
outstanding fetches is added later, `PendSlave` must become a FIFO per master, and
responses from different slaves would have to be reordered — a real design step, not a
tweak.

Symmetrically, `SlaveBusy[s]` blocks a second grant to a slave that still owes a
response, since the memories and peripherals here handle one access at a time. This is
why two masters hitting the same slave serialise.

## Internal signals of `obi_xbar` — reference

Everything internal to the crossbar, in dataflow order. "Comb" signals are
combinational (valid within the cycle); "Reg" signals update on the clock edge.
Indices: `m` = master, `s` = slave.

### Address phase

| Signal | Kind | Per | Meaning |
|--------|------|-----|---------|
| `SlaveSel[m]` | comb | master | One-hot output of master `m`'s address decoder: which slave its current `MAddr` falls into. All zero when the address is unmapped. |
| `DecErr[m]` | comb | master | Master `m`'s address matches no region (`= ~\|SlaveSel[m]`). Routes the access to the error responder instead of a slave. |
| `SlaveReqM[s]` | comb | slave | The request picture as slave `s` sees it: bit `m` set when master `m` is requesting (`MReq[m]`), targets this slave (`SlaveSel[m][s]`), and is not a decode error. This is the arbiter's input. |
| `GrantM[s]` | comb* | slave | One-hot arbiter decision for slave `s`: which master owns this slave's port this cycle. Selects whose `Addr/We/Be/Wdata` are muxed onto the slave port. (*Combinational for `ARB_FIXED`; depends on the pointer register for round robin.) |
| `SlaveBusy[s]` | reg | slave | Slave `s` owes a response: set on `SReq[s] & SGnt[s]`, cleared on `SRvalid[s]`. While set, `SReq[s]` is suppressed, so a slave never receives a second access before answering the first. |
| `NormalGnt[m]` | comb | master | Master `m` was granted a *real* slave this cycle: its winning arbiter's request actually went out (`SReq`) and the slave accepted (`SGnt`). This is the moment a transaction becomes outstanding. |

### Error responder

| Signal | Kind | Per | Meaning |
|--------|------|-----|---------|
| `ErrGnt[m]` | comb | master | Master `m` requested an unmapped address and is granted immediately by the internal error responder (no slave involved). `~ErrPend` keeps it a single-cycle pulse. |
| `ErrPend[m]` | reg | master | Registered copy of `ErrGnt`: in the cycle after the error grant, master `m` receives `MRvalid` with zero data. One-cycle "fake slave" latency. |

`MGnt[m] = NormalGnt[m] | ErrGnt[m]` — a master cannot tell a real grant from an
error grant; only the returned data (and, later, an `err` flag) differ.

### Response routing

| Signal | Kind | Per | Meaning |
|--------|------|-----|---------|
| `PendValid[m]` | reg | master | Master `m` has a transaction outstanding at a real slave. Set on `NormalGnt[m]`, cleared when its response is delivered. |
| `PendSlave[m]` | reg | master | *Which* slave owes master `m` the response — the crossbar's memory of the address phase, written at grant time. The response mux uses it: `MRvalid[m] = PendValid[m] & SRvalid[PendSlave[m]]`. Holds its last value after the response (only meaningful while `PendValid[m]` is set). |

### Worked trace: both masters read DMEM (contention)

Captured from simulation (`ARB_FIXED`, 1-cycle slaves; values are bitmasks, bit 0 =
`MASTER_D`, DMEM = slave 1 so bit 1 on slave vectors):

| cycle | MReq | MGnt | SReq | SGnt | SRvalid | MRvalid | SlaveBusy | NormalGnt | PendValid | PendSlave | what is happening |
|-------|------|------|------|------|---------|---------|-----------|-----------|-----------|-----------|-------------------|
| 0 | `11` | `01` | DMEM | DMEM | 0 | 0 | 0 | `01` | 0 | — | Both masters ask for DMEM. The arbiter picks D (`MASTER_D = 0`, fixed priority); D's address goes out and is granted. I keeps waiting. |
| 1 | `10` | 0 | 0 | 0 | DMEM | `01` | DMEM | 0 | `01` | D→DMEM | DMEM is busy (owes D). Its response arrives and is routed to D via `PendSlave[0] = 1`. I's request is suppressed by `SlaveBusy`. |
| 2 | `10` | `10` | DMEM | DMEM | 0 | 0 | 0 | `10` | 0 | — | Busy cleared; the arbiter now grants I. |
| 3 | 0 | 0 | 0 | 0 | DMEM | `10` | DMEM | 0 | `10` | I→DMEM | DMEM's second response is routed to I. Total: 4 cycles for two serialised accesses (2 each). |

The same two accesses to *different* slaves overlap cycles 0–1 completely (both done
after 2 cycles) — that is the crossbar's concurrency, visible in the trace as two bits
set simultaneously in `SReq`/`SRvalid`.

### Worked trace: decode error

Master D reads unmapped `0x8000_0000` (captured from simulation):

| cycle | MGnt | SReq | MRvalid | ErrGnt | ErrPend | what is happening |
|-------|------|------|---------|--------|---------|-------------------|
| −1 | `01` | 0 | 0 | `01` | 0 | Error grant fires; **no slave port sees a request**. |
| 0 | 0 | 0 | `01` | 0 | `01` | One cycle later `ErrPend` delivers `MRvalid` with `MRdata = 0`. |
| 1 | 0 | 0 | 0 | 0 | 0 | Bus idle again; nothing hung. |

### What to plot in GTKWave

For debugging a routing problem, this signal set (in this order) tells the whole
story: `MReq`, `MGnt`, `SReq`, `SGnt`, `SlaveBusy`, `SRvalid`, `MRvalid`,
`PendValid`, `PendSlave[0]`, `PendSlave[1]`, plus `MAddr`/`SAddr` in hex. Run any
xbar test with `make WAVES=1` and find them under `obi_xbar`. Reading rule of thumb:
a transaction is *born* where `SReq & SGnt` pulse together, *lives* in `SlaveBusy`
and `PendValid`/`PendSlave`, and *dies* where `SRvalid` meets `MRvalid`.

## Decode errors

An unmapped address is granted immediately by an internal error responder and answered
one cycle later with `rvalid` and zero data; the access never reaches a slave port. The
bus therefore cannot hang on a stray address — important in a teaching setting, where a
hung simulation is far harder to diagnose than a zero read. A natural extension is
OBI's `err` signal plus a load/store fault trap.

## Flattened ports

The coding standard forbids arrays of signals as ports, so the crossbar boundary uses
packed vectors: master `m` occupies `[m*32 +: 32]` of `MAddr`, bit `m` of `MReq`, and so
on. Internally, 2D arrays are used freely. The testbench mirrors this with slice
helpers.

## Performance

Measured in `tb/unit/obi_xbar` with one-cycle-latency slave models: two concurrent
accesses to **different** slaves complete in 21 ns, versus 40 ns to the **same** slave —
close to the ideal 2× and the reason for choosing a crossbar over a shared bus.

## Verification

- `tb/unit/obi_decoder` — region bases, first/last address of each region, one-past-the-end,
  one-hot guarantee (no overlapping regions), and unmapped holes.
- `tb/unit/obi_arbiter` — built with `NUM_MASTERS=4`; one-hot grants for all 16 request
  combinations, single requester, fixed-priority starvation, round-robin rotation and
  skipping of idle masters, pointer stability without `Update`. Run both policies:
  `make` and `make ARB_POLICY=1`.
- `tb/unit/obi_xbar` — routing from both masters to all five slaves, write routing and
  isolation, concurrency timing, contention with policy-dependent ordering, the
  busy-slave check (asserts no second request is issued to a busy slave), decode errors
  alone and concurrent with a normal access, and back-to-back streams. Both policies pass.
