///////////////////////////////////////////////////////////////////////
// top
//
// Purpose: FPGA wrapper for the HIPV SoC on the Digilent Nexys A7-100T,
//          built with Anvil (F4PGA). Board plumbing only — no design
//          logic lives here:
//            - the board clock drives the SoC directly (50 MHz, see the
//              clock constraint in the XDC)
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
           (input  logic       clk,          // SoC clock, 50 MHz (see XDC)
            input  logic       cpu_resetn,   // active-low push button
            output logic       uart_tx,      // to the USB-serial RXD
            input  logic       uart_rx,      // from the USB-serial TXD
            input  logic [7:0] sw,           // slide switches -> GPIO in
            output logic [7:0] led,          // LEDs <- GPIO out
            output logic       led_timer);   // timer compare match

  // ---------------------------------------------------------------
  // reset: active-low button -> synchronous active-high reset
  //
  // Two flops synchronise the release edge into the clock domain. The
  // SoC resets synchronously, so the clock must be running while reset
  // is asserted — always true here, the board clock free-runs.
  //
  // PorCount additionally holds reset for the first 15 clocks after
  // configuration, so the SoC starts cleanly even if the button is
  // never pressed.
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

  always_ff @(posedge clk) begin
    ResetSyncQ <= ~cpu_resetn;   // button pressed = reset requested
    ResetSync  <= ResetSyncQ;
  end

  always_ff @(posedge clk)
    if (PorCount != 4'hF) PorCount <= PorCount + 4'd1;

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
    soc(.clk(clk), .reset(SocReset),
        .Tx(uart_tx), .Rx(uart_rx),
        .GpioIn(sw), .GpioOut(led),
        .TimerOverflow(led_timer));

endmodule
