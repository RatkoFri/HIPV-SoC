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

  // 0. Internal signals
  //      RD1E, RD2E, ImmExtE, PCE                         [31:0]
  //      FwdAE, SrcAE, SrcBE, PCTargetBaseE, JalrTargetE  [31:0]
  //      RD1NextE, RD2NextE                               [31:0]
  //      BranchE, JumpE, JalrE, TakenE, ALUSrcBE
  //      ALUSrcAE [1:0], ALUControlE [3:0]
  //      EnDE, ValidEReg, HoldE

  // 1. D/E handshake
  //    - ReadyE = stage is empty (~ValidEReg) or being drained (ReadyM)
  //    - EnDE   = ValidD & ReadyE
  //    - ValidE = ValidEReg

  // 2. D/E valid bit ValidEReg (always_ff)
  //    - reset: 0, else if ReadyE: take ValidD

  // 3. Operand refresh while E stalls
  //    - HoldE = ValidEReg & ~ReadyE (instruction waiting in E)
  //    - The producer can leave W (and stop being forwarded) before this
  //      instruction leaves E, so keep re-capturing the forwarded values:
  //        rd1mux (mux2): EnDE ? RD1D : FwdAE      -> RD1NextE
  //        rd2mux (mux2): EnDE ? RD2D : WriteDataE -> RD2NextE

  // 4. D/E pipeline registers (flopenr)
  //    - enable EnDE | HoldE:  rd1reg RD1NextE -> RD1E, rd2reg RD2NextE -> RD2E
  //    - enable EnDE:
  //        immreg     #(32) ImmExtD  -> ImmExtE
  //        pcreg      #(32) PCD      -> PCE
  //        pcplus4reg #(32) PCPlus4D -> PCPlus4E
  //        regsreg    #(15) {Rs1D, Rs2D, RdD} -> {Rs1E, Rs2E, RdE}
  //        funct3reg  #(3)  Funct3D  -> Funct3E
  //        ctrlreg    #(14) {RegWrite, MemWrite, Branch, Jump, Jalr, ResultSrc,
  //                          ALUSrcA, ALUSrcB, ALUControl}  D -> E

  // 5. Forwarding muxes (mux3), select from the hazard unit
  //      fwdamux: D0 = RD1E, D1 = ResultW, D2 = ForwardDataM, S = ForwardAE -> FwdAE
  //      fwdbmux: D0 = RD2E, D1 = ResultW, D2 = ForwardDataM, S = ForwardBE -> WriteDataE
  //    (the forwarded rs2 is also the store data)

  // 6. ALU operand selection
  //      srcamux (mux3): FwdAE / PCE / 32'b0, S = ALUSrcAE -> SrcAE
  //      srcbmux (mux2): WriteDataE / ImmExtE, S = ALUSrcBE -> SrcBE

  // 7. ALU and branch comparator
  //      alu "alu":        SrcAE, SrcBE, ALUControlE -> ALUResultE
  //      branchcmp "bcmp": FwdAE, WriteDataE, Funct3E -> TakenE
  //                        (compares the forwarded registers, not SrcA/SrcB)

  // 8. Branch/jump target
  //      targetadd (adder): PCE + ImmExtE -> PCTargetBaseE  (branch, jal)
  //      JalrTargetE = ALUResultE with bit 0 cleared        (jalr: rs1 + imm)
  //      targetmux (mux2): JalrE selects JalrTargetE        -> PCTargetE

  // 9. Redirect
  //      PCSrcE = ValidEReg & ReadyM & (JumpE | JalrE | (BranchE & TakenE))
  //      Gated with ReadyM: fire only in the cycle the instruction leaves E,
  //      when the forwarded operands are guaranteed to be resolved.

endmodule
