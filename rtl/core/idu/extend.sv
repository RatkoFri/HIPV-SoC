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

  import hipv_pkg::*;

  always_comb
    case (ImmSrcD)
      IMM_I:   ImmExtD = {{20{InstrD[31]}}, InstrD[31:20]};
      IMM_S:   ImmExtD = {{20{InstrD[31]}}, InstrD[31:25], InstrD[11:7]};
      IMM_B:   ImmExtD = {{20{InstrD[31]}}, InstrD[7], InstrD[30:25], InstrD[11:8], 1'b0};
      IMM_J:   ImmExtD = {{12{InstrD[31]}}, InstrD[19:12], InstrD[20], InstrD[30:21], 1'b0};
      IMM_U:   ImmExtD = {InstrD[31:12], 12'b0};
      default: ImmExtD = 32'b0;
    endcase

endmodule
