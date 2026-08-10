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

  import hipv_pkg::*;

  always_comb
    if (RegWriteM & (Rs1E == RdM) & (Rs1E != 5'b0)) ForwardAE = FWD_MEM;
    else if (RegWriteW & (Rs1E == RdW) & (Rs1E != 5'b0)) ForwardAE = FWD_WB;
    else ForwardAE = FWD_RF;

  always_comb
    if (RegWriteM & (Rs2E == RdM) & (Rs2E != 5'b0)) ForwardBE = FWD_MEM;
    else if (RegWriteW & (Rs2E == RdW) & (Rs2E != 5'b0)) ForwardBE = FWD_WB;
    else ForwardBE = FWD_RF;

endmodule
