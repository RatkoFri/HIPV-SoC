# How to add a new slave to the HIPV SoC

Step-by-step instructions for attaching a new memory-mapped slave (peripheral or
memory) to the crossbar. The running example adds a PWM peripheral at `0x2000_3000`.
Total: two RTL files touched, one new module, two testbench files, no crossbar changes —
`obi_xbar` scales with `NUM_SLAVES` automatically.

The procedure has been validated end-to-end: steps 1, 2, 4 and 5 were executed on a
scratch copy of the repository and all interconnect testbenches pass with the sixth
slave in place.

## Checklist

| # | File | Change |
|---|------|--------|
| 1 | `config/hipv_soc_pkg.sv` | slave index, `NUM_SLAVES`, base/size |
| 2 | `rtl/interconnect/obi_decoder.sv` | one `SlaveSel` line |
| 3 | `rtl/periph/<name>.sv` | the slave itself (template below) |
| 4 | `tb/common/socmap.py` | mirror the map for testbenches |
| 5 | `tb/unit/obi_decoder`, `tb/unit/obi_xbar` | rerun; widths follow the package |
| 6 | SoC top (`rtl/top/hipv_soc.sv`, once it exists) | connect the new slave port |
| 7 | `docs/INTERCONNECT.md` | add the region to the address-map table |

## 1. Address map (`config/hipv_soc_pkg.sv`)

Add an index, bump `NUM_SLAVES`, and define the region:

```systemverilog
  localparam int unsigned NUM_SLAVES = 6;          // was 5
  ...
  localparam int unsigned SLAVE_PWM   = 5;

  localparam logic [31:0] PWM_BASE   = 32'h2000_3000;
  localparam logic [31:0] PWM_SIZE   = 32'h0000_1000;  // 4 KiB
```

Rules the decoder depends on:

- **Power-of-two size, naturally aligned** (`BASE % SIZE == 0`). The decoder matches
  `(Addr & ~(SIZE-1)) == BASE` — one comparator — and this only works for aligned
  power-of-two regions.
- **No overlap** with any existing region. The decoder test's one-hot check
  (`test_onehot`) will catch an overlap, but check the table in
  `docs/INTERCONNECT.md` first anyway.
- Peripherals conventionally go in the `0x2000_xxxx` block, 4 KiB apart.

## 2. Decoder (`rtl/interconnect/obi_decoder.sv`)

Add one line to the match block:

```systemverilog
    SlaveSel[SLAVE_PWM]   = in_region(Addr, PWM_BASE, PWM_SIZE);
```

That is all: the `SlaveSel` port width is `[NUM_SLAVES-1:0]` from the package, and the
crossbar's parameter defaults also come from the package
(`parameter NUM_SLAVES = hipv_soc_pkg::NUM_SLAVES`), so decoder, crossbar and every
testbench resize automatically. Nothing else in `obi_xbar.sv` changes — arbitration,
muxing, busy tracking and response routing are all `generate`d per slave.

## 3. The slave module (`rtl/periph/`)

A slave must speak the OBI subset the crossbar uses: accept an address phase
(`Req`/`Gnt`), give exactly **one** `Rvalid` response per granted request (also for
writes), and tolerate at most one outstanding transaction (the crossbar's `SlaveBusy`
guarantees no second grant before the response).

The simplest compliant behaviour: always grant, respond one cycle later. Template,
following the register-slave pattern:

```systemverilog
///////////////////////////////////////////////////////////////////////
// pwm
//
// Purpose: <one line>. OBI slave, always-ready, 1-cycle response.
// Register map (word offsets within the region):
//   0x0  CTRL   RW
//   0x4  PERIOD RW
//   0x8  DUTY   RW
///////////////////////////////////////////////////////////////////////

module pwm (input  logic        clk, reset,
            // OBI slave port
            input  logic        ObiReq,
            output logic        ObiGnt,
            input  logic [31:0] ObiAddr,
            input  logic        ObiWe,
            input  logic [3:0]  ObiBe,
            input  logic [31:0] ObiWdata,
            output logic        ObiRvalid,
            output logic [31:0] ObiRdata,
            // function side
            output logic        PwmOut);

  logic [31:0] CtrlReg, PeriodReg, DutyReg;
  logic [3:0]  AddrReg;          // captured word-offset bits for the read mux

  // always ready: grant combinationally, respond next cycle
  assign ObiGnt = ObiReq;

  always_ff @(posedge clk)
    if (reset) ObiRvalid <= 1'b0;
    else ObiRvalid <= ObiReq & ObiGnt;

  // register writes (decode word offset ObiAddr[11:2] as needed)
  always_ff @(posedge clk)
    if (reset) begin
      CtrlReg   <= 32'b0;
      PeriodReg <= 32'b0;
      DutyReg   <= 32'b0;
    end else if (ObiReq & ObiGnt & ObiWe)
      case (ObiAddr[3:2])
        2'd0: CtrlReg   <= ObiWdata;
        2'd1: PeriodReg <= ObiWdata;
        2'd2: DutyReg   <= ObiWdata;
        default: ;
      endcase

  // capture the offset in the address phase, mux the read data with it
  always_ff @(posedge clk)
    if (ObiReq & ObiGnt) AddrReg <= ObiAddr[5:2];

  always_comb
    case (AddrReg[1:0])
      2'd0:    ObiRdata = CtrlReg;
      2'd1:    ObiRdata = PeriodReg;
      2'd2:    ObiRdata = DutyReg;
      default: ObiRdata = 32'b0;
    endcase

  // ... the actual PWM counter/comparator goes here ...
endmodule
```

Notes:

- **Writes get a response too.** The LSU waits for `Rvalid` on stores; a slave that
  only responds to reads hangs the pipeline on the first `sw`.
- **Capture the address at grant.** `ObiAddr` is only guaranteed during the address
  phase; the read mux must use the captured copy, not the live bus.
- `ObiBe` may be ignored by simple peripherals (word-only registers) — say so in the
  banner. Memories must honour it.
- A slower slave (e.g. one doing a real bus access) may hold off `ObiGnt` or delay
  `ObiRvalid` for as many cycles as it needs; the crossbar and the LSU/IFU wait
  correctly — that is what the valid/ready and req/gnt handshakes are for.

## 4. Testbench map (`tb/common/socmap.py`)

Mirror the package — the decoder/xbar testbenches derive everything from this dict:

```python
SLAVE = { "IMEM": 0, "DMEM": 1, "UART": 2, "TIMER": 3, "GPIO": 4, "PWM": 5 }
REGIONS = { ...,
    "PWM": (0x2000_3000, 0x0000_1000),
}
```

## 5. Rerun the interconnect testbenches

```sh
cd tb/unit/obi_decoder && make          # extents, one-hot, holes
cd ../obi_xbar && make && make ARB_POLICY=1
```

`test_routing_per_slave` and friends iterate over `SLAVE`/`REGIONS`, so the new slave
is covered without editing the tests. If the region overlaps an old one, `test_onehot`
fails; if you forgot the decoder line, `test_unmapped`/`test_routing_per_slave` fail.
Note that the hole list in `test_unmapped` contains `0x2000_3000` ("just past GPIO") —
that address is now mapped, so **move the hole** to `0x2000_4000`.

Then write a unit testbench for the slave itself (`tb/unit/pwm/`): reuse
`master_access`-style driving or drive the OBI pins directly; check every register
reads back, a write followed by a read returns the new value, and one `Rvalid` pulse
follows every access, including writes.

## 6. SoC top

In `hipv_soc.sv` (when it exists): instantiate the slave and connect it to the
crossbar's flattened slave port at its index, e.g. for index 5:

```systemverilog
  pwm pwm(.clk(clk), .reset(reset),
          .ObiReq(SReq[SLAVE_PWM]), .ObiGnt(SGnt[SLAVE_PWM]),
          .ObiAddr(SAddr[SLAVE_PWM*32 +: 32]), .ObiWe(SWe[SLAVE_PWM]),
          .ObiBe(SBe[SLAVE_PWM*4 +: 4]), .ObiWdata(SWdata[SLAVE_PWM*32 +: 32]),
          .ObiRvalid(SRvalid[SLAVE_PWM]), .ObiRdata(SRdata[SLAVE_PWM*32 +: 32]),
          .PwmOut(PwmOut));
```

and pass `.NUM_SLAVES(NUM_SLAVES)` to the `obi_xbar` instance (it already comes from
the package if the top imports it).

## 7. Documentation

Add the region to the address-map table in `docs/INTERCONNECT.md`, and the register
map to the slave's own doc or banner comment. Software-visible registers belong in
`docs/MemoryMap.md` once that file exists.

## Common mistakes

| Symptom | Cause |
|---------|-------|
| First store to the new slave hangs the core | Slave never asserts `Rvalid` for writes |
| Reads return the wrong register | Read mux uses live `ObiAddr` instead of the captured offset |
| `test_onehot` fails after the edit | New region overlaps an existing one (check size/alignment) |
| `test_unmapped` fails | The new region absorbed an address that the test listed as a hole — update the hole list |
| Decoder compiles but slave unreachable | `NUM_SLAVES` bumped but the `SlaveSel[SLAVE_X] = in_region(...)` line was not added, so the new index decodes as unmapped |
| Slave works alone, fails behind the xbar | Slave assumed back-to-back accesses; it must produce one response per grant, in order |
