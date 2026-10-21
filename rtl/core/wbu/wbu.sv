///////////////////////////////////////////////////////////////////////
// wbu
//
// Purpose: Writeback Unit for the HIPV core (W stage).
//          Holds the M/W pipeline register and selects the writeback
//          result (ALU result, load data or PC+4). RegWriteW is
//          qualified with the stage valid bit and drives the register
//          file write port in the Decode stage directly. Writeback
//          never stalls (ReadyW is constant 1).
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module wbu (input  logic        clk, reset,
            // handshake with the Memory stage
            input  logic        ValidM,
            output logic        ReadyW,
            // inputs from Memory
            input  logic [31:0] ALUResultM, ReadDataM, PCPlus4M,
            input  logic [4:0]  RdM,
            input  logic        RegWriteM,
            input  logic [1:0]  ResultSrcM,
            // writeback outputs (to the register file and hazard unit)
            output logic        ValidW,
            output logic        RegWriteW,
            output logic [4:0]  RdW,
            output logic [31:0] ResultW);

  // 0. Internal signals: ALUResultW, ReadDataW, PCPlus4W [31:0],
  //    RegWriteWReg, ResultSrcW [1:0], EnMW

  // 1. M/W handshake: Writeback never stalls
  //    - ReadyW = 1
  //    - EnMW   = ValidM & ReadyW

  // 2. M/W valid bit ValidW (always_ff): reset 0, else ValidW <= EnMW

  // 3. M/W pipeline registers (flopenr, enable EnMW)
  //      alureg     #(32) ALUResultM -> ALUResultW
  //      rdatareg   #(32) ReadDataM  -> ReadDataW
  //      pcplus4reg #(32) PCPlus4M   -> PCPlus4W
  //      ctrlreg    #(8)  {RegWriteM, RdM, ResultSrcM}
  //                    -> {RegWriteWReg, RdW, ResultSrcW}

  // 4. Result select: resultmux (mux3), S = ResultSrcW
  //      D0 = ALUResultW, D1 = ReadDataW, D2 = PCPlus4W -> ResultW

  // 5. RegWriteW = RegWriteWReg qualified with ValidW

endmodule
