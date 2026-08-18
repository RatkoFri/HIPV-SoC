///////////////////////////////////////////////////////////////////////
// timer
//
// Purpose: SoC adapter for the obi_timer core
//          (rtl/periph/obi_timer.sv, from github.com/RatkoFri/obi_timer).
//          Interface changes only, the core is instantiated as-is:
//          project port naming, active-high reset, rready tied high,
//          error output unrouted.
//          Register map (byte offsets, from the IP):
//            0x00 CONF  {bit1: reset counter, bit0: enable counting}
//            0x04 COUNT_LO   (read-only)
//            0x08 COUNT_HI   (read-only)
//            0x0C CMP_LO
//            0x10 CMP_HI
//          Overflow is a level: Overflow = count >= {CMP_HI, CMP_LO}.
//          Both compare registers reset to 0, so Overflow is asserted
//          out of reset — software must program the compare value
//          before (or together with) enabling the counter.
//          Overflow is the future machine-timer interrupt source; it is
//          brought to the SoC boundary until traps exist.
// Author:  Ratko Pilipovic
// Date:    18 August 2026
///////////////////////////////////////////////////////////////////////

module timer (input  logic        clk, reset,
              // OBI slave port
              input  logic        ObiReq,
              output logic        ObiGnt,
              input  logic [31:0] ObiAddr,
              input  logic        ObiWe,
              input  logic [3:0]  ObiBe,
              input  logic [31:0] ObiWdata,
              output logic        ObiRvalid,
              output logic [31:0] ObiRdata,
              // compare match (machine timer interrupt source)
              output logic        Overflow);

  // no error routing in the fabric yet
  /* verilator lint_off UNUSEDSIGNAL */
  logic UnusedErr;
  /* verilator lint_on UNUSEDSIGNAL */

  obi_timer #(.ADDR_WIDTH(32), .DATA_WIDTH(32)) core(
    .clk_i(clk), .rstn_i(~reset),
    .obi_areq_i(ObiReq), .obi_agnt_o(ObiGnt), .obi_aaddr_i(ObiAddr),
    .obi_awdata_i(ObiWdata), .obi_awe_i(ObiWe), .obi_abe_i(ObiBe),
    .obi_rvalid_o(ObiRvalid), .obi_rready_i(1'b1), .obi_rdata_o(ObiRdata),
    .obi_rerr_o(UnusedErr),
    .overflow_o(Overflow));

endmodule
