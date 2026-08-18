///////////////////////////////////////////////////////////////////////
// uart
//
// Purpose: SoC adapter for the obi_uart core
//          (rtl/periph/obi_uart.sv, from github.com/RatkoFri/obi_uart).
//          Interface changes only, the core is instantiated as-is:
//            - project port naming and active-high reset
//            - obi_rready_i tied high (the HIPV fabric has no response
//              ready; masters always accept responses)
//            - obi_rerr_o left unrouted (no error path in the fabric
//              yet)
//          Register map (byte offsets, from the IP):
//            0x00 CONF, 0x04 SPEED (baud limit in clk cycles),
//            0x08 TX (write starts transmission), 0x0C RX,
//            0x10 STATUS {bit1: rx data available, bit0: tx empty}
// Author:  Ratko Pilipovic
// Date:    17 August 2026
///////////////////////////////////////////////////////////////////////

module uart (input  logic        clk, reset,
             // OBI slave port
             input  logic        ObiReq,
             output logic        ObiGnt,
             input  logic [31:0] ObiAddr,
             input  logic        ObiWe,
             input  logic [3:0]  ObiBe,
             input  logic [31:0] ObiWdata,
             output logic        ObiRvalid,
             output logic [31:0] ObiRdata,
             // serial pins
             output logic        Tx,
             input  logic        Rx);

  // no error routing in the fabric yet
  /* verilator lint_off UNUSEDSIGNAL */
  logic UnusedErr;
  /* verilator lint_on UNUSEDSIGNAL */

  obi_uart #(.ADDR_WIDTH(32), .DATA_WIDTH(32)) core(
    .clk_i(clk), .rstn_i(~reset),
    .obi_areq_i(ObiReq), .obi_agnt_o(ObiGnt), .obi_aaddr_i(ObiAddr),
    .obi_awdata_i(ObiWdata), .obi_awe_i(ObiWe), .obi_abe_i(ObiBe),
    .obi_rvalid_o(ObiRvalid), .obi_rready_i(1'b1), .obi_rdata_o(ObiRdata),
    .obi_rerr_o(UnusedErr),
    .tx_o(Tx), .rx_i(Rx));

endmodule
