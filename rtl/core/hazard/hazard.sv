///////////////////////////////////////////////////////////////////////
// hazard
//
// Purpose: Hazard unit for the HIPV core. Pure forwarding logic:
//          selects the Execute operands from the M stage (newest),
//          the W stage, or the D/E register (no dependency). x0 is
//          never forwarded.
//          No stall outputs are needed: the elastic valid/ready
//          handshake covers the classic load-use case. A load holds
//          the Memory stage (ReadyM = 0) until its data is available,
//          the dependent instruction waits in Execute, and
//          ForwardDataM then supplies the load data.
//          RegWriteM/RegWriteW inputs must already be qualified with
//          the stage valid bits (the LSU and WBU outputs are).
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module hazard (input  logic [4:0] Rs1E, Rs2E,
               input  logic [4:0] RdM, RdW,
               input  logic       RegWriteM, RegWriteW,
               output logic [1:0] ForwardAE, ForwardBE);

  // 0. import hipv_pkg::* for the forwarding encodings
  //      FWD_RF  = operand from the D/E register (no dependency)
  //      FWD_WB  = ResultW from Writeback
  //      FWD_MEM = ForwardDataM from Memory

  // 1. ForwardAE (operand rs1), always_comb, in priority order:
  //      a) RegWriteM and Rs1E == RdM and Rs1E != x0  -> FWD_MEM (newest value)
  //      b) RegWriteW and Rs1E == RdW and Rs1E != x0  -> FWD_WB
  //      c) otherwise                                 -> FWD_RF

  // 2. ForwardBE (operand rs2): same rules with Rs2E

  // Note: no stall output. A load holds the M stage (ReadyM = 0) until
  // its data arrives; the dependent instruction waits in E and then
  // takes the load data via FWD_MEM.

endmodule
