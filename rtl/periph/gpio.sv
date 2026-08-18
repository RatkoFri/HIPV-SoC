///////////////////////////////////////////////////////////////////////
// gpio
//
// Purpose: SoC adapter for the obi_gpio core
//          (rtl/periph/obi_gpio.sv, from github.com/RatkoFri/obi_gpio).
//          Interface changes only, the core is instantiated as-is:
//          project port naming, active-high reset, rready tied high,
//          error output unrouted.
//          Register map (byte offsets, from the IP):
//            0x00 GPO (output register, read-back), 0x04 GPI (inputs,
//            registered once)
// Author:  Ratko Pilipovic
// Date:    17 August 2026
///////////////////////////////////////////////////////////////////////

module gpio #(parameter NUM_IN = 8, parameter NUM_OUT = 8) (
  input  logic               clk, reset,
  // OBI slave port
  input  logic               ObiReq,
  output logic               ObiGnt,
  input  logic [31:0]        ObiAddr,
  input  logic               ObiWe,
  input  logic [3:0]         ObiBe,
  input  logic [31:0]        ObiWdata,
  output logic               ObiRvalid,
  output logic [31:0]        ObiRdata,
  // pins
  input  logic [NUM_IN-1:0]  GpioIn,
  output logic [NUM_OUT-1:0] GpioOut);

  // no error routing in the fabric yet
  /* verilator lint_off UNUSEDSIGNAL */
  logic UnusedErr;
  /* verilator lint_on UNUSEDSIGNAL */

  obi_gpio #(.ADDR_WIDTH(32), .DATA_WIDTH(32),
             .NUM_IN(NUM_IN), .NUM_OUT(NUM_OUT)) core(
    .clk_i(clk), .rstn_i(~reset),
    .obi_areq_i(ObiReq), .obi_agnt_o(ObiGnt), .obi_aaddr_i(ObiAddr),
    .obi_awdata_i(ObiWdata), .obi_awe_i(ObiWe), .obi_abe_i(ObiBe),
    .obi_rvalid_o(ObiRvalid), .obi_rready_i(1'b1), .obi_rdata_o(ObiRdata),
    .obi_rerr_o(UnusedErr),
    .gpio_in_i(GpioIn), .gpio_out_o(GpioOut));

endmodule
