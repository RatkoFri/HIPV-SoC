///////////////////////////////////////////////////////////////////////
// extend
//
// Purpose: Immediate extension unit. Assembles and sign-extends the
//          immediate from the instruction word for the five RV32I
//          formats (I, S, B, U, J), selected by ImmSrcD.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module extend (input  logic [31:7] InstrD,
               input  logic [2:0]  ImmSrcD,
               output logic [31:0] ImmExtD);

  // 0. import hipv_pkg::* for the IMM_* encodings

  // 1. always_comb case (ImmSrcD). Instr[31] is always the sign bit;
  //    replicate it to fill the upper bits ({n{InstrD[31]}}).
  //      IMM_I: imm[11:0]  = Instr[31:20]
  //      IMM_S: imm[11:0]  = {Instr[31:25], Instr[11:7]}
  //      IMM_B: imm[12:0]  = {Instr[31], Instr[7], Instr[30:25], Instr[11:8], 1'b0}
  //      IMM_J: imm[20:0]  = {Instr[31], Instr[19:12], Instr[20], Instr[30:21], 1'b0}
  //      IMM_U: imm[31:0]  = {Instr[31:12], 12'b0}   (no extension needed)
  //      default: 32'b0

endmodule
