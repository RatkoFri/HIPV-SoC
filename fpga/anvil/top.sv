///////////////////////////////////////////////////////////////////////
// top
//
// Purpose: FPGA wrapper for the HIPV SoC on the Digilent Nexys A7-100T,
//          built with Anvil (F4PGA). Board plumbing only — no core
//          design logic lives here:
//            - divides the board's 100 MHz oscillator down to the
//              SoC's 25 MHz operating clock with the CMT's MMCME2_ADV
//              + a BUFG (see below; see also the clock constraint in
//              the XDC and CPU_HZ in sw/rules.mk, which must match)
//            - converts the active-low CPU_RESETN button to the SoC's
//              synchronous active-high reset, through a synchroniser,
//              plus a power-on reset so the SoC starts without the
//              button being pressed
//            - maps GPIO to the LEDs and slide switches
//            - maps the UART to the USB-serial bridge
//            - shows the timer compare match on the top LED
//
//          Deliberately free of package imports and type parameters:
//          Anvil converts project sources with sv2v, and this file is
//          kept simple enough to survive any conversion path.
// Author:  Ratko Pilipovic
// Date:    20 August 2026
///////////////////////////////////////////////////////////////////////

module top #(parameter RAM_ADDR_WIDTH = 14,          // 2^14 words = 64 KiB
             parameter INIT_FILE      = "firmware.hex")
           (input  logic       clk,          // board oscillator, 100 MHz
            input  logic       cpu_resetn,   // active-low push button
            output logic       uart_tx,      // to the USB-serial RXD
            input  logic       uart_rx,      // from the USB-serial TXD
            input  logic [7:0] sw,           // slide switches -> GPIO in
            output logic [7:0] led,          // LEDs <- GPIO out
            output logic       led_timer);   // timer compare match

  // ---------------------------------------------------------------
  // clock: divide the 100 MHz board oscillator down to 25 MHz for the
  // SoC using the Artix-7's CMT hard block, via MMCME2_ADV directly.
  // MMCME2_BASE (the simplified wrapper) doesn't work in this flow --
  // Yosys's Xilinx techmap doesn't lower it to the MMCME2_ADV
  // primitive this toolchain's VPR architecture actually models, so
  // packing fails with "no matching architecture model for
  // MMCME2_BASE". MMCME2_ADV is that primitive, so it's used here
  // directly; the dynamic-reconfiguration/phase-shift ports this
  // design never uses (DADDR/DCLK/DEN/DI/DWE, PSCLK/PSEN/PSINCDEC) are
  // tied off disabled, and CLKINSEL pins CLKIN1 as the only input.
  //
  // VCO = 100 MHz * 10 / 1 = 1000 MHz; CLKOUT0 = 1000 / 40 = 25 MHz.
  // Confirmed working on real hardware (Nexys A7-50T). A plain fabric
  // FSM divider works too and was the first thing confirmed on
  // hardware -- see KnownBugs.md, BUG-CLOCK, for that history and for
  // why this toolchain can't automatically verify either version's
  // timing (the XDC->SDC conversion doesn't follow a clock through a
  // divider, hard block or fabric).
  // ---------------------------------------------------------------
  logic SocClkUnbuf, SocClk, ClkFb, MmcmLocked;

  MMCME2_ADV #(.CLKIN1_PERIOD(10.0),      // 100 MHz input
               .CLKFBOUT_MULT_F(10.0),    // VCO = 100 * 10 / 1 = 1000 MHz
               .DIVCLK_DIVIDE(1),
               .CLKOUT0_DIVIDE_F(40.0))   // 1000 / 40 = 25 MHz
    mmcm(.CLKIN1(clk), .CLKIN2(1'b0), .CLKINSEL(1'b1),
         .CLKFBIN(ClkFb), .CLKFBOUT(ClkFb),
         .CLKOUT0(SocClkUnbuf),
         .LOCKED(MmcmLocked),
         .RST(~cpu_resetn), .PWRDWN(1'b0),
         .DADDR(7'b0), .DCLK(1'b0), .DEN(1'b0), .DI(16'b0), .DWE(1'b0),
         .PSCLK(1'b0), .PSEN(1'b0), .PSINCDEC(1'b0));

  BUFG bufg(.I(SocClkUnbuf), .O(SocClk));

  // ---------------------------------------------------------------
  // reset: active-low button -> synchronous active-high reset
  //
  // Two flops synchronise the release edge into SocClk's domain --
  // the domain this reset actually drives. The SoC resets
  // synchronously, so the clock must be running while reset is
  // asserted — guaranteed once the MMCM reports LOCKED.
  //
  // PorCount additionally holds reset for the first 15 SocClk cycles
  // after lock, so the SoC starts cleanly even if the button is never
  // pressed.
  // ---------------------------------------------------------------
  logic       ResetSyncQ, ResetSync;
  logic [3:0] PorCount;
  logic       PorReset;
  logic       SocReset;

  initial begin
    PorCount   = 4'd0;
    ResetSyncQ = 1'b1;
    ResetSync  = 1'b1;
  end

  always_ff @(posedge SocClk) begin
    ResetSyncQ <= ~cpu_resetn | ~MmcmLocked;   // button, or clock not ready
    ResetSync  <= ResetSyncQ;
  end

  always_ff @(posedge SocClk)
    if (~MmcmLocked) PorCount <= 4'd0;
    else if (PorCount != 4'hF) PorCount <= PorCount + 4'd1;

  assign PorReset = (PorCount != 4'hF);
  assign SocReset = ResetSync | PorReset;

  // ---------------------------------------------------------------
  // the SoC
  //
  // INIT_FILE is resolved by the synthesiser relative to the directory
  // the build runs in, so firmware.hex sits in the project root. Build
  // it from sw/ — see docs/FPGA.md.
  // ---------------------------------------------------------------
  hipv_soc #(.RAM_ADDR_WIDTH(RAM_ADDR_WIDTH),
             .INIT_FILE(INIT_FILE),
             .ARB_POLICY(0),               // fixed priority, data first
             .GPIO_WIDTH(8))
    soc(.clk(SocClk), .reset(SocReset),
        .Tx(uart_tx), .Rx(uart_rx),
        .GpioIn(sw), .GpioOut(led),
        .TimerOverflow(led_timer));

endmodule
