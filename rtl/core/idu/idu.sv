///////////////////////////////////////////////////////////////////////
// idu
//
// Purpose: Instruction Decode Unit for the HIPV core (D stage).
//          Receives InstrF/PCF/PCPlus4F from Fetch through a
//          valid/ready handshake into the F/D pipeline register,
//          decodes the instruction (idudec), reads the register file
//          and extends the immediate. The stage output is qualified
//          by ValidD/ReadyE toward Execute. A taken branch/jump
//          (PCSrcE) flushes the instruction held in this stage.
//          The register file write port is driven by the Writeback
//          stage (RegWriteW/RdW/ResultW).
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module idu (input  logic        clk, reset,
            // handshake with the Fetch stage
            input  logic        ValidF,
            output logic        ReadyD,
            input  logic [31:0] InstrF, PCF, PCPlus4F,
            // flush on taken branch/jump resolved in Execute
            input  logic        PCSrcE,
            // handshake with the Execute stage
            output logic        ValidD,
            input  logic        ReadyE,
            // write port from the Writeback stage
            input  logic        RegWriteW,
            input  logic [4:0]  RdW,
            input  logic [31:0] ResultW,
            // stage outputs to Execute
            output logic [31:0] RD1D, RD2D, ImmExtD, PCD, PCPlus4D,
            output logic [4:0]  Rs1D, Rs2D, RdD,
            output logic [2:0]  Funct3D,
            output logic        RegWriteD, MemWriteD, BranchD, JumpD, JalrD,
            output logic [1:0]  ResultSrcD, ALUSrcAD,
            output logic        ALUSrcBD,
            output logic [3:0]  ALUControlD);

  logic [31:0] InstrD;
  logic [2:0]  ImmSrcD;
  logic        EnFD, ValidDReg;

  // F/D handshake: accept when the stage is empty or being drained
  assign ReadyD = ~ValidDReg | ReadyE;
  assign EnFD   = ValidF & ReadyD;
  assign ValidD = ValidDReg & ~PCSrcE;

  // F/D valid bit, cleared by a flush
  always_ff @(posedge clk)
    if (reset) ValidDReg <= 1'b0;
    else if (PCSrcE) ValidDReg <= 1'b0;
    else if (ReadyD) ValidDReg <= ValidF;

  // F/D pipeline registers
  flopenr #(32) instrreg(.clk(clk), .reset(reset), .en(EnFD), .D(InstrF), .Q(InstrD));
  flopenr #(32) pcreg(.clk(clk), .reset(reset), .en(EnFD), .D(PCF), .Q(PCD));
  flopenr #(32) pcplus4reg(.clk(clk), .reset(reset), .en(EnFD), .D(PCPlus4F), .Q(PCPlus4D));

  // instruction fields
  assign Rs1D    = InstrD[19:15];
  assign Rs2D    = InstrD[24:20];
  assign RdD     = InstrD[11:7];
  assign Funct3D = InstrD[14:12];

  // control decoder
  idudec dec(.OpD(InstrD[6:0]), .Funct3D(Funct3D), .Funct7b5D(InstrD[30]),
             .RegWriteD(RegWriteD), .ImmSrcD(ImmSrcD), .ALUSrcAD(ALUSrcAD),
             .ALUSrcBD(ALUSrcBD), .MemWriteD(MemWriteD), .ResultSrcD(ResultSrcD),
             .BranchD(BranchD), .JumpD(JumpD), .JalrD(JalrD), .ALUControlD(ALUControlD));

  // register file, written by the Writeback stage
  regfile rf(.clk(clk), .WE3(RegWriteW), .A1(Rs1D), .A2(Rs2D), .A3(RdW),
             .WD3(ResultW), .RD1(RD1D), .RD2(RD2D));

  // immediate extension
  extend ext(.InstrD(InstrD[31:7]), .ImmSrcD(ImmSrcD), .ImmExtD(ImmExtD));

endmodule
