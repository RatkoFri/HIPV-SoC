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

  logic [31:0] ALUResultW, ReadDataW, PCPlus4W;
  logic        RegWriteWReg;
  logic [1:0]  ResultSrcW;
  logic        EnMW;

  // writeback never stalls
  assign ReadyW = 1'b1;
  assign EnMW   = ValidM & ReadyW;

  // M/W valid bit
  always_ff @(posedge clk)
    if (reset) ValidW <= 1'b0;
    else ValidW <= EnMW;

  // M/W pipeline registers
  flopenr #(32) alureg(.clk(clk), .reset(reset), .en(EnMW), .D(ALUResultM), .Q(ALUResultW));
  flopenr #(32) rdatareg(.clk(clk), .reset(reset), .en(EnMW), .D(ReadDataM), .Q(ReadDataW));
  flopenr #(32) pcplus4reg(.clk(clk), .reset(reset), .en(EnMW), .D(PCPlus4M), .Q(PCPlus4W));
  flopenr #(8)  ctrlreg(.clk(clk), .reset(reset), .en(EnMW),
                        .D({RegWriteM, RdM, ResultSrcM}),
                        .Q({RegWriteWReg, RdW, ResultSrcW}));

  // result selection
  mux3 #(32) resultmux(.D0(ALUResultW), .D1(ReadDataW), .D2(PCPlus4W),
                       .S(ResultSrcW), .Y(ResultW));

  // register write, qualified with the stage valid bit
  assign RegWriteW = RegWriteWReg & ValidW;

endmodule
