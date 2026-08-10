///////////////////////////////////////////////////////////////////////
// ieu
//
// Purpose: Integer Execution Unit for the HIPV core (E stage).
//          Holds the D/E pipeline register (elastic valid/ready),
//          selects ALU operands through the forwarding muxes
//          (ForwardAE/ForwardBE from the hazard unit) and the operand
//          source muxes (register/PC/zero, register/immediate), runs
//          the ALU and the branch comparator, and computes the
//          branch/jump target. PCSrcE/PCTargetE redirect the Fetch
//          stage and flush Decode; the branch itself continues to the
//          Memory stage. PCSrcE is gated with ReadyM so the redirect
//          fires exactly in the cycle the instruction leaves E; while
//          the Memory stage stalls (e.g. a load in flight) forwarded
//          operands may not be resolved yet and must not redirect.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module ieu (input  logic        clk, reset,
            // handshake with the Decode stage
            input  logic        ValidD,
            output logic        ReadyE,
            // inputs from Decode
            input  logic [31:0] RD1D, RD2D, ImmExtD, PCD, PCPlus4D,
            input  logic [4:0]  Rs1D, Rs2D, RdD,
            input  logic [2:0]  Funct3D,
            input  logic        RegWriteD, MemWriteD, BranchD, JumpD, JalrD,
            input  logic [1:0]  ResultSrcD, ALUSrcAD,
            input  logic        ALUSrcBD,
            input  logic [3:0]  ALUControlD,
            // forwarding (from the hazard unit and later stages)
            input  logic [1:0]  ForwardAE, ForwardBE,
            input  logic [31:0] ForwardDataM, ResultW,
            // redirect to Fetch/Decode
            output logic        PCSrcE,
            output logic [31:0] PCTargetE,
            // handshake with the Memory stage
            output logic        ValidE,
            input  logic        ReadyM,
            // stage outputs to Memory
            output logic [31:0] ALUResultE, WriteDataE, PCPlus4E,
            output logic [4:0]  RdE,
            output logic [4:0]  Rs1E, Rs2E,
            output logic [2:0]  Funct3E,
            output logic        RegWriteE, MemWriteE,
            output logic [1:0]  ResultSrcE);

  logic [31:0] RD1E, RD2E, ImmExtE, PCE;
  logic [31:0] FwdAE, SrcAE, SrcBE, PCTargetBaseE, JalrTargetE;
  logic        BranchE, JumpE, JalrE, TakenE;
  logic [1:0]  ALUSrcAE;
  logic        ALUSrcBE;
  logic [3:0]  ALUControlE;
  logic        EnDE, ValidEReg;

  // D/E handshake: accept when the stage is empty or being drained
  assign ReadyE = ~ValidEReg | ReadyM;
  assign EnDE   = ValidD & ReadyE;
  assign ValidE = ValidEReg;

  // D/E valid bit
  always_ff @(posedge clk)
    if (reset) ValidEReg <= 1'b0;
    else if (ReadyE) ValidEReg <= ValidD;

  // D/E pipeline registers
  flopenr #(32) rd1reg(.clk(clk), .reset(reset), .en(EnDE), .D(RD1D), .Q(RD1E));
  flopenr #(32) rd2reg(.clk(clk), .reset(reset), .en(EnDE), .D(RD2D), .Q(RD2E));
  flopenr #(32) immreg(.clk(clk), .reset(reset), .en(EnDE), .D(ImmExtD), .Q(ImmExtE));
  flopenr #(32) pcreg(.clk(clk), .reset(reset), .en(EnDE), .D(PCD), .Q(PCE));
  flopenr #(32) pcplus4reg(.clk(clk), .reset(reset), .en(EnDE), .D(PCPlus4D), .Q(PCPlus4E));
  flopenr #(15) regsreg(.clk(clk), .reset(reset), .en(EnDE),
                        .D({Rs1D, Rs2D, RdD}), .Q({Rs1E, Rs2E, RdE}));
  flopenr #(3)  funct3reg(.clk(clk), .reset(reset), .en(EnDE), .D(Funct3D), .Q(Funct3E));
  flopenr #(14) ctrlreg(.clk(clk), .reset(reset), .en(EnDE),
                        .D({RegWriteD, MemWriteD, BranchD, JumpD, JalrD, ResultSrcD,
                            ALUSrcAD, ALUSrcBD, ALUControlD}),
                        .Q({RegWriteE, MemWriteE, BranchE, JumpE, JalrE, ResultSrcE,
                            ALUSrcAE, ALUSrcBE, ALUControlE}));

  // forwarding muxes: register operand / ResultW / ForwardDataM
  mux3 #(32) fwdamux(.D0(RD1E), .D1(ResultW), .D2(ForwardDataM), .S(ForwardAE), .Y(FwdAE));
  mux3 #(32) fwdbmux(.D0(RD2E), .D1(ResultW), .D2(ForwardDataM), .S(ForwardBE), .Y(WriteDataE));

  // ALU operand selection: A = rs1/PC/zero, B = rs2/immediate
  mux3 #(32) srcamux(.D0(FwdAE), .D1(PCE), .D2(32'b0), .S(ALUSrcAE), .Y(SrcAE));
  mux2 #(32) srcbmux(.D0(WriteDataE), .D1(ImmExtE), .S(ALUSrcBE), .Y(SrcBE));

  // ALU and branch comparator (comparator uses the forwarded operands)
  alu alu(.A(SrcAE), .B(SrcBE), .ALUControl(ALUControlE), .Y(ALUResultE));
  branchcmp bcmp(.A(FwdAE), .B(WriteDataE), .Funct3E(Funct3E), .TakenE(TakenE));

  // branch/jump target: PC + imm for branch/jal, ALU (rs1 + imm) for jalr
  adder #(32) targetadd(.A(PCE), .B(ImmExtE), .Y(PCTargetBaseE));
  assign JalrTargetE = {ALUResultE[31:1], 1'b0};
  mux2 #(32) targetmux(.D0(PCTargetBaseE), .D1(JalrTargetE), .S(JalrE), .Y(PCTargetE));

  // redirect, qualified with the valid bit and gated to the retire cycle
  assign PCSrcE = ValidEReg & ReadyM & (JumpE | JalrE | (BranchE & TakenE));

endmodule
