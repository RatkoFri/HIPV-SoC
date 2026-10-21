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

  // 0. Internal signals: InstrD [31:0], ImmSrcD [2:0], EnFD, ValidDReg

  // 1. F/D handshake
  //    - ReadyD = stage is empty (~ValidDReg) or being drained (ReadyE)
  //    - EnFD   = Fetch offers (ValidF) and we accept (ReadyD)
  //    - ValidD = ValidDReg, killed by a taken branch/jump (PCSrcE)

  // 2. F/D valid bit ValidDReg (always_ff)
  //    - reset: 0
  //    - else if ReadyD: take ValidF
  //    No extra flush term needed: PCSrcE implies ReadyD, and ValidF is
  //    already low during a redirect.

  // 3. F/D pipeline registers: flopenr #(32), enable EnFD
  //      instrreg:   InstrF   -> InstrD
  //      pcreg:      PCF      -> PCD
  //      pcplus4reg: PCPlus4F -> PCPlus4D

  // 4. Instruction fields from InstrD
  //      Rs1D = [19:15], Rs2D = [24:20], RdD = [11:7], Funct3D = [14:12]

  // 5. Control decoder: idudec "dec"
  //    - inputs:  OpD = InstrD[6:0], Funct3D, Funct7b5D = InstrD[30]
  //    - outputs: RegWriteD, ImmSrcD, ALUSrcAD, ALUSrcBD, MemWriteD,
  //               ResultSrcD, BranchD, JumpD, JalrD, ALUControlD

  // 6. Register file: regfile "rf"
  //    - read:  A1 = Rs1D -> RD1D, A2 = Rs2D -> RD2D
  //    - write (from Writeback): WE3 = RegWriteW, A3 = RdW, WD3 = ResultW

  // 7. Immediate extension: extend "ext"
  //    - InstrD[31:7], ImmSrcD -> ImmExtD

endmodule
